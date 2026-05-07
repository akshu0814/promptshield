import time
import uuid
import logging
from typing import Optional, Union
from sqlalchemy.orm import Session

from scanner.rule_engine import get_engine, RuleMatch
from scanner.ml_classifier import get_classifier, MLMatch
from models.database import ScanEvent
from models.schemas import ScanRequest, ScanResponse, MatchedRule

logger = logging.getLogger(__name__)

HIGH_SEVERITY_LEVELS = {"high", "critical"}

# Union type — a match can come from regex or ML
AnyMatch = Union[RuleMatch, MLMatch]


def _build_response(
    verdict: str,
    match: Optional[AnyMatch],
    duration_ms: float,
    event_id: str,
    confidence: Optional[float] = None,
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
        confidence=confidence if confidence is not None else (1.0 if match else None),
        scan_duration_ms=round(duration_ms, 3),
        event_id=event_id,
    )


def run_scan(request: ScanRequest, db: Session) -> ScanResponse:
    """
    Two-layer scan pipeline:
      Layer 1 — Regex rule engine  (<1ms)   catches known patterns
      Layer 2 — ML classifier      (10-30ms) catches subtle attacks regex misses
    Returns ScanResponse and persists a ScanEvent to the database.
    """
    start = time.perf_counter()
    event_id = str(uuid.uuid4())

    match: Optional[AnyMatch] = None
    verdict = "ALLOW"
    confidence: Optional[float] = None
    layer_used = "regex"

    # ── Layer 1: Regex rule engine ────────────────────────────────────────────
    try:
        rule_engine = get_engine()
        regex_match = rule_engine.scan(request.prompt)
        if regex_match:
            match = regex_match
            verdict = "BLOCK"
            confidence = 1.0
    except Exception as e:
        logger.error("Regex engine error during scan %s: %s", event_id, e)

    # ── Layer 2: ML classifier (only runs if regex said ALLOW) ────────────────
    if verdict == "ALLOW":
        try:
            classifier = get_classifier()
            if classifier.is_loaded:
                ml_match = classifier.classify(request.prompt)
                if ml_match:
                    match = ml_match
                    verdict = "BLOCK"
                    confidence = ml_match.confidence
                    layer_used = "ml"
        except Exception as e:
            logger.error("ML classifier error during scan %s: %s", event_id, e)
            # Fail-open: ML error → keep verdict as ALLOW

    duration_ms = (time.perf_counter() - start) * 1000
    logger.info(
        "Scan %s | verdict=%s | layer=%s | duration=%.2fms",
        event_id, verdict, layer_used, duration_ms
    )

    # ── Persist to PostgreSQL ─────────────────────────────────────────────────
    try:
        event = ScanEvent(
            id=event_id,
            app_id=request.app_id,
            prompt=request.prompt,
            verdict=verdict,
            category=match.category if match else None,
            severity=match.severity if match else None,
            matched_rule=match.rule_id if match else None,
            confidence=confidence,
            scan_duration_ms=duration_ms,
            metadata_=request.metadata,
        )
        db.add(event)
        db.commit()
    except Exception as e:
        logger.error("Failed to persist scan event %s: %s", event_id, e)
        db.rollback()

    return _build_response(verdict, match, duration_ms, event_id, confidence)
