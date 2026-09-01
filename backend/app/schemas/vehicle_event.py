from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field

EventType = Literal[
    "detected",
    "entered_camera",
    "exited_camera",
    "plate_recognized",
    "vehicle_tracked",
    "cross_camera_match",
]


class VehicleEventBase(BaseModel):
    vehicle_id: int
    camera_id: Optional[int] = None
    frame_id: Optional[int] = None
    plate_id: Optional[int] = None
    event_type: EventType
    timestamp: datetime
    latitude: Optional[float] = Field(None, ge=-90, le=90)
    longitude: Optional[float] = Field(None, ge=-180, le=180)
    confidence: Optional[float] = Field(None, ge=0, le=1)


class VehicleEventCreate(VehicleEventBase):
    pass


class VehicleEventOut(VehicleEventBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    created_at: datetime
