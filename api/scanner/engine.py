import time
import uuid
import logging
from typing import Optional
from sqlalchemy.orm import Session

from scanner.rule_engine import get_engine, RuleMatch
from models.database import ScanEvent
from models.schemas import ScanRequest, ScanResponse, MatchedRule

logger = logging.getLogger(__name__)

HIGH_SEVERITY_LEVELS = {"high", "critical"}


def _build_response(
    verdict: str,
    match: Optional[RuleMatch],
    duration_ms: float,
    event_id: str,
) -> ScanResponse:
    matched_rule_out = None
    if match:
        matched_rule_out = MatchedRule(
            rule_id=match.rule_id,
            name=match.name,
            category=match.category,
            severity=match.severity,
            description=match.description,
        )
    return ScanResponse(
        verdict=verdict,
        category=match.category if match else None,
        severity=match.severity if match else None,
        matched_rule=matched_rule_out,
        confidence=1.0 if match else None,
        scan_duration_ms=round(duration_ms, 3),
        event_id=event_id,
    )


def run_scan(request: ScanRequest, db: Session) -> ScanResponse:
    """
    Layer 1 pipeline: regex rule engine.
    HIGH/CRITICAL severity → block immediately.
    Returns ScanResponse and persists a ScanEvent to the database.
    """
    start = time.perf_counter()
    event_id = str(uuid.uuid4())
    engine = get_engine()

    match: Optional[RuleMatch] = None
    verdict = "ALLOW"

    try:
        match = engine.scan(request.prompt)
        if match:
            verdict = "BLOCK"
    except Exception as e:
        logger.error("Rule engine error during scan %s: %s", event_id, e)
        # Fail-open: unexpected engine error → allow
        verdict = "ALLOW"
        match = None

    duration_ms = (time.perf_counter() - start) * 1000

    # Persist to PostgreSQL
    try:
        event = ScanEvent(
            id=event_id,
            app_id=request.app_id,
            prompt=request.prompt,
            verdict=verdict,
            category=match.category if match else None,
            severity=match.severity if match else None,
            matched_rule=match.rule_id if match else None,
            confidence=1.0 if match else None,
            scan_duration_ms=duration_ms,
            metadata_=request.metadata,
        )
        db.add(event)
        db.commit()
    except Exception as e:
        logger.error("Failed to persist scan event %s: %s", event_id, e)
        db.rollback()

    return _build_response(verdict, match, duration_ms, event_id)
