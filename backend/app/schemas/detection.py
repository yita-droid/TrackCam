from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, model_validator

DetectionSource = Literal["ground_truth", "model_prediction"]


class DetectionBase(BaseModel):
    frame_id: int
    class_id: int
    class_name: str = Field(..., max_length=100)
    confidence: Optional[float] = Field(None, ge=0, le=1)
    x_center: float = Field(..., ge=0, le=1)
    y_center: float = Field(..., ge=0, le=1)
    width: float = Field(..., ge=0, le=1)
    height: float = Field(..., ge=0, le=1)
    source: DetectionSource

    @model_validator(mode="after")
    def ground_truth_has_no_confidence(self):
        if self.source == "ground_truth" and self.confidence is not None:
            raise ValueError("confidence must be NULL for source='ground_truth' rows")
        return self


class DetectionCreate(DetectionBase):
    pass


class DetectionOut(DetectionBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    created_at: datetime
