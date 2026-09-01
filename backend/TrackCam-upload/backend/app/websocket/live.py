from __future__ import annotations

from datetime import datetime, timezone
from fastapi import APIRouter, WebSocket, WebSocketDisconnect

router = APIRouter(tags=["Live"])

@router.websocket("/ws/live")
async def live(websocket: WebSocket):
    await websocket.accept()
    try:
        await websocket.send_json({
            "type": "connected",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "message": "TrackCam live channel connected",
        })
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        return
