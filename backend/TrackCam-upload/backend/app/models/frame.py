"""
Frame model — mirrors the `frames` table in trackcam_database.sql exactly.

image_path stores only a reference/path to the frame image (e.g.
vid-1/frame_00001.jpg). The image binary itself is never stored here.
"""

from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base


class Frame(Base):
    __tablename__ = "frames"

    id: Mapped[int] = mapped_column(primary_key=True)
    video_id: Mapped[int] = mapped_column(ForeignKey("videos.id", ondelete="CASCADE"), nullable=False)
    frame_number: Mapped[int] = mapped_column(Integer, nullable=False)
    image_path: Mapped[str | None] = mapped_column(Text)
    timestamp: Mapped[datetime | None] = mapped_column(DateTime)
    width: Mapped[int | None] = mapped_column(Integer)
    height: Mapped[int | None] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    video = relationship("Video", back_populates="frames")
    detections = relationship("Detection", back_populates="frame", cascade="all, delete-orphan")
    vehicle_events = relationship("VehicleEvent", back_populates="frame")

    __table_args__ = (
        UniqueConstraint("video_id", "frame_number", name="uq_video_frame"),
        CheckConstraint("frame_number >= 0", name="chk_frame_number"),
        CheckConstraint("width IS NULL OR width > 0", name="chk_frame_width"),
        CheckConstraint("height IS NULL OR height > 0", name="chk_frame_height"),
    )
