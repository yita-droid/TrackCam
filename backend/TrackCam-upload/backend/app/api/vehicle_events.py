from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.database.connection import get_db
from app.models.vehicle_event import VehicleEvent
from app.schemas.vehicle_event import VehicleEventCreate, VehicleEventOut

router = APIRouter()


@router.get("", response_model=list[VehicleEventOut])
def list_vehicle_events(
    vehicle_id: Optional[int] = None,
    camera_id: Optional[int] = None,
    event_type: Optional[str] = None,
    db: Session = Depends(get_db),
):
    stmt = select(VehicleEvent)
    if vehicle_id is not None:
        stmt = stmt.where(VehicleEvent.vehicle_id == vehicle_id)
    if camera_id is not None:
        stmt = stmt.where(VehicleEvent.camera_id == camera_id)
    if event_type is not None:
        stmt = stmt.where(VehicleEvent.event_type == event_type)
    stmt = stmt.order_by(VehicleEvent.timestamp.desc())
    return db.execute(stmt).scalars().all()


@router.get("/{event_id}", response_model=VehicleEventOut)
def get_vehicle_event(event_id: int, db: Session = Depends(get_db)):
    event = db.get(VehicleEvent, event_id)
    if not event:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Vehicle event not found")
    return event


@router.post("", response_model=VehicleEventOut, status_code=status.HTTP_201_CREATED)
def create_vehicle_event(payload: VehicleEventCreate, db: Session = Depends(get_db)):
    event = VehicleEvent(**payload.model_dump())
    db.add(event)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status.HTTP_409_CONFLICT, "invalid vehicle_id/camera_id/frame_id/plate_id") from exc
    db.refresh(event)
    return event


@router.delete("/{event_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_vehicle_event(event_id: int, db: Session = Depends(get_db)):
    event = db.get(VehicleEvent, event_id)
    if not event:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Vehicle event not found")
    db.delete(event)
    db.commit()
