"""
TrackCam API routers.

These endpoints provide the contract consumed by the React/Next.js frontend.
They are intentionally independent of PostgreSQL so the prototype can run
before database migrations are introduced.
"""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from fastapi import APIRouter, File, HTTPException, UploadFile

from app.config import settings

router = APIRouter(prefix="/api", tags=["TrackCam"])

CAMERAS = [
    {"id": "CAM001", "name": "North Gate", "location": "Anna Salai / North Gate", "status": "active", "traffic": "Moderate", "count": 284, "health": "98%", "plate": "TN01AB1234", "confidence": 96, "quality": "Good", "time": "10:42:18"},
    {"id": "CAM008", "name": "Harbour Link", "location": "Rajaji Salai / Gate 2", "status": "active", "traffic": "High", "count": 412, "health": "94%", "plate": "TN01AB1234", "confidence": 91, "quality": "Good", "time": "10:39:44"},
    {"id": "CAM014", "name": "Central Junction", "location": "Mount Road / Cathedral", "status": "moderate", "traffic": "Severe", "count": 631, "health": "89%", "plate": "TN01A81234", "confidence": 62, "quality": "Degraded", "time": "10:36:02"},
    {"id": "CAM023", "name": "Airport Corridor", "location": "GST Road / Meenambakkam", "status": "congested", "traffic": "Severe", "count": 718, "health": "96%", "plate": "TN01AB1234", "confidence": 94, "quality": "Good", "time": "10:31:27"},
]

VEHICLES = {
    "TN01AB1234": {"first": "09:18:04", "last": "10:42:18", "duration": "1h 24m", "overall": 88, "events": [
        {"camera": "CAM001", "place": "North Gate", "time": "09:18:04", "confidence": 96, "state": "HIGH", "x": 16, "y": 68},
        {"camera": "CAM008", "place": "Harbour Link", "time": "09:42:31", "confidence": 91, "state": "HIGH", "x": 39, "y": 35},
        {"camera": "CAM014", "place": "Central Junction", "time": "10:16:48", "confidence": 62, "state": "UNCERTAIN", "x": 61, "y": 54},
        {"camera": "CAM023", "place": "Airport Corridor", "time": "10:42:18", "confidence": 94, "state": "HIGH", "x": 83, "y": 29},
    ]},
    "TN01XX9999": {"first": "08:54:22", "last": "10:42:18", "duration": "1h 48m", "overall": 93, "events": [
        {"camera": "CAM008", "place": "Harbour Link", "time": "08:54:22", "confidence": 95, "state": "HIGH", "x": 24, "y": 56},
        {"camera": "CAM014", "place": "Central Junction", "time": "09:37:16", "confidence": 89, "state": "HIGH", "x": 50, "y": 42},
        {"camera": "CAM023", "place": "Airport Corridor", "time": "10:42:18", "confidence": 97, "state": "HIGH", "x": 78, "y": 68},
    ]},
    "KA03YY1111": {"first": "07:12:09", "last": "08:08:41", "duration": "56m", "overall": 86, "events": [
        {"camera": "CAM001", "place": "North Gate", "time": "07:12:09", "confidence": 86, "state": "HIGH", "x": 18, "y": 30},
        {"camera": "CAM014", "place": "Central Junction", "time": "08:08:41", "confidence": 86, "state": "HIGH", "x": 59, "y": 65},
    ]},
    "DL04CD5678": {"first": "11:08:12", "last": "11:52:05", "duration": "44m", "overall": 79, "events": [
        {"camera": "CAM008", "place": "Harbour Link", "time": "11:08:12", "confidence": 79, "state": "UNCERTAIN", "x": 27, "y": 72},
        {"camera": "CAM023", "place": "Airport Corridor", "time": "11:52:05", "confidence": 88, "state": "HIGH", "x": 80, "y": 35},
    ]},
}

ALERTS = [
    {"type": "WATCHLIST MATCH", "plate": "TN01XX9999", "camera": "CAM023", "place": "Central Junction", "time": "10:42:18", "confidence": 97, "tone": "critical"},
    {"type": "POTENTIAL ROUTE ANOMALY", "plate": "DL04CD5678", "camera": "CAM014", "place": "Mount Road / Cathedral", "time": "10:18:07", "confidence": 68, "tone": "warning", "detail": "Spatial-temporal inconsistency · Requires human review"},
    {"type": "WATCHLIST MATCH", "plate": "KA03YY1111", "camera": "CAM008", "place": "Harbour Link", "time": "09:37:16", "confidence": 91, "tone": "critical"},
]

