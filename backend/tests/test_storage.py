import threading

from finreq.models import ApprovalRecord, AuditEvent, ApprovalStatus, Requirement, RiskItem, RiskLevel
from finreq.storage import in_memory_store


def _sample_requirement(req_id="FR-LOAN-001"):
    return Requirement(id=req_id, statement="The system shall do X.", source_stakeholder="loan_officer")


def test_save_and_get_requirement_round_trips():
    store = in_memory_store()
    req = _sample_requirement()
    store.save_requirement(req)
    fetched = store.get_requirement(req.id)
    assert fetched is not None
    assert fetched.statement == req.statement


def test_save_requirement_upserts_on_same_id():
    store = in_memory_store()
    req = _sample_requirement()
    store.save_requirement(req)
    req.approval_status = ApprovalStatus.APPROVED
    store.save_requirement(req)
    assert len(store.all_requirements()) == 1
    assert store.get_requirement(req.id).approval_status == ApprovalStatus.APPROVED


def test_get_requirement_missing_returns_none():
    store = in_memory_store()
    assert store.get_requirement("nope") is None


def test_risk_and_approval_and_audit_round_trip():
    store = in_memory_store()
    req = _sample_requirement()
    store.save_requirement(req)

    risk = RiskItem(
        related_requirement_id=req.id, category="security",
        description="x", likelihood="high", impact="high", risk_level=RiskLevel.HIGH,
    )
    store.save_risk(risk)
    assert store.all_risks()[0].related_requirement_id == req.id

    approval = ApprovalRecord(target_type="requirement", target_id=req.id, action="accept", actor_role="ba")
    store.save_approval(approval)
    assert len(store.approvals_for(req.id)) == 1

    event = AuditEvent(agent="extraction", event_type="decision", payload="{}")
    store.log_event(event)
    assert len(store.all_events()) == 1


def test_store_can_be_used_from_a_different_thread_than_it_was_created_on():
    # Regression test: API requests and analysis threads share one Store.
    store = in_memory_store()
    req = _sample_requirement()
    errors = []

    def worker():
        try:
            store.save_requirement(req)
            store.log_event(AuditEvent(agent="x", event_type="decision", payload="{}"))
        except Exception as exc:  # noqa: BLE001
            errors.append(exc)

    thread = threading.Thread(target=worker)
    thread.start()
    thread.join()

    assert errors == []
    assert store.get_requirement(req.id) is not None


def test_events_come_back_in_insertion_order():
    store = in_memory_store()
    for agent in ("zeta", "alpha", "mid"):  # ids are random hex; order must not depend on them
        store.log_event(AuditEvent(agent=agent, event_type="prompt", payload="{}"))
    assert [e.agent for e in store.all_events()] == ["zeta", "alpha", "mid"]
