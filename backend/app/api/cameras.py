from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.database.connection import get_db
from app.models.camera import Camera
from app.schemas.camera import CameraCreate, CameraOut, CameraUpdate

router = APIRouter()


@router.get("", response_model=list[CameraOut])
def list_cameras(
    status_filter: Optional[str] = None,
    db: Session = Depends(get_db),
):
    """Get all cameras, optionally filtered by status (e.g. ?status_filter=online)."""
    stmt = select(Camera)
    if status_filter:
        stmt = stmt.where(Camera.status == status_filter)
    stmt = stmt.order_by(Camera.camera_id)
    return db.execute(stmt).scalars().all()


@router.get("/{camera_id}", response_model=CameraOut)
def get_camera(camera_id: int, db: Session = Depends(get_db)):
    camera = db.get(Camera, camera_id)
    if not camera:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Camera not found")
    return camera


@router.post("", response_model=CameraOut, status_code=status.HTTP_201_CREATED)
def create_camera(payload: CameraCreate, db: Session = Depends(get_db)):
    camera = Camera(**payload.model_dump())
    db.add(camera)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status.HTTP_409_CONFLICT, "camera_id already exists") from exc
    db.refresh(camera)
    return camera


@router.patch("/{camera_id}", response_model=CameraOut)
def update_camera(camera_id: int, payload: CameraUpdate, db: Session = Depends(get_db)):
    camera = db.get(Camera, camera_id)
    if not camera:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Camera not found")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(camera, field, value)
    db.commit()
    db.refresh(camera)
    return camera


@router.delete("/{camera_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_camera(camera_id: int, db: Session = Depends(get_db)):
    camera = db.get(Camera, camera_id)
    if not camera:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Camera not found")
    db.delete(camera)
    db.commit()
