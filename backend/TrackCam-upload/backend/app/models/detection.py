"""
Detection model — mirrors the `detections` table in trackcam_database.sql
exactly. Stores normalized YOLO-format bounding boxes as-is.

source = 'ground_truth'    -> dataset annotation, confidence MUST be NULL
source = 'model_prediction' -> real model output, confidence is the actual score
"""

from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Integer, Numeric, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base


class Detection(Base):
    __tablename__ = "detections"

    id: Mapped[int] = mapped_column(primary_key=True)
    frame_id: Mapped[int] = mapped_column(ForeignKey("frames.id", ondelete="CASCADE"), nullable=False)
    class_id: Mapped[int] = mapped_column(Integer, nullable=False)
    class_name: Mapped[str] = mapped_column(String(100), nullable=False)
    confidence: Mapped[float | None] = mapped_column(Numeric(6, 5))
    x_center: Mapped[float] = mapped_column(Numeric(10, 7), nullable=False)
    y_center: Mapped[float] = mapped_column(Numeric(10, 7), nullable=False)
    width: Mapped[float] = mapped_column(Numeric(10, 7), nullable=False)
    height: Mapped[float] = mapped_column(Numeric(10, 7), nullable=False)
    source: Mapped[str] = mapped_column(String(30), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    frame = relationship("Frame", back_populates="detections")
    license_plate = relationship(
        "LicensePlate", back_populates="detection", uselist=False, cascade="all, delete-orphan"
    )

    __table_args__ = (
        CheckConstraint("source IN ('ground_truth', 'model_prediction')", name="chk_detection_source"),
        CheckConstraint("x_center BETWEEN 0 AND 1", name="chk_detection_x_center"),
        CheckConstraint("y_center BETWEEN 0 AND 1", name="chk_detection_y_center"),
        CheckConstraint("width BETWEEN 0 AND 1", name="chk_detection_width"),
        CheckConstraint("height BETWEEN 0 AND 1", name="chk_detection_height"),
        CheckConstraint("confidence IS NULL OR (confidence BETWEEN 0 AND 1)", name="chk_detection_confidence"),
        CheckConstraint(
            "source <> 'ground_truth' OR confidence IS NULL",
            name="chk_detection_gt_no_confidence",
        ),
    )
