import re
import os
import glob
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional
import yaml

logger = logging.getLogger(__name__)

SEVERITY_RANK = {"low": 1, "medium": 2, "high": 3, "critical": 4}


@dataclass
class RuleMatch:
    rule_id: str
    name: str
    category: str
    severity: str
    description: Optional[str] = None


@dataclass
class CompiledRule:
    rule_id: str
    name: str
    category: str
    severity: str
    description: Optional[str]
    pattern: re.Pattern


class RuleEngine:
    def __init__(self, rules_dir: Optional[str] = None):
        self._rules: list[CompiledRule] = []
        self._loaded = False
        if rules_dir:
            self.load(rules_dir)

    def load(self, rules_dir: str) -> None:
        rules_dir = Path(rules_dir)
        if not rules_dir.exists():
            raise FileNotFoundError(f"Rules directory not found: {rules_dir}")

        compiled: list[CompiledRule] = []
        for yaml_path in sorted(glob.glob(str(rules_dir / "*.yaml"))):
            try:
                with open(yaml_path) as f:
                    data = yaml.safe_load(f)
                for rule in data.get("rules", []):
                    try:
                        compiled.append(CompiledRule(
                            rule_id=rule["id"],
                            name=rule["name"],
                            category=rule["category"],
                            severity=rule["severity"],
                            description=rule.get("description"),
                            pattern=re.compile(rule["pattern"]),
                        ))
                    except re.error as e:
                        logger.warning("Skipping rule %s — invalid regex: %s", rule.get("id"), e)
            except Exception as e:
                logger.error("Failed to load rules from %s: %s", yaml_path, e)

        # Sort: critical → high → medium → low so we match highest severity first
        compiled.sort(key=lambda r: SEVERITY_RANK.get(r.severity, 0), reverse=True)
        self._rules = compiled
        self._loaded = True
        logger.info("Loaded %d rules from %s", len(self._rules), rules_dir)

    def scan(self, text: str) -> Optional[RuleMatch]:
        """Return the first (highest-severity) matching rule, or None."""
        for rule in self._rules:
            if rule.pattern.search(text):
                return RuleMatch(
                    rule_id=rule.rule_id,
                    name=rule.name,
                    category=rule.category,
                    severity=rule.severity,
                    description=rule.description,
                )
        return None

    def scan_all(self, text: str) -> list[RuleMatch]:
        """Return all matching rules."""
        return [
            RuleMatch(
                rule_id=rule.rule_id,
                name=rule.name,
                category=rule.category,
                severity=rule.severity,
                description=rule.description,
            )
            for rule in self._rules
            if rule.pattern.search(text)
        ]

    @property
    def rules(self) -> list[CompiledRule]:
        return self._rules

    @property
    def rule_count(self) -> int:
        return len(self._rules)


# Module-level singleton — loaded once at startup
_engine_instance: Optional[RuleEngine] = None


def get_engine() -> RuleEngine:
    global _engine_instance
    if _engine_instance is None:
        rules_dir = os.getenv("RULES_DIR", str(Path(__file__).parent.parent / "rules"))
        _engine_instance = RuleEngine(rules_dir)
    return _engine_instance


def reset_engine() -> None:
    """For testing — force a fresh engine on next get_engine() call."""
    global _engine_instance
    _engine_instance = None
