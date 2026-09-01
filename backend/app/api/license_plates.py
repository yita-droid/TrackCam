from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.database.connection import get_db
from app.models.license_plate import LicensePlate
from app.schemas.license_plate import LicensePlateCreate, LicensePlateOut, LicensePlateUpdate

router = APIRouter()


@router.get("", response_model=list[LicensePlateOut])
def list_license_plates(
    recognized_only: bool = False,
    db: Session = Depends(get_db),
):
    """Get recognized license plates with ?recognized_only=true (plate_number IS NOT NULL)."""
    stmt = select(LicensePlate)
    if recognized_only:
        stmt = stmt.where(LicensePlate.plate_number.is_not(None))
    stmt = stmt.order_by(LicensePlate.created_at.desc())
    return db.execute(stmt).scalars().all()


@router.get("/{plate_id}", response_model=LicensePlateOut)
def get_license_plate(plate_id: int, db: Session = Depends(get_db)):
    plate = db.get(LicensePlate, plate_id)
    if not plate:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "License plate not found")
    return plate


@router.post("", response_model=LicensePlateOut, status_code=status.HTTP_201_CREATED)
def create_license_plate(payload: LicensePlateCreate, db: Session = Depends(get_db)):
    plate = LicensePlate(**payload.model_dump())
    db.add(plate)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status.HTTP_409_CONFLICT, "detection_id invalid or already has a license plate row"
        ) from exc
    db.refresh(plate)
    return plate


@router.patch("/{plate_id}", response_model=LicensePlateOut)
def update_license_plate(plate_id: int, payload: LicensePlateUpdate, db: Session = Depends(get_db)):
    """Typical use: attach real OCR output (plate_number, ocr_confidence) once available."""
    plate = db.get(LicensePlate, plate_id)
    if not plate:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "License plate not found")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(plate, field, value)
    db.commit()
    db.refresh(plate)
    return plate


@router.delete("/{plate_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_license_plate(plate_id: int, db: Session = Depends(get_db)):
    plate = db.get(LicensePlate, plate_id)
    if not plate:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "License plate not found")
    db.delete(plate)
    db.commit()
