from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class LicensePlateBase(BaseModel):
    detection_id: Optional[int] = None
    plate_number: Optional[str] = Field(
        None, max_length=30, description="NULL until a real OCR/ANPR model produces this."
    )
    ocr_text_raw: Optional[str] = None
    ocr_confidence: Optional[float] = Field(None, ge=0, le=1)
    verified: bool = False


class LicensePlateCreate(LicensePlateBase):
    pass


class LicensePlateUpdate(BaseModel):
    plate_number: Optional[str] = Field(None, max_length=30)
    ocr_text_raw: Optional[str] = None
    ocr_confidence: Optional[float] = Field(None, ge=0, le=1)
    verified: Optional[bool] = None


class LicensePlateOut(LicensePlateBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    created_at: datetime
