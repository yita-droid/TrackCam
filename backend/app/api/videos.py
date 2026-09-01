from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.database.connection import get_db
from app.models.video import Video
from app.schemas.video import VideoCreate, VideoOut, VideoUpdate

router = APIRouter()


@router.get("", response_model=list[VideoOut])
def list_videos(camera_id: Optional[int] = None, db: Session = Depends(get_db)):
    stmt = select(Video)
    if camera_id is not None:
        stmt = stmt.where(Video.camera_id == camera_id)
    stmt = stmt.order_by(Video.created_at.desc())
    return db.execute(stmt).scalars().all()


@router.get("/{video_id}", response_model=VideoOut)
def get_video(video_id: int, db: Session = Depends(get_db)):
    video = db.get(Video, video_id)
    if not video:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Video not found")
    return video


@router.post("", response_model=VideoOut, status_code=status.HTTP_201_CREATED)
def create_video(payload: VideoCreate, db: Session = Depends(get_db)):
    video = Video(**payload.model_dump())
    db.add(video)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status.HTTP_409_CONFLICT, "video_id already exists or camera_id invalid") from exc
    db.refresh(video)
    return video


@router.patch("/{video_id}", response_model=VideoOut)
def update_video(video_id: int, payload: VideoUpdate, db: Session = Depends(get_db)):
    video = db.get(Video, video_id)
    if not video:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Video not found")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(video, field, value)
    db.commit()
    db.refresh(video)
    return video


@router.delete("/{video_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_video(video_id: int, db: Session = Depends(get_db)):
    video = db.get(Video, video_id)
    if not video:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Video not found")
    db.delete(video)
    db.commit()
