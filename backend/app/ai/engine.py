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
from app.ai.plate_ocr import PlateOCR, normalize_indian_plate

_state: dict[str, Any] = {"plate_model": None, "ocr": None, "device": None}


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
    _state["plate_model"] = YOLO(_resolve(settings.PLATE_MODEL_PATH))
    _state["ocr"] = PlateOCR(gpu=device == "cuda")


def analyze_image(data: bytes, plate_conf: float = 0.25,
                  plate_format: str = "indian") -> dict[str, Any]:
    """Detect plates in an image and read them. Returns real detections only;
    never fabricates a plate. Confidence is a 0-1 float (frontend x100)."""
    _ensure_loaded()
    arr = np.frombuffer(data, np.uint8)
    frame = cv2.imdecode(arr, cv2.IMREAD_COLOR)
    if frame is None:
        return {"detected": False, "device": _state["device"],
                "detections": [], "message": "Could not decode image."}

    H, W = frame.shape[:2]
    res = _state["plate_model"](frame, conf=plate_conf,
                                device=_state["device"], verbose=False)[0]

    detections: list[dict[str, Any]] = []
    for box in sorted(res.boxes, key=lambda b: -float(b.conf[0])):
        px1, py1, px2, py2 = map(int, box.xyxy[0])
        detect_conf = float(box.conf[0])
        pad_x = int(0.06 * (px2 - px1))
        pad_y = int(0.20 * (py2 - py1))
        cx1, cy1 = max(0, px1 - pad_x), max(0, py1 - pad_y)
        cx2, cy2 = min(W, px2 + pad_x), min(H, py2 + pad_y)
        crop = frame[cy1:cy2, cx1:cx2]

        text, conf, info = _state["ocr"].read(crop)
        if not text:
            continue  # plate located but not legible -> not a fabricated read

        plate, ok = (text, None)
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

        detections.append({
            "plate": plate,
            "plate_raw": text,
            "format_valid": ok,
            "confidence": round(conf, 3),          # 0-1 float
            "detect_conf": round(detect_conf, 3),
            "quality": "Good" if conf >= 0.80 else "Degraded",
            "box": [px1, py1, px2, py2],
            "frames": frames,
        })

    return {"detected": len(detections) > 0, "device": _state["device"],
            "detections": detections}
