"""
LicensePlate model — mirrors the `license_plates` table in
trackcam_database.sql exactly.

For dataset-only rows (no OCR run yet): plate_number and ocr_confidence stay
NULL. They are populated later once a real OCR/ANPR model produces them.
"""

from datetime import datetime

from sqlalchemy import Boolean, CheckConstraint, DateTime, ForeignKey, Numeric, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base


class LicensePlate(Base):
    __tablename__ = "license_plates"

    id: Mapped[int] = mapped_column(primary_key=True)
    detection_id: Mapped[int | None] = mapped_column(
        ForeignKey("detections.id", ondelete="CASCADE"), unique=True
    )
    plate_number: Mapped[str | None] = mapped_column(String(30))
    ocr_text_raw: Mapped[str | None] = mapped_column(Text)
    ocr_confidence: Mapped[float | None] = mapped_column(Numeric(6, 5))
    verified: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    detection = relationship("Detection", back_populates="license_plate")
    vehicles = relationship("Vehicle", back_populates="plate")
    vehicle_events = relationship("VehicleEvent", back_populates="plate")
    alerts = relationship("Alert", back_populates="plate")

    __table_args__ = (
        CheckConstraint(
            "ocr_confidence IS NULL OR (ocr_confidence BETWEEN 0 AND 1)",
            name="chk_plate_ocr_confidence",
        ),
    )
