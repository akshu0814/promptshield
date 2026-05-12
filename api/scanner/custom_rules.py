import re
import logging
from dataclasses import dataclass
from typing import Optional
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

SEVERITY_RANK = {"low": 1, "medium": 2, "high": 3, "critical": 4}


@dataclass
class CustomRuleMatch:
    rule_id: str
    name: str
    category: str
    severity: str
    description: Optional[str] = None


@dataclass
class _CompiledCustomRule:
    rule_id: str
    name: str
    category: str
    severity: str
    description: Optional[str]
    pattern: re.Pattern
    enabled: bool


_cache: list[_CompiledCustomRule] = []


def reload_from_db(db: Session) -> None:
    global _cache
    from models.database import Rule
    rules = db.query(Rule).filter(Rule.source == "custom").all()
    compiled = []
    for rule in rules:
        try:
            compiled.append(_CompiledCustomRule(
                rule_id=rule.rule_id,
                name=rule.name,
                category=rule.category,
                severity=rule.severity,
                description=rule.description,
                pattern=re.compile(rule.pattern, re.IGNORECASE),
                enabled=rule.enabled if rule.enabled is not None else True,
            ))
        except re.error as e:
            logger.warning("Skipping custom rule %s — invalid regex: %s", rule.rule_id, e)
    compiled.sort(key=lambda r: SEVERITY_RANK.get(r.severity, 0), reverse=True)
    _cache = compiled
    logger.info("Custom rules cache: %d rules loaded", len(_cache))


def scan_custom(text: str) -> Optional[CustomRuleMatch]:
    for rule in _cache:
        if rule.enabled and rule.pattern.search(text):
            return CustomRuleMatch(
                rule_id=rule.rule_id,
                name=rule.name,
                category=rule.category,
                severity=rule.severity,
                description=rule.description,
            )
    return None