TRAFFIC = [
    {"name": "Anna Salai", "status": "High", "density": 68},
    {"name": "Rajaji Salai", "status": "Moderate", "density": 44},
    {"name": "GST Road", "status": "Low", "density": 21},
]

@router.get("/dashboard")
def dashboard() -> dict[str, Any]:
    return {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "network": {"total_cameras": 32, "active_cameras": 28, "vehicles_observed": 12846, "active_alerts": len(ALERTS), "avg_confidence": 91.8},
        "cameras": CAMERAS,
        "vehicles": VEHICLES,
        "alerts": ALERTS,
        "traffic": TRAFFIC,
    }

@router.get("/cameras")
def cameras() -> list[dict[str, Any]]:
    return CAMERAS

@router.get("/vehicles/{plate}")
def vehicle(plate: str) -> dict[str, Any]:
    result = VEHICLES.get(plate.upper())
    if not result:
        raise HTTPException(status_code=404, detail="Vehicle not found")
    return {"plate": plate.upper(), **result}

@router.get("/alerts")
def alerts() -> list[dict[str, Any]]:
    return ALERTS

@router.get("/traffic")
def traffic() -> list[dict[str, Any]]:
    return TRAFFIC

@router.post("/anpr/analyze")
async def analyze(file: UploadFile = File(...)) -> dict[str, Any]:
    """Accept an image/video and report model readiness.

    The current supplied backend is Stage 2 and contains no trained model
    weights. Therefore this endpoint never fabricates an ANPR result.
    Once the plate detector/OCR service is added, this same contract can
    return detections and recognized plates.
    """
    suffix = Path(file.filename or "").suffix.lower()
    if suffix not in settings.allowed_video_extensions and not (file.content_type or "").startswith("image/"):
        raise HTTPException(status_code=415, detail="Unsupported file type")

    data = await file.read()
    max_bytes = settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024
    if len(data) > max_bytes:
        raise HTTPException(status_code=413, detail=f"File exceeds {settings.MAX_UPLOAD_SIZE_MB} MB")

    upload_dir = Path(__file__).resolve().parents[2] / "videos"
    upload_dir.mkdir(parents=True, exist_ok=True)
    safe_name = Path(file.filename or "upload.bin").name
    destination = upload_dir / safe_name
    destination.write_bytes(data)

    backend_root = Path(__file__).resolve().parents[2]

    def _exists(rel: str) -> bool:
        p = Path(rel)
        return p.exists() or (backend_root / rel).exists()

    yolo_exists = _exists(settings.YOLO_MODEL_PATH)
    plate_exists = _exists(settings.PLATE_MODEL_PATH)
    is_image = (file.content_type or "").startswith("image/")

    detections: list[dict[str, Any]] = []
    ocr_ran = False
    device = None
    error: str | None = None

    # Real inference: images only (per demo scope). Videos are accepted and
    # stored but not run through the live pipeline here.
    if is_image and plate_exists:
        try:
            from app.ai.engine import analyze_image
            result = analyze_image(data)
            detections = result.get("detections", [])
            device = result.get("device")
            ocr_ran = True
        except Exception as exc:  # noqa: BLE001 - report, don't crash the API
            error = f"{type(exc).__name__}: {exc}"

    if ocr_ran:
        status = "model_ready"
        if detections:
            message = f"Read {len(detections)} plate(s) on {device or 'cpu'}."
        else:
            message = "No license plate detected / legible in this image."
    elif not plate_exists:
        status = "model_not_available"
        message = "Plate model weights not found. Add backend/models/plate.pt to enable inference."
    elif not is_image:
        status = "model_ready"
        message = "Video stored. Live inference is enabled for images only; use the offline pipeline for video."
    else:
        status = "model_not_available"
        message = f"Inference failed: {error}" if error else "Inference unavailable."

    return {
        "status": status,
        "filename": safe_name,
        "size_bytes": len(data),
        "media_type": file.content_type,
        "models": {
            "vehicle_detector": yolo_exists,
            "plate_detector": plate_exists,
            "ocr": ocr_ran,
        },
        "detections": detections,
        "message": message,
    }
