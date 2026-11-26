"""Risk-analysis agent.

Deterministic, rule-based scoring (same reasoning as quality.py: risk
scores must be explainable and reproducible for an audit, not a black-box
LLM judgment). Combines requirement category, priority, unresolved
compliance gaps, other quality issues and cross-requirement conflicts into
one risk score, then emits a `RiskItem` an auditor can trace back to the
exact factors that produced it.
"""
from __future__ import annotations

from finreq.models import Priority, QualityIssueType, Requirement, RequirementCategory, RiskItem, RiskLevel

_CATEGORY_BASE_SCORE = {
    RequirementCategory.SECURITY: 0.30,
    RequirementCategory.PRIVACY: 0.30,
    RequirementCategory.REGULATORY: 0.30,
    RequirementCategory.AUDIT_REPORTING: 0.20,
}
_PRIORITY_WEIGHT = {
    Priority.CRITICAL: 0.30,
    Priority.HIGH: 0.20,
    Priority.MEDIUM: 0.10,
    Priority.LOW: 0.0,
}
_HIGH_IMPACT_CATEGORIES = {
    RequirementCategory.SECURITY, RequirementCategory.PRIVACY,
    RequirementCategory.REGULATORY, RequirementCategory.AUDIT_REPORTING,
}


def _risk_category(requirement: Requirement) -> str:
    if any(m.gap for m in requirement.compliance_mappings):
        return "compliance"
    cats = set(requirement.categories)
    if cats & {RequirementCategory.SECURITY, RequirementCategory.PRIVACY}:
        return "security"
    if cats & {RequirementCategory.REGULATORY, RequirementCategory.AUDIT_REPORTING}:
        return "compliance"
    if cats & {RequirementCategory.PERFORMANCE, RequirementCategory.AVAILABILITY_RELIABILITY,
               RequirementCategory.INTEGRATION, RequirementCategory.DATA_MANAGEMENT,
               RequirementCategory.OPERATIONAL_MAINTENANCE}:
        return "technical"
    return "business"


def _score_to_level(score: float) -> RiskLevel:
    if score >= 0.70:
        return RiskLevel.CRITICAL
    if score >= 0.50:
        return RiskLevel.HIGH
    if score >= 0.25:
        return RiskLevel.MEDIUM
    return RiskLevel.LOW


def _band(score: float) -> str:
    return {"low": "low", "medium": "medium", "high": "high"}[
        "low" if score < 0.34 else ("medium" if score < 0.67 else "high")
    ]


def assess(requirement: Requirement) -> RiskItem:
    gaps = [m for m in requirement.compliance_mappings if m.gap]
    other_issues = [i for i in requirement.quality_issues if i.issue_type != QualityIssueType.MISSING_CONTROL]

    score = max([_CATEGORY_BASE_SCORE.get(c, 0.0) for c in requirement.categories] or [0.05])
    score += _PRIORITY_WEIGHT.get(requirement.priority, 0.10)
    score += min(0.15 * len(gaps), 0.30)
    score += min(0.05 * len(other_issues), 0.20)
    score += 0.20 if requirement.conflicts_with else 0.0
    score = min(score, 1.0)

    reasons = []
    if gaps:
        reasons.append(f"{len(gaps)} unresolved compliance gap(s)")
    if requirement.conflicts_with:
        reasons.append(f"conflicts with {', '.join(requirement.conflicts_with)}")
    if other_issues:
        reasons.append(f"{len(other_issues)} open quality issue(s)")
    if set(requirement.categories) & _HIGH_IMPACT_CATEGORIES:
        reasons.append("touches a security/privacy/regulatory category")

    mitigation = (
        "Route to the relevant officer for review before approval: " + "; ".join(reasons) + "."
        if reasons else
        "No elevated risk factors identified; standard review is sufficient."
    )

    return RiskItem(
        related_requirement_id=requirement.id,
        category=_risk_category(requirement),
        description=f"Risk assessment for {requirement.id}: {', '.join(reasons) if reasons else 'no elevated factors'}.",
        likelihood=_band(min(0.20 * len(other_issues) + (0.3 if requirement.conflicts_with else 0), 1.0)),
        impact=_band(score),
        risk_level=_score_to_level(score),
        mitigation=mitigation,
    )


class RiskAnalysisAgent:
    """Not an LLM agent — kept class-based (rather than a bare function) so
    it composes the same way as the other pipeline stages."""
    name = "risk_analysis"

    def run(self, requirement: Requirement) -> RiskItem:
        """Also mutates `requirement.risk_level` in place, matching every
        other agent's convention — the risk register and the requirement
        record must agree on one risk level, not carry two different ones."""
        risk_item = assess(requirement)
        requirement.risk_level = risk_item.risk_level
        return risk_item

    def assess_all(self, requirements: list[Requirement]) -> list[RiskItem]:
        return [self.run(r) for r in requirements]
