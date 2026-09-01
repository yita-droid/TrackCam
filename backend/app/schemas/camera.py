from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field

CameraStatus = Literal["online", "offline", "maintenance"]
TrafficLevel = Literal["low", "medium", "high"]


class CameraBase(BaseModel):
    camera_id: str = Field(..., max_length=50)
    name: str = Field(..., max_length=150)
    location: Optional[str] = Field(None, max_length=255)
    latitude: Optional[float] = Field(None, ge=-90, le=90)
    longitude: Optional[float] = Field(None, ge=-180, le=180)
    status: CameraStatus
    traffic_level: Optional[TrafficLevel] = None
    vehicle_count: int = Field(0, ge=0)
    health: Optional[float] = Field(None, ge=0, le=100)


class CameraCreate(CameraBase):
    pass


class CameraUpdate(BaseModel):
    name: Optional[str] = Field(None, max_length=150)
    location: Optional[str] = Field(None, max_length=255)
    latitude: Optional[float] = Field(None, ge=-90, le=90)
    longitude: Optional[float] = Field(None, ge=-180, le=180)
    status: Optional[CameraStatus] = None
    traffic_level: Optional[TrafficLevel] = None
    vehicle_count: Optional[int] = Field(None, ge=0)
    health: Optional[float] = Field(None, ge=0, le=100)


class CameraOut(CameraBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    created_at: datetime
    updated_at: datetime
