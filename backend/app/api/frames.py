from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.database.connection import get_db
from app.models.frame import Frame
from app.schemas.frame import FrameCreate, FrameOut

router = APIRouter()


@router.get("", response_model=list[FrameOut])
def list_frames(video_id: Optional[int] = None, db: Session = Depends(get_db)):
    stmt = select(Frame)
    if video_id is not None:
        stmt = stmt.where(Frame.video_id == video_id)
    stmt = stmt.order_by(Frame.frame_number)
    return db.execute(stmt).scalars().all()


@router.get("/{frame_id}", response_model=FrameOut)
def get_frame(frame_id: int, db: Session = Depends(get_db)):
    frame = db.get(Frame, frame_id)
    if not frame:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Frame not found")
    return frame


@router.post("", response_model=FrameOut, status_code=status.HTTP_201_CREATED)
def create_frame(payload: FrameCreate, db: Session = Depends(get_db)):
    frame = Frame(**payload.model_dump())
    db.add(frame)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            "duplicate frame_number for this video_id, or video_id invalid",
        ) from exc
    db.refresh(frame)
    return frame


@router.delete("/{frame_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_frame(frame_id: int, db: Session = Depends(get_db)):
    frame = db.get(Frame, frame_id)
    if not frame:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Frame not found")
    db.delete(frame)
    db.commit()
