from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.database.connection import get_db
from app.models.alert import Alert
from app.schemas.alert import AlertCreate, AlertOut, AlertUpdate

router = APIRouter()


@router.get("", response_model=list[AlertOut])
def list_alerts(
    status_filter: Optional[str] = None,
    severity: Optional[str] = None,
    db: Session = Depends(get_db),
):
    """Get alerts, optionally filtered — e.g. ?status_filter=active&severity=high."""
    stmt = select(Alert)
    if status_filter is not None:
        stmt = stmt.where(Alert.status == status_filter)
    if severity is not None:
        stmt = stmt.where(Alert.severity == severity)
    stmt = stmt.order_by(Alert.created_at.desc())
    return db.execute(stmt).scalars().all()


@router.get("/{alert_id}", response_model=AlertOut)
def get_alert(alert_id: int, db: Session = Depends(get_db)):
    alert = db.get(Alert, alert_id)
    if not alert:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Alert not found")
    return alert


@router.post("", response_model=AlertOut, status_code=status.HTTP_201_CREATED)
def create_alert(payload: AlertCreate, db: Session = Depends(get_db)):
    alert = Alert(**payload.model_dump())
    db.add(alert)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status.HTTP_409_CONFLICT, "invalid vehicle_id/plate_id/camera_id") from exc
    db.refresh(alert)
    return alert


@router.patch("/{alert_id}", response_model=AlertOut)
def update_alert(alert_id: int, payload: AlertUpdate, db: Session = Depends(get_db)):
    """Typical use: acknowledge or resolve an alert."""
    alert = db.get(Alert, alert_id)
    if not alert:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Alert not found")
    data = payload.model_dump(exclude_unset=True)
    if data.get("status") == "resolved" and not data.get("resolved_at"):
        data["resolved_at"] = datetime.now(timezone.utc).replace(tzinfo=None)
    for field, value in data.items():
        setattr(alert, field, value)
    db.commit()
    db.refresh(alert)
    return alert


@router.delete("/{alert_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_alert(alert_id: int, db: Session = Depends(get_db)):
    alert = db.get(Alert, alert_id)
    if not alert:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Alert not found")
    db.delete(alert)
    db.commit()
