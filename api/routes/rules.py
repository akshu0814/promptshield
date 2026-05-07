from fastapi import APIRouter
from models.schemas import RuleOut
from scanner.rule_engine import get_engine

router = APIRouter()


@router.get("/rules", response_model=list[RuleOut])
def list_rules():
    """Return all loaded detection rules."""
    engine = get_engine()
    return [
        RuleOut(
            rule_id=r.rule_id,
            name=r.name,
            category=r.category,
            severity=r.severity,
            description=r.description,
            enabled=True,
        )
        for r in engine.rules
    ]
