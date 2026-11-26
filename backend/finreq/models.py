"""Core data structures shared by every agent and by storage/artifacts.

These follow the requirement record shape from the problem statement
(problem_statement.txt, "Requirement record"): every field the spec asks for is
represented, plus the traceability link back to the stakeholder statement.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class RequirementCategory(str, Enum):
    BUSINESS = "business"
    STAKEHOLDER = "stakeholder"
    FUNCTIONAL = "functional"
    SECURITY = "security"
    PRIVACY = "privacy"
    REGULATORY = "regulatory"
    PERFORMANCE = "performance"
    AVAILABILITY_RELIABILITY = "availability_reliability"
    USABILITY = "usability"
    DATA_MANAGEMENT = "data_management"
    INTEGRATION = "integration"
    AUDIT_REPORTING = "audit_reporting"
    OPERATIONAL_MAINTENANCE = "operational_maintenance"


class Priority(str, Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class RiskLevel(str, Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class ApprovalStatus(str, Enum):
    DRAFT = "draft"                # just extracted, not yet checked
    NEEDS_CLARIFICATION = "needs_clarification"
    PENDING_REVIEW = "pending_review"   # passed automated checks, awaiting human
    APPROVED = "approved"
    REJECTED = "rejected"
    NEEDS_REGENERATION = "needs_regeneration"


class QualityIssueType(str, Enum):
    AMBIGUITY = "ambiguity"
    INCOMPLETENESS = "incompleteness"
    INCONSISTENCY = "inconsistency"
    DUPLICATION = "duplication"
    INFEASIBILITY = "infeasibility"
    NOT_TESTABLE = "not_testable"
    MISSING_SOURCE = "missing_source"
    UNDEFINED_TERMINOLOGY = "undefined_terminology"
    CONFLICTING_EXPECTATIONS = "conflicting_expectations"
    MISSING_CONTROL = "missing_control"


class QualityIssue(BaseModel):
    issue_type: QualityIssueType
    detail: str
    related_requirement_id: Optional[str] = None


class Evidence(BaseModel):
    """One retrieved knowledge-base passage cited in support of a mapping or
    a generated statement. `confidence` is the retrieval similarity score,
    not a correctness guarantee."""
    source_id: str
    source_title: str
    jurisdiction: str
    effective_date: str
    version: str
    excerpt: str
    similarity: float


class ComplianceMapping(BaseModel):
    regulation_or_policy: str
    jurisdiction: str
    required_control: str
    evidence: list[Evidence] = Field(default_factory=list)
    gap: Optional[str] = None
    confidence: float = 0.0


class Requirement(BaseModel):
    id: str
    statement: str
    categories: list[RequirementCategory] = Field(default_factory=list)
    source_stakeholder: str
    source_excerpt: str = ""
    business_justification: str = ""
    priority: Priority = Priority.MEDIUM
    dependencies: list[str] = Field(default_factory=list)
    assumptions: list[str] = Field(default_factory=list)
    acceptance_criteria: list[str] = Field(default_factory=list)
    applicable_regulations: list[str] = Field(default_factory=list)
    risk_level: RiskLevel = RiskLevel.MEDIUM
    confidence_score: float = 0.0
    approval_status: ApprovalStatus = ApprovalStatus.DRAFT

    quality_issues: list[QualityIssue] = Field(default_factory=list)
    compliance_mappings: list[ComplianceMapping] = Field(default_factory=list)
    conflicts_with: list[str] = Field(default_factory=list)
    duplicate_of: Optional[str] = None

    created_at: str = Field(default_factory=_now_iso)
    updated_at: str = Field(default_factory=_now_iso)

    @staticmethod
    def new_id(domain_tag: str, seq: int) -> str:
        return f"FR-{domain_tag.upper()}-{seq:03d}"


class RiskItem(BaseModel):
    id: str = Field(default_factory=lambda: f"RISK-{uuid.uuid4().hex[:8]}")
    related_requirement_id: str
    category: str  # business | technical | compliance | security
    description: str
    likelihood: str  # low | medium | high
    impact: str      # low | medium | high
    risk_level: RiskLevel
    mitigation: str = ""


class ApprovalRecord(BaseModel):
    """One row of the audit trail: who decided what, on which artefact."""
    id: str = Field(default_factory=lambda: f"APR-{uuid.uuid4().hex[:8]}")
    target_type: str  # "requirement" | "sdlc_recommendation" | ...
    target_id: str
    action: str        # accept | reject | modify | regenerate
    actor_role: str     # e.g. "business_analyst", "compliance_officer"
    note: str = ""
    timestamp: str = Field(default_factory=_now_iso)


class AuditEvent(BaseModel):
    """One row of the full audit log: every prompt, retrieval, agent
    decision and artefact generation, per the spec's 'audit everything'
    constraint."""
    id: str = Field(default_factory=lambda: f"EVT-{uuid.uuid4().hex[:8]}")
    agent: str
    event_type: str  # "prompt" | "retrieval" | "decision" | "artifact"
    payload: str      # JSON-serialised details
    timestamp: str = Field(default_factory=_now_iso)
