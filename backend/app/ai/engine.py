"""
ANPR inference engine (Stage 3).

Wraps the SAME vehicle+plate+OCR pipeline used in the offline demo
(``app/ai/plate_ocr.py``, a copy of the AIML module) behind one function the
API layer can call:

    analyze_image(bytes) -> { detected, device, detections: [ {plate, ...} ] }

Design notes
------------
* Models load LAZILY on the first request (not at import), so importing this
  module for tests never blocks on EasyOCR/YOLO or requires a GPU.
* Loaded ONCE then kept warm in ``_state`` (first request ~15s incl. EasyOCR
  download; subsequent requests ~1-3s on GPU).
* Uses EasyOCR (via PlateOCR) deliberately — PaddlePaddle is unreliable on
  Windows / Python 3.12 (see plate_ocr.py). Indian-format correction is applied
  so 8<->B / 5<->S / O<->Q confusions are repaired.
"""
from __future__ import annotations

import os
from typing import Any

import cv2
import numpy as np
import torch
from ultralytics import YOLO

from app.config import settings
from app.ai.plate_ocr import PlateOCR, normalize_indian_plate, VEHICLE_CLASSES

_state: dict[str, Any] = {
    "vehicle_model": None,
    "plate_model": None,
    "ocr": None,
    "device": None,
}


def _tone(conf_pct: int) -> str:
    return "good" if conf_pct >= 85 else "warn" if conf_pct >= 70 else "critical"


def _resolve(path: str) -> str:
    """Resolve a (possibly relative) model path against the backend root."""
    if os.path.isabs(path):
        return path
    backend_root = os.path.dirname(os.path.dirname(os.path.dirname(
        os.path.abspath(__file__))))  # .../backend
    return os.path.join(backend_root, path)


def models_available() -> bool:
    return os.path.exists(_resolve(settings.PLATE_MODEL_PATH))


def _ensure_loaded() -> None:
    if _state["ocr"] is not None:
        return
    device = "cuda" if torch.cuda.is_available() else "cpu"
    _state["device"] = device
    # Stage 1: COCO vehicle detector (yolo11n.pt from the sih models/ folder)
    _state["vehicle_model"] = YOLO(_resolve(settings.YOLO_MODEL_PATH))
    # Stage 2: fine-tuned license-plate detector
    _state["plate_model"] = YOLO(_resolve(settings.PLATE_MODEL_PATH))
    # Stage 3: EasyOCR reader
    _state["ocr"] = PlateOCR(gpu=device == "cuda")


def _center_inside(inner: list[int], outer: list[int]) -> bool:
    """True when the centre of *inner* box lies within *outer* box."""
    ix1, iy1, ix2, iy2 = inner
    cx, cy = (ix1 + ix2) / 2, (iy1 + iy2) / 2
    ox1, oy1, ox2, oy2 = outer
    return ox1 <= cx <= ox2 and oy1 <= cy <= oy2


def analyze_image(data: bytes, plate_conf: float = 0.25,
                  vehicle_conf: float = 0.40,
                  plate_format: str = "indian") -> dict[str, Any]:
    """Two-stage YOLO pipeline matching the offline traffic-AI demo:

    1. Run yolo11n.pt (COCO) to find vehicles → returns vehicle_boxes
    2. Run plate.pt to find license plates inside those vehicles
    3. OCR + Indian-format correction on each plate crop

    Returns real detections only; never fabricates a plate or vehicle.
    Confidence values are 0-1 floats (frontend multiplies by 100).
    """
    _ensure_loaded()
    arr = np.frombuffer(data, np.uint8)
    frame = cv2.imdecode(arr, cv2.IMREAD_COLOR)
    if frame is None:
        return {"detected": False, "device": _state["device"],
                "detections": [], "vehicle_boxes": [],
                "message": "Could not decode image."}

    H, W = frame.shape[:2]

    # ---------------------------------------------------------------------- #
    # Stage 1 — vehicle detection (yolo11n.pt, COCO classes)
    # ---------------------------------------------------------------------- #
    v_results = _state["vehicle_model"](
        frame,
        conf=vehicle_conf,
        classes=list(VEHICLE_CLASSES.keys()),
        device=_state["device"],
        verbose=False,
    )[0]

    vehicle_boxes: list[dict[str, Any]] = []
    for vbox in v_results.boxes:
        vx1, vy1, vx2, vy2 = map(int, vbox.xyxy[0])
        cls_id = int(vbox.cls[0])
        vehicle_boxes.append({
            "box": [vx1, vy1, vx2, vy2],
            "label": VEHICLE_CLASSES.get(cls_id, "vehicle"),
            "conf": round(float(vbox.conf[0]), 3),
        })

    # ---------------------------------------------------------------------- #
    # Stage 2 — license-plate detection (plate.pt)
    # ---------------------------------------------------------------------- #
    p_results = _state["plate_model"](
        frame, conf=plate_conf, device=_state["device"], verbose=False
    )[0]

    detections: list[dict[str, Any]] = []
    for box in sorted(p_results.boxes, key=lambda b: -float(b.conf[0])):
        px1, py1, px2, py2 = map(int, box.xyxy[0])
        detect_conf = float(box.conf[0])

        # Stage 3 — crop + OCR
        pad_x = int(0.06 * (px2 - px1))
        pad_y = int(0.20 * (py2 - py1))
        cx1, cy1 = max(0, px1 - pad_x), max(0, py1 - pad_y)
        cx2, cy2 = min(W, px2 + pad_x), min(H, py2 + pad_y)
        crop = frame[cy1:cy2, cx1:cx2]

        text, conf, info = _state["ocr"].read(crop)
        if not text:
            continue  # plate located but not legible — never fabricate

        plate, ok = text, None
        if plate_format == "indian":
            plate, ok = normalize_indian_plate(text)

        conf_pct = int(round(conf * 100))
        frames = []
        for i, (vname, vtext, vconf) in enumerate(info.get("variants", [])):
            if vtext:
                vpct = int(round(vconf * 100))
                row = [f"{i + 1:02d}", vtext, f"{vpct}%", _tone(vpct)]
                if vtext != plate:
                    row.append("character ambiguity")
                frames.append(row)

        # Which vehicle owns this plate?
        owner = "vehicle"
        for v in vehicle_boxes:
            if _center_inside([px1, py1, px2, py2], v["box"]):
                owner = v["label"]
                break

        detections.append({
            "plate": plate,
            "plate_raw": text,
            "format_valid": ok,
            "confidence": round(conf, 3),       # 0-1 float; frontend × 100
            "detect_conf": round(detect_conf, 3),
            "quality": "Good" if conf >= 0.80 else "Degraded",
            "box": [px1, py1, px2, py2],        # plate box in image pixels
            "vehicle": owner,
            "frames": frames,
        })

    return {
        "detected": len(detections) > 0 or len(vehicle_boxes) > 0,
        "device": _state["device"],
        "vehicle_boxes": vehicle_boxes,         # NEW — stage-1 results
        "detections": detections,               # plate + OCR results
    }
