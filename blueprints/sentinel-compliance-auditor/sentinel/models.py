from __future__ import annotations

from enum import Enum
from pydantic import BaseModel


class ComplianceLevel(str, Enum):
    COMPLIANT = "compliant"
    PARTIAL = "partial"
    GAP = "gap"


class Severity(str, Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


class SOPChunk(BaseModel):
    sop_id: str
    title: str
    business_unit: str
    chunk_text: str
    section: str = ""
    page_estimate: int = 0
    score: float = 0.0


class AuditFinding(BaseModel):
    clause_id: str
    clause_title: str
    regulation: str
    sop_id: str
    sop_title: str
    business_unit: str
    compliance_level: ComplianceLevel
    severity: Severity
    evidence_quote: str = ""
    gap_description: str = ""
    remediation: str = ""
    reasoning: str = ""


class AuditMetrics(BaseModel):
    total_clauses: int = 0
    total_sops_audited: int = 0
    total_findings: int = 0
    compliant_count: int = 0
    partial_count: int = 0
    gap_count: int = 0
    critical_count: int = 0
    high_count: int = 0
    medium_count: int = 0
    low_count: int = 0
    total_tokens: int = 0
    total_retrieval_steps: int = 0
    avg_latency_per_cell: float = 0.0
    total_latency: float = 0.0
    total_cost: float = 0.0


