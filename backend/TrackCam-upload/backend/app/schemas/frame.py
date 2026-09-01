from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class FrameBase(BaseModel):
    video_id: int
    frame_number: int = Field(..., ge=0)
    image_path: Optional[str] = Field(
        None, description="Reference/path to the frame image. Never the binary itself."
    )
    timestamp: Optional[datetime] = None
    width: Optional[int] = Field(None, gt=0)
    height: Optional[int] = Field(None, gt=0)


class FrameCreate(FrameBase):
    pass


class FrameOut(FrameBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    created_at: datetime
