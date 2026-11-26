from finreq.agents.risk import RiskAnalysisAgent
from finreq.models import ComplianceMapping, Priority, Requirement, RequirementCategory, RiskLevel


def _req(**overrides):
    base = dict(id="FR-LOAN-001", statement="The system shall do X.", source_stakeholder="x")
    base.update(overrides)
    return Requirement(**base)


def test_plain_low_priority_functional_requirement_is_low_risk():
    req = _req(priority=Priority.LOW, categories=[RequirementCategory.FUNCTIONAL])
    risk = RiskAnalysisAgent().run(req)
    assert risk.risk_level == RiskLevel.LOW
    assert risk.related_requirement_id == req.id


def test_security_requirement_with_gap_is_high_or_critical():
    gap_mapping = ComplianceMapping(
        regulation_or_policy="none found", jurisdiction="unknown",
        required_control="", gap="no confident mapping found", confidence=0.1,
    )
    req = _req(
        priority=Priority.CRITICAL,
        categories=[RequirementCategory.SECURITY],
        compliance_mappings=[gap_mapping],
    )
    risk = RiskAnalysisAgent().run(req)
    assert risk.risk_level in (RiskLevel.HIGH, RiskLevel.CRITICAL)
    assert risk.category == "compliance"  # gap dominates category assignment
    assert "gap" in risk.mitigation.lower() or "gap" in risk.description.lower()


def test_conflicting_requirement_scores_higher_than_non_conflicting():
    plain = _req(categories=[RequirementCategory.FUNCTIONAL])
    conflicting = _req(categories=[RequirementCategory.FUNCTIONAL], conflicts_with=["FR-LOAN-099"])
    agent = RiskAnalysisAgent()
    plain_risk = agent.run(plain)
    conflict_risk = agent.run(conflicting)
    order = {"low": 0, "medium": 1, "high": 2, "critical": 3}
    assert order[conflict_risk.risk_level.value] >= order[plain_risk.risk_level.value]


def test_run_mutates_requirement_risk_level_to_match_the_risk_item():
    req = _req(
        priority=Priority.CRITICAL,
        categories=[RequirementCategory.SECURITY],
    )
    assert req.risk_level == RiskLevel.MEDIUM  # pydantic default, before assessment
    risk_item = RiskAnalysisAgent().run(req)
    assert req.risk_level == risk_item.risk_level
    assert req.risk_level in (RiskLevel.HIGH, RiskLevel.CRITICAL)


def test_assess_all_returns_one_risk_per_requirement():
    reqs = [_req(id="FR-LOAN-001"), _req(id="FR-LOAN-002")]
    risks = RiskAnalysisAgent().assess_all(reqs)
    assert {r.related_requirement_id for r in risks} == {"FR-LOAN-001", "FR-LOAN-002"}
