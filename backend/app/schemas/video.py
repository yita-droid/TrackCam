from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class VideoBase(BaseModel):
    video_id: str = Field(..., max_length=100)
    camera_id: Optional[int] = None
    video_name: str = Field(..., max_length=255)
    source: Optional[str] = Field(None, max_length=100)
    file_path: Optional[str] = Field(
        None, description="Reference/path to the video file. Never the binary itself."
    )
    started_at: Optional[datetime] = None
    ended_at: Optional[datetime] = None


class VideoCreate(VideoBase):
    pass


class VideoUpdate(BaseModel):
    camera_id: Optional[int] = None
    video_name: Optional[str] = Field(None, max_length=255)
    source: Optional[str] = Field(None, max_length=100)
    file_path: Optional[str] = None
    started_at: Optional[datetime] = None
    ended_at: Optional[datetime] = None


class VideoOut(VideoBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    created_at: datetime
