"""
Alert model — mirrors the `alerts` table in trackcam_database.sql exactly.
"""

from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Numeric, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base


class Alert(Base):
    __tablename__ = "alerts"

    id: Mapped[int] = mapped_column(primary_key=True)
    vehicle_id: Mapped[int | None] = mapped_column(ForeignKey("vehicles.id", ondelete="SET NULL"))
    plate_id: Mapped[int | None] = mapped_column(ForeignKey("license_plates.id", ondelete="SET NULL"))
    camera_id: Mapped[int | None] = mapped_column(ForeignKey("cameras.id", ondelete="SET NULL"))
    alert_type: Mapped[str] = mapped_column(String(50), nullable=False)
    severity: Mapped[str] = mapped_column(String(20), nullable=False)
    confidence: Mapped[float | None] = mapped_column(Numeric(6, 5))
    message: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="active")
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime)

    vehicle = relationship("Vehicle", back_populates="alerts")
    plate = relationship("LicensePlate", back_populates="alerts")
    camera = relationship("Camera", back_populates="alerts")

    __table_args__ = (
        CheckConstraint(
            "alert_type IN ('watchlist', 'suspicious_vehicle', 'anomaly', "
            "'traffic_congestion', 'unknown_plate', 'system')",
            name="chk_alert_type",
        ),
        CheckConstraint("severity IN ('low', 'medium', 'high', 'critical')", name="chk_alert_severity"),
        CheckConstraint("status IN ('active', 'acknowledged', 'resolved')", name="chk_alert_status"),
        CheckConstraint("confidence IS NULL OR (confidence BETWEEN 0 AND 1)", name="chk_alert_confidence"),
        CheckConstraint("resolved_at IS NULL OR resolved_at >= created_at", name="chk_alert_resolved_order"),
    )
