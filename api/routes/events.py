import asyncio
import json
import logging
from typing import Optional
from fastapi import APIRouter, Depends, Query, WebSocket, WebSocketDisconnect
from sqlalchemy.orm import Session

from models.database import get_db, ScanEvent
from models.schemas import ScanEventOut
from routes.scan import get_broadcast_queue

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/events", response_model=list[ScanEventOut])
def list_events(
    limit: int = Query(50, ge=1, le=500),
    verdict: Optional[str] = Query(None, pattern="^(ALLOW|BLOCK)$"),
    category: Optional[str] = None,
    db: Session = Depends(get_db),
):
    """Return recent scan events, newest first."""
    q = db.query(ScanEvent).order_by(ScanEvent.created_at.desc())
    if verdict:
        q = q.filter(ScanEvent.verdict == verdict)
    if category:
        q = q.filter(ScanEvent.category == category)
    return q.limit(limit).all()


@router.websocket("/ws/events")
async def websocket_events(websocket: WebSocket):
    """
    Live stream of BLOCK events.
    Clients receive JSON messages whenever a prompt is blocked.
    """
    await websocket.accept()
    queue = get_broadcast_queue()
    logger.info("WebSocket client connected")
    try:
        while True:
            try:
                event = await asyncio.wait_for(queue.get(), timeout=30.0)
                await websocket.send_text(json.dumps(event))
            except asyncio.TimeoutError:
                # Send keepalive ping so the connection doesn't idle-close
                await websocket.send_text(json.dumps({"type": "ping"}))
    except WebSocketDisconnect:
        logger.info("WebSocket client disconnected")
    except Exception as e:
        logger.warning("WebSocket error: %s", e)
