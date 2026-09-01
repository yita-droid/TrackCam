"""
Camera model — mirrors the `cameras` table in trackcam_database.sql exactly.
"""

from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, Integer, Numeric, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base


class Camera(Base):
    __tablename__ = "cameras"

    id: Mapped[int] = mapped_column(primary_key=True)
    camera_id: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(150), nullable=False)
    location: Mapped[str | None] = mapped_column(String(255))
    latitude: Mapped[float | None] = mapped_column(Numeric(10, 7))
    longitude: Mapped[float | None] = mapped_column(Numeric(10, 7))
    status: Mapped[str] = mapped_column(String(20), nullable=False)
    traffic_level: Mapped[str | None] = mapped_column(String(20))
    vehicle_count: Mapped[int] = mapped_column(Integer, default=0)
    health: Mapped[float | None] = mapped_column(Numeric(5, 2))
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    videos = relationship("Video", back_populates="camera", cascade="all, delete-orphan")
    vehicle_events = relationship("VehicleEvent", back_populates="camera")
    alerts = relationship("Alert", back_populates="camera")
    current_vehicles = relationship("Vehicle", back_populates="current_camera")

    __table_args__ = (
        CheckConstraint("status IN ('online', 'offline', 'maintenance')", name="chk_camera_status"),
        CheckConstraint(
            "traffic_level IS NULL OR traffic_level IN ('low', 'medium', 'high')",
            name="chk_camera_traffic_level",
        ),
        CheckConstraint("vehicle_count >= 0", name="chk_camera_vehicle_count"),
        CheckConstraint("health IS NULL OR (health BETWEEN 0 AND 100)", name="chk_camera_health"),
        CheckConstraint("latitude IS NULL OR (latitude BETWEEN -90 AND 90)", name="chk_camera_lat"),
        CheckConstraint("longitude IS NULL OR (longitude BETWEEN -180 AND 180)", name="chk_camera_lng"),
    )
