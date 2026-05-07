from datetime import datetime
from typing import Optional, Any
from pydantic import BaseModel, Field


class ScanRequest(BaseModel):
    prompt: str = Field(..., min_length=1, max_length=32000, description="The user message to scan")
    app_id: Optional[str] = Field(None, description="Identifier for the calling application")
    metadata: Optional[dict[str, Any]] = Field(None, description="Extra metadata to store with the event")


class MatchedRule(BaseModel):
    rule_id: str
    name: str
    category: str
    severity: str
    description: Optional[str] = None


class ScanResponse(BaseModel):
    verdict: str                          # ALLOW | BLOCK
    category: Optional[str] = None
    severity: Optional[str] = None
    matched_rule: Optional[MatchedRule] = None
    confidence: Optional[float] = None
    scan_duration_ms: float
    event_id: str


class ScanEventOut(BaseModel):
    id: str
    app_id: Optional[str]
    prompt: str
    verdict: str
    category: Optional[str]
    severity: Optional[str]
    matched_rule: Optional[str]
    confidence: Optional[float]
    scan_duration_ms: Optional[float]
    created_at: datetime

    model_config = {"from_attributes": True}


class StatsResponse(BaseModel):
    total_scans: int
    blocked: int
    allowed: int
    block_rate: float
    by_category: dict[str, int]
    by_severity: dict[str, int]
    avg_scan_duration_ms: float


class RuleOut(BaseModel):
    rule_id: str
    name: str
    category: str
    severity: str
    description: Optional[str]
    enabled: bool

    model_config = {"from_attributes": True}
