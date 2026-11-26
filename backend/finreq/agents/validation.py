"""Validation agent: the last automated gate before a requirement is put in
front of a human (spec step 10's "requirements that fail these checks
should be returned to the clarification agent").

Deterministic classification of each requirement's `approval_status`:
- an issue that means the requirement itself is unclear, incomplete, or
  untestable sends it back to `NEEDS_CLARIFICATION` (more stakeholder input
  is needed, not a human decision yet);
- an issue that means two well-formed requirements disagree, or a control
  is missing, still leaves the requirement well-formed — it goes to
  `PENDING_REVIEW` so a human (officer) can decide, per the
  human-in-the-loop constraint, rather than looping back to the
  stakeholder.
"""
from __future__ import annotations

from finreq.models import ApprovalStatus, QualityIssueType, Requirement

_CLARIFICATION_TRIGGERS = {
    QualityIssueType.AMBIGUITY,
    QualityIssueType.INCOMPLETENESS,
    QualityIssueType.NOT_TESTABLE,
    QualityIssueType.MISSING_SOURCE,
    QualityIssueType.UNDEFINED_TERMINOLOGY,
    QualityIssueType.INFEASIBILITY,
    QualityIssueType.INCONSISTENCY,
}


class ValidationAgent:
    name = "validation"

    def run(self, requirement: Requirement) -> ApprovalStatus:
        issue_types = {i.issue_type for i in requirement.quality_issues}
        status = (
            ApprovalStatus.NEEDS_CLARIFICATION
            if issue_types & _CLARIFICATION_TRIGGERS
            else ApprovalStatus.PENDING_REVIEW
        )
        requirement.approval_status = status
        return status

    def validate_all(self, requirements: list[Requirement]) -> None:
        for req in requirements:
            self.run(req)
