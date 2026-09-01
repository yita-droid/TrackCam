from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field

AlertType = Literal[
    "watchlist", "suspicious_vehicle", "anomaly", "traffic_congestion", "unknown_plate", "system"
]
AlertSeverity = Literal["low", "medium", "high", "critical"]
AlertStatus = Literal["active", "acknowledged", "resolved"]


class AlertBase(BaseModel):
    vehicle_id: Optional[int] = None
    plate_id: Optional[int] = None
    camera_id: Optional[int] = None
    alert_type: AlertType
    severity: AlertSeverity
    confidence: Optional[float] = Field(None, ge=0, le=1)
    message: Optional[str] = None
    status: AlertStatus = "active"


class AlertCreate(AlertBase):
    pass


class AlertUpdate(BaseModel):
    status: Optional[AlertStatus] = None
    message: Optional[str] = None
    resolved_at: Optional[datetime] = None


class AlertOut(AlertBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    created_at: datetime
    resolved_at: Optional[datetime] = None
