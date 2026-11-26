from finreq.agents.conflict import ConflictDetectionAgent
from finreq.models import QualityIssueType, Requirement


def _req(rid, statement):
    return Requirement(id=rid, statement=statement, source_stakeholder="loan_officer")


def test_identical_statements_flagged_as_duplicate():
    reqs = [
        _req("FR-LOAN-001", "The system shall send an SMS alert after each disbursement."),
        _req("FR-LOAN-002", "The system shall send an SMS alert after each disbursement."),
    ]
    ConflictDetectionAgent(ctx=None).run(reqs)
    assert reqs[1].duplicate_of == "FR-LOAN-001"
    assert any(i.issue_type == QualityIssueType.DUPLICATION for i in reqs[1].quality_issues)


def test_differing_numeric_threshold_flagged_as_conflict_not_duplicate():
    reqs = [
        _req("FR-LOAN-001", "The system shall approve loan applications within 2 seconds."),
        _req("FR-LOAN-002", "The system shall approve loan applications within 5 seconds."),
    ]
    ConflictDetectionAgent(ctx=None).run(reqs)
    assert reqs[0].duplicate_of is None
    assert reqs[1].duplicate_of is None
    assert "FR-LOAN-002" in reqs[0].conflicts_with
    assert "FR-LOAN-001" in reqs[1].conflicts_with
    assert any(i.issue_type == QualityIssueType.CONFLICTING_EXPECTATIONS for i in reqs[0].quality_issues)


def test_negated_statement_flagged_as_conflict():
    reqs = [
        _req("FR-LOAN-001", "The system shall allow manual override of credit decisions."),
        _req("FR-LOAN-002", "The system shall not allow manual override of credit decisions."),
    ]
    ConflictDetectionAgent(ctx=None).run(reqs)
    assert "FR-LOAN-002" in reqs[0].conflicts_with


def test_unrelated_statements_are_not_flagged():
    reqs = [
        _req("FR-LOAN-001", "The system shall send an SMS alert after each disbursement."),
        _req("FR-LOAN-002", "The system shall encrypt customer data at rest using AES-256."),
    ]
    ConflictDetectionAgent(ctx=None).run(reqs)
    assert reqs[0].duplicate_of is None
    assert reqs[0].conflicts_with == []
    assert reqs[1].conflicts_with == []


def test_single_requirement_is_a_no_op():
    reqs = [_req("FR-LOAN-001", "The system shall send an SMS alert.")]
    ConflictDetectionAgent(ctx=None).run(reqs)  # should not raise
    assert reqs[0].conflicts_with == []
