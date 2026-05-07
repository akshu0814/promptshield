import asyncio
import logging
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from models.database import get_db
from models.schemas import ScanRequest, ScanResponse
from scanner.engine import run_scan
from alerts.webhooks import send_slack_alert

logger = logging.getLogger(__name__)

router = APIRouter()

# WebSocket broadcast queue — populated here, consumed in events.py
_broadcast_queue: asyncio.Queue = asyncio.Queue(maxsize=500)


def get_broadcast_queue() -> asyncio.Queue:
    return _broadcast_queue


@router.post("/scan", response_model=ScanResponse, status_code=status.HTTP_200_OK)
async def scan_prompt(request: ScanRequest, db: Session = Depends(get_db)):
    """
    Scan a user prompt for injection attacks.
    Returns verdict ALLOW or BLOCK with matched rule details.
    """
    try:
        response = run_scan(request, db)
    except Exception as e:
        logger.exception("Unexpected error in scan endpoint: %s", e)
        raise HTTPException(status_code=500, detail="Internal scan error")

    if response.verdict == "BLOCK":
        # Fire-and-forget: alert + broadcast (don't block the response)
        asyncio.create_task(_post_block_tasks(response))

    return response


async def _post_block_tasks(response: ScanResponse) -> None:
    try:
        await send_slack_alert(response)
    except Exception as e:
        logger.warning("Slack alert failed for event %s: %s", response.event_id, e)
    try:
        _broadcast_queue.put_nowait(response.model_dump())
    except asyncio.QueueFull:
        logger.warning("Broadcast queue full — dropping event %s", response.event_id)
