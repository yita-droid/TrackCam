from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.database.connection import get_db
from app.models.detection import Detection
from app.schemas.detection import DetectionCreate, DetectionOut

router = APIRouter()


@router.get("", response_model=list[DetectionOut])
def list_detections(
    frame_id: Optional[int] = None,
    class_name: Optional[str] = None,
    source: Optional[str] = None,
    db: Session = Depends(get_db),
):
    stmt = select(Detection)
    if frame_id is not None:
        stmt = stmt.where(Detection.frame_id == frame_id)
    if class_name is not None:
        stmt = stmt.where(Detection.class_name == class_name)
    if source is not None:
        stmt = stmt.where(Detection.source == source)
    stmt = stmt.order_by(Detection.created_at.desc())
    return db.execute(stmt).scalars().all()


@router.get("/{detection_id}", response_model=DetectionOut)
def get_detection(detection_id: int, db: Session = Depends(get_db)):
    detection = db.get(Detection, detection_id)
    if not detection:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Detection not found")
    return detection


@router.post("", response_model=DetectionOut, status_code=status.HTTP_201_CREATED)
def create_detection(payload: DetectionCreate, db: Session = Depends(get_db)):
    detection = Detection(**payload.model_dump())
    db.add(detection)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status.HTTP_409_CONFLICT, "invalid frame_id, or a CHECK constraint failed"
        ) from exc
    db.refresh(detection)
    return detection


@router.delete("/{detection_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_detection(detection_id: int, db: Session = Depends(get_db)):
    detection = db.get(Detection, detection_id)
    if not detection:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Detection not found")
    db.delete(detection)
    db.commit()
