"""
VehicleEvent model — mirrors the `vehicle_events` table in
trackcam_database.sql exactly. Used to reconstruct a vehicle's path across
cameras over time.
"""

from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Numeric, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base


class VehicleEvent(Base):
    __tablename__ = "vehicle_events"

    id: Mapped[int] = mapped_column(primary_key=True)
    vehicle_id: Mapped[int] = mapped_column(ForeignKey("vehicles.id", ondelete="CASCADE"), nullable=False)
    camera_id: Mapped[int | None] = mapped_column(ForeignKey("cameras.id", ondelete="SET NULL"))
    frame_id: Mapped[int | None] = mapped_column(ForeignKey("frames.id", ondelete="SET NULL"))
    plate_id: Mapped[int | None] = mapped_column(ForeignKey("license_plates.id", ondelete="SET NULL"))
    event_type: Mapped[str] = mapped_column(String(50), nullable=False)
    timestamp: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    latitude: Mapped[float | None] = mapped_column(Numeric(10, 7))
    longitude: Mapped[float | None] = mapped_column(Numeric(10, 7))
    confidence: Mapped[float | None] = mapped_column(Numeric(6, 5))
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    vehicle = relationship("Vehicle", back_populates="events")
    camera = relationship("Camera", back_populates="vehicle_events")
    frame = relationship("Frame", back_populates="vehicle_events")
    plate = relationship("LicensePlate", back_populates="vehicle_events")

    __table_args__ = (
        CheckConstraint(
            "event_type IN ('detected', 'entered_camera', 'exited_camera', "
            "'plate_recognized', 'vehicle_tracked', 'cross_camera_match')",
            name="chk_event_type",
        ),
        CheckConstraint("confidence IS NULL OR (confidence BETWEEN 0 AND 1)", name="chk_event_confidence"),
        CheckConstraint("latitude IS NULL OR (latitude BETWEEN -90 AND 90)", name="chk_event_lat"),
        CheckConstraint("longitude IS NULL OR (longitude BETWEEN -180 AND 180)", name="chk_event_lng"),
    )
