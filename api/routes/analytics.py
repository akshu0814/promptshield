from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func
from sqlalchemy.orm import Session

from models.database import get_db, ScanEvent
from models.schemas import TimeseriesResponse, TimeseriesBucket, BreakdownResponse

router = APIRouter()


@router.get("/stats/timeseries", response_model=TimeseriesResponse, tags=["Analytics"])
def get_timeseries(
    hours: int = Query(default=24, ge=1, le=168, description="Lookback window in hours (max 168 = 7 days)"),
    db: Session = Depends(get_db),
):
    """Attacks per hour for the last N hours."""
    cutoff = datetime.utcnow() - timedelta(hours=hours)

    dialect = db.bind.dialect.name
    if dialect == "sqlite":
        bucket_expr = func.strftime("%Y-%m-%dT%H:00:00", ScanEvent.created_at).label("bucket")
    else:
        bucket_expr = func.date_trunc("hour", ScanEvent.created_at).label("bucket")

    rows = (
        db.query(
            bucket_expr,
            ScanEvent.verdict,
            func.count(ScanEvent.id).label("count"),
        )
        .filter(ScanEvent.created_at >= cutoff)
        .group_by("bucket", ScanEvent.verdict)
        .order_by("bucket")
        .all()
    )

    buckets: dict[str, dict] = {}
    for bucket, verdict, count in rows:
        ts = bucket.isoformat()
        if ts not in buckets:
            buckets[ts] = {"timestamp": ts, "total": 0, "blocked": 0, "allowed": 0}
        buckets[ts]["total"] += count
        if verdict == "BLOCK":
            buckets[ts]["blocked"] += count
        else:
            buckets[ts]["allowed"] += count

    return TimeseriesResponse(
        hours=hours,
        buckets=[TimeseriesBucket(**v) for v in buckets.values()],
    )


@router.get("/stats/breakdown", response_model=BreakdownResponse, tags=["Analytics"])
def get_breakdown(db: Session = Depends(get_db)):
    """Blocked scan counts grouped by category and severity."""
    total_blocked = (
        db.query(func.count(ScanEvent.id))
        .filter(ScanEvent.verdict == "BLOCK")
        .scalar() or 0
    )

    by_category_rows = (
        db.query(ScanEvent.category, func.count(ScanEvent.id))
        .filter(ScanEvent.verdict == "BLOCK", ScanEvent.category.isnot(None))
        .group_by(ScanEvent.category)
        .all()
    )

    by_severity_rows = (
        db.query(ScanEvent.severity, func.count(ScanEvent.id))
        .filter(ScanEvent.verdict == "BLOCK", ScanEvent.severity.isnot(None))
        .group_by(ScanEvent.severity)
        .all()
    )

    return BreakdownResponse(
        by_category={row[0]: row[1] for row in by_category_rows},
        by_severity={row[0]: row[1] for row in by_severity_rows},
        total_blocked=total_blocked,
    )
