import re
import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from models.database import get_db, Rule
from models.schemas import RuleOut, RuleCreate, RulePatch
from scanner.rule_engine import get_engine
from scanner.custom_rules import reload_from_db

router = APIRouter()

VALID_CATEGORIES = {"prompt_injection", "jailbreak", "extraction", "pii_exfiltration"}
VALID_SEVERITIES = {"low", "medium", "high", "critical"}


@router.get("/rules", response_model=list[RuleOut])
def list_rules(db: Session = Depends(get_db)):
    """Return all rules — YAML built-ins plus custom DB rules."""
    engine = get_engine()
    yaml_rules = [
        RuleOut(
            rule_id=r.rule_id,
            name=r.name,
            category=r.category,
            severity=r.severity,
            description=r.description,
            enabled=True,
            source="yaml",
        )
        for r in engine.rules
    ]

    custom_rules = [
        RuleOut(
            rule_id=r.rule_id,
            name=r.name,
            category=r.category,
            severity=r.severity,
            description=r.description,
            enabled=r.enabled,
            source="custom",
        )
        for r in db.query(Rule).filter(Rule.source == "custom").order_by(Rule.created_at.desc()).all()
    ]

    return yaml_rules + custom_rules


@router.post("/rules", response_model=RuleOut, status_code=status.HTTP_201_CREATED, tags=["Rules"])
def create_rule(payload: RuleCreate, db: Session = Depends(get_db)):
    """Create a custom detection rule."""
    if payload.category not in VALID_CATEGORIES:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"category must be one of: {', '.join(sorted(VALID_CATEGORIES))}",
        )
    if payload.severity not in VALID_SEVERITIES:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"severity must be one of: {', '.join(sorted(VALID_SEVERITIES))}",
        )
    try:
        re.compile(payload.pattern)
    except re.error as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Invalid regex pattern: {e}",
        )

    rule_id = f"CST-{uuid.uuid4().hex[:8].upper()}"
    rule = Rule(
        id=str(uuid.uuid4()),
        rule_id=rule_id,
        name=payload.name,
        category=payload.category,
        severity=payload.severity,
        pattern=payload.pattern,
        description=payload.description,
        enabled=True,
        source="custom",
    )
    db.add(rule)
    db.commit()
    db.refresh(rule)
    reload_from_db(db)

    return RuleOut(
        rule_id=rule.rule_id,
        name=rule.name,
        category=rule.category,
        severity=rule.severity,
        description=rule.description,
        enabled=rule.enabled,
        source=rule.source,
    )


@router.patch("/rules/{rule_id}", response_model=RuleOut, tags=["Rules"])
def toggle_rule(rule_id: str, payload: RulePatch, db: Session = Depends(get_db)):
    """Enable or disable a custom rule."""
    rule = db.query(Rule).filter(Rule.rule_id == rule_id, Rule.source == "custom").first()
    if not rule:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Custom rule not found — YAML rules cannot be toggled via API",
        )
    rule.enabled = payload.enabled
    db.commit()
    db.refresh(rule)
    reload_from_db(db)

    return RuleOut(
        rule_id=rule.rule_id,
        name=rule.name,
        category=rule.category,
        severity=rule.severity,
        description=rule.description,
        enabled=rule.enabled,
        source=rule.source,
    )


@router.delete("/rules/{rule_id}", status_code=status.HTTP_204_NO_CONTENT, tags=["Rules"])
def delete_rule(rule_id: str, db: Session = Depends(get_db)):
    """Delete a custom rule. YAML rules cannot be deleted."""
    rule = db.query(Rule).filter(Rule.rule_id == rule_id, Rule.source == "custom").first()
    if not rule:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Custom rule not found — YAML rules cannot be deleted via API",
        )
    db.delete(rule)
    db.commit()
    reload_from_db(db)
