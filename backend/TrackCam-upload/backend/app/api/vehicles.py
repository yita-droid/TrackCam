from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.database.connection import get_db
from app.models.vehicle import Vehicle
from app.models.vehicle_event import VehicleEvent
from app.schemas.vehicle import VehicleCreate, VehicleOut, VehicleUpdate
from app.schemas.vehicle_event import VehicleEventOut

router = APIRouter()


@router.get("", response_model=list[VehicleOut])
def list_vehicles(vehicle_type: Optional[str] = None, db: Session = Depends(get_db)):
    stmt = select(Vehicle)
    if vehicle_type is not None:
        stmt = stmt.where(Vehicle.vehicle_type == vehicle_type)
    stmt = stmt.order_by(Vehicle.last_seen.desc().nullslast())
    return db.execute(stmt).scalars().all()


@router.get("/{vehicle_id}", response_model=VehicleOut)
def get_vehicle(vehicle_id: int, db: Session = Depends(get_db)):
    vehicle = db.get(Vehicle, vehicle_id)
    if not vehicle:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Vehicle not found")
    return vehicle


@router.get("/{vehicle_id}/journey", response_model=list[VehicleEventOut])
def get_vehicle_journey(vehicle_id: int, db: Session = Depends(get_db)):
    """
    Get a vehicle's complete movement history / cross-camera journey,
    ordered chronologically (Vehicle -> CAM001 -> CAM002 -> ...).
    """
    vehicle = db.get(Vehicle, vehicle_id)
    if not vehicle:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Vehicle not found")
    stmt = (
        select(VehicleEvent)
        .where(VehicleEvent.vehicle_id == vehicle_id)
        .order_by(VehicleEvent.timestamp.asc())
    )
    return db.execute(stmt).scalars().all()


@router.post("", response_model=VehicleOut, status_code=status.HTTP_201_CREATED)
def create_vehicle(payload: VehicleCreate, db: Session = Depends(get_db)):
    vehicle = Vehicle(**payload.model_dump())
    db.add(vehicle)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status.HTTP_409_CONFLICT, "vehicle_id already exists or FK invalid") from exc
    db.refresh(vehicle)
    return vehicle


@router.patch("/{vehicle_id}", response_model=VehicleOut)
def update_vehicle(vehicle_id: int, payload: VehicleUpdate, db: Session = Depends(get_db)):
    vehicle = db.get(Vehicle, vehicle_id)
    if not vehicle:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Vehicle not found")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(vehicle, field, value)
    db.commit()
    db.refresh(vehicle)
    return vehicle


@router.delete("/{vehicle_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_vehicle(vehicle_id: int, db: Session = Depends(get_db)):
    vehicle = db.get(Vehicle, vehicle_id)
    if not vehicle:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Vehicle not found")
    db.delete(vehicle)
    db.commit()
