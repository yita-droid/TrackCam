from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field

VehicleType = Literal["car", "truck", "bus", "motorcycle", "van", "unknown"]


class VehicleBase(BaseModel):
    vehicle_id: str = Field(..., max_length=50)
    track_id: Optional[str] = Field(None, max_length=100)
    plate_id: Optional[int] = None
    vehicle_type: Optional[VehicleType] = None
    color: Optional[str] = Field(None, max_length=50)
    first_seen: Optional[datetime] = None
    last_seen: Optional[datetime] = None
    current_camera_id: Optional[int] = None


class VehicleCreate(VehicleBase):
    pass


class VehicleUpdate(BaseModel):
    track_id: Optional[str] = Field(None, max_length=100)
    plate_id: Optional[int] = None
    vehicle_type: Optional[VehicleType] = None
    color: Optional[str] = Field(None, max_length=50)
    first_seen: Optional[datetime] = None
    last_seen: Optional[datetime] = None
    current_camera_id: Optional[int] = None


class VehicleOut(VehicleBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    created_at: datetime
    updated_at: datetime
