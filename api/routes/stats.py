from fastapi import APIRouter, Depends
from sqlalchemy import func
from sqlalchemy.orm import Session

from models.database import get_db, ScanEvent
from models.schemas import StatsResponse

router = APIRouter()


@router.get("/stats", response_model=StatsResponse)
def get_stats(db: Session = Depends(get_db)):
    """Aggregate statistics across all scan events."""
    total = db.query(func.count(ScanEvent.id)).scalar() or 0
    blocked = db.query(func.count(ScanEvent.id)).filter(ScanEvent.verdict == "BLOCK").scalar() or 0
    allowed = total - blocked

    by_category_rows = (
        db.query(ScanEvent.category, func.count(ScanEvent.id))
        .filter(ScanEvent.category.isnot(None))
        .group_by(ScanEvent.category)
        .all()
    )
    by_severity_rows = (
        db.query(ScanEvent.severity, func.count(ScanEvent.id))
        .filter(ScanEvent.severity.isnot(None))
        .group_by(ScanEvent.severity)
        .all()
    )
    avg_duration = db.query(func.avg(ScanEvent.scan_duration_ms)).scalar() or 0.0

    return StatsResponse(
        total_scans=total,
        blocked=blocked,
        allowed=allowed,
        block_rate=round(blocked / total, 4) if total else 0.0,
        by_category={row[0]: row[1] for row in by_category_rows},
        by_severity={row[0]: row[1] for row in by_severity_rows},
        avg_scan_duration_ms=round(float(avg_duration), 3),
    )
