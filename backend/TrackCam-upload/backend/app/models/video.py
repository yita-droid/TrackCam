"""
Video model — mirrors the `videos` table in trackcam_database.sql exactly.

file_path stores only a reference/path to the video file. The binary video
data itself is never stored in the database.
"""

from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base


class Video(Base):
    __tablename__ = "videos"

    id: Mapped[int] = mapped_column(primary_key=True)
    video_id: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    camera_id: Mapped[int | None] = mapped_column(ForeignKey("cameras.id", ondelete="CASCADE"))
    video_name: Mapped[str] = mapped_column(String(255), nullable=False)
    source: Mapped[str | None] = mapped_column(String(100))
    file_path: Mapped[str | None] = mapped_column(Text)
    started_at: Mapped[datetime | None] = mapped_column(DateTime)
    ended_at: Mapped[datetime | None] = mapped_column(DateTime)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    camera = relationship("Camera", back_populates="videos")
    frames = relationship("Frame", back_populates="video", cascade="all, delete-orphan")

    __table_args__ = (
        CheckConstraint(
            "ended_at IS NULL OR started_at IS NULL OR ended_at >= started_at",
            name="chk_video_time_order",
        ),
    )
