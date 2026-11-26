from finreq.agents.quality import QualityCheckAgent
from finreq.models import QualityIssueType, Requirement


def _req(**overrides):
    base = dict(
        id="FR-LOAN-001",
        statement="The system shall approve loans within 2 seconds.",
        source_stakeholder="loan_officer",
        source_excerpt="Loans must be approved fast.",
        business_justification="Improves customer experience.",
        acceptance_criteria=["Approval decision returned in <= 2 seconds for 95% of requests."],
    )
    base.update(overrides)
    return Requirement(**base)


def test_clean_requirement_has_no_issues():
    agent = QualityCheckAgent(ctx=None)
    issues = agent.run(_req())
    assert issues == []


def test_vague_term_flagged_as_ambiguity():
    agent = QualityCheckAgent(ctx=None)
    issues = agent.run(_req(statement="The system shall respond appropriately."))
    types = [i.issue_type for i in issues]
    assert QualityIssueType.AMBIGUITY in types


def test_missing_modal_verb_flagged_as_ambiguity():
    agent = QualityCheckAgent(ctx=None)
    issues = agent.run(_req(statement="The system approves loans within 2 seconds."))
    assert any(i.issue_type == QualityIssueType.AMBIGUITY for i in issues)


def test_missing_acceptance_criteria_flagged_as_incomplete():
    agent = QualityCheckAgent(ctx=None)
    issues = agent.run(_req(acceptance_criteria=[]))
    assert any(i.issue_type == QualityIssueType.INCOMPLETENESS for i in issues)


def test_missing_source_excerpt_flagged():
    agent = QualityCheckAgent(ctx=None)
    issues = agent.run(_req(source_excerpt=""))
    assert any(i.issue_type == QualityIssueType.MISSING_SOURCE for i in issues)


def test_unknown_acronym_flagged_as_undefined_terminology():
    agent = QualityCheckAgent(ctx=None)
    issues = agent.run(_req(statement="The system shall integrate with the LMS within 2 seconds."))
    assert any(i.issue_type == QualityIssueType.UNDEFINED_TERMINOLOGY for i in issues)


def test_known_acronym_not_flagged():
    agent = QualityCheckAgent(ctx=None)
    issues = agent.run(_req(statement="The system shall verify KYC status within 2 seconds."))
    assert not any(i.issue_type == QualityIssueType.UNDEFINED_TERMINOLOGY for i in issues)


def test_absolute_guarantee_flagged_as_infeasible():
    agent = QualityCheckAgent(ctx=None)
    issues = agent.run(_req(statement="The system shall achieve 100% accuracy within 2 seconds."))
    assert any(i.issue_type == QualityIssueType.INFEASIBILITY for i in issues)


def test_check_all_mutates_each_requirement_in_place():
    agent = QualityCheckAgent(ctx=None)
    reqs = [_req(statement="The system approves loans appropriately.", acceptance_criteria=[])]
    agent.check_all(reqs)
    assert len(reqs[0].quality_issues) > 0
