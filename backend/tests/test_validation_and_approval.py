import pytest

from finreq.agents.approval import InvalidApprovalAction, record_decision
from finreq.agents.validation import ValidationAgent
from finreq.models import ApprovalStatus, QualityIssue, QualityIssueType, Requirement
from finreq.storage import in_memory_store


def _req(**overrides):
    base = dict(id="FR-LOAN-001", statement="The system shall do X.", source_stakeholder="x")
    base.update(overrides)
    return Requirement(**base)


def test_clean_requirement_goes_to_pending_review():
    req = _req()
    status = ValidationAgent().run(req)
    assert status == ApprovalStatus.PENDING_REVIEW
    assert req.approval_status == ApprovalStatus.PENDING_REVIEW


def test_ambiguity_issue_sends_back_to_clarification():
    req = _req(quality_issues=[QualityIssue(issue_type=QualityIssueType.AMBIGUITY, detail="vague")])
    status = ValidationAgent().run(req)
    assert status == ApprovalStatus.NEEDS_CLARIFICATION


def test_missing_control_alone_does_not_block_on_clarification():
    req = _req(quality_issues=[QualityIssue(issue_type=QualityIssueType.MISSING_CONTROL, detail="gap")])
    status = ValidationAgent().run(req)
    assert status == ApprovalStatus.PENDING_REVIEW


def test_conflicting_expectations_alone_does_not_block_on_clarification():
    req = _req(quality_issues=[QualityIssue(issue_type=QualityIssueType.CONFLICTING_EXPECTATIONS, detail="x")])
    status = ValidationAgent().run(req)
    assert status == ApprovalStatus.PENDING_REVIEW


def test_record_decision_accept_sets_approved_and_persists():
    store = in_memory_store()
    req = _req()
    store.save_requirement(req)
    record = record_decision(store, req, action="accept", actor_role="business_analyst")
    assert req.approval_status == ApprovalStatus.APPROVED
    assert store.get_requirement(req.id).approval_status == ApprovalStatus.APPROVED
    assert store.approvals_for(req.id) == [record]


def test_record_decision_reject_sets_rejected():
    store = in_memory_store()
    req = _req()
    store.save_requirement(req)
    record_decision(store, req, action="reject", actor_role="compliance_officer", note="not in scope")
    assert req.approval_status == ApprovalStatus.REJECTED


def test_record_decision_rejects_unknown_action():
    store = in_memory_store()
    req = _req()
    with pytest.raises(InvalidApprovalAction):
        record_decision(store, req, action="approve_forever", actor_role="x")
