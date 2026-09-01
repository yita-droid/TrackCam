"""
Vehicle model — mirrors the `vehicles` table in trackcam_database.sql exactly.

Rows are only created once real vehicle information is available — never
synthetic/placeholder data.
"""

from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base


class Vehicle(Base):
    __tablename__ = "vehicles"

    id: Mapped[int] = mapped_column(primary_key=True)
    vehicle_id: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    track_id: Mapped[str | None] = mapped_column(String(100))
    plate_id: Mapped[int | None] = mapped_column(ForeignKey("license_plates.id", ondelete="SET NULL"))
    vehicle_type: Mapped[str | None] = mapped_column(String(50))
    color: Mapped[str | None] = mapped_column(String(50))
    first_seen: Mapped[datetime | None] = mapped_column(DateTime)
    last_seen: Mapped[datetime | None] = mapped_column(DateTime)
    current_camera_id: Mapped[int | None] = mapped_column(ForeignKey("cameras.id", ondelete="SET NULL"))
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    plate = relationship("LicensePlate", back_populates="vehicles")
    current_camera = relationship("Camera", back_populates="current_vehicles")
    events = relationship("VehicleEvent", back_populates="vehicle", cascade="all, delete-orphan")
    alerts = relationship("Alert", back_populates="vehicle")

    __table_args__ = (
        CheckConstraint(
            "vehicle_type IS NULL OR vehicle_type IN ('car', 'truck', 'bus', 'motorcycle', 'van', 'unknown')",
            name="chk_vehicle_type",
        ),
        CheckConstraint(
            "last_seen IS NULL OR first_seen IS NULL OR last_seen >= first_seen",
            name="chk_vehicle_seen_order",
        ),
    )
