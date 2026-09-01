from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.database.connection import get_db
from app.models.camera import Camera
from app.models.detection import Detection

router = APIRouter()


@router.get("/cameras/vehicle-counts")
def camera_vehicle_counts(db: Session = Depends(get_db)):
    """Camera-wise vehicle count, ordered highest first."""
    stmt = (
        select(Camera.camera_id, Camera.name, Camera.vehicle_count)
        .order_by(Camera.vehicle_count.desc())
    )
    rows = db.execute(stmt).all()
    return [{"camera_id": r.camera_id, "name": r.name, "vehicle_count": r.vehicle_count} for r in rows]


@router.get("/detections/daily-count")
def daily_detection_count(db: Session = Depends(get_db)):
    """Detection count grouped by day."""
    day = func.date(Detection.created_at)
    stmt = (
        select(day.label("detection_date"), func.count().label("total_detections"))
        .group_by(day)
        .order_by(day.desc())
    )
    rows = db.execute(stmt).all()
    return [{"detection_date": str(r.detection_date), "total_detections": r.total_detections} for r in rows]


@router.get("/traffic")
def traffic_statistics(db: Session = Depends(get_db)):
    """Current per-camera traffic snapshot."""
    stmt = select(
        Camera.camera_id,
        Camera.name,
        Camera.traffic_level,
        Camera.vehicle_count,
        Camera.health,
        Camera.status,
    ).order_by(Camera.vehicle_count.desc())
    rows = db.execute(stmt).all()
    return [
        {
            "camera_id": r.camera_id,
            "name": r.name,
            "traffic_level": r.traffic_level,
            "vehicle_count": r.vehicle_count,
            "health": float(r.health) if r.health is not None else None,
            "status": r.status,
        }
        for r in rows
    ]
