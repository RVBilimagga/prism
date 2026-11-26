import pytest

from finreq.llm import FakeLLMClient
from finreq.models import ApprovalStatus
from finreq.pipeline import run_pipeline
from finreq.retrieval import KnowledgeBase
from finreq.storage import in_memory_store


def _responder(system: str, prompt: str):
    if "Stakeholder Interaction Agent" in system:
        return {"covered_topics": ["business objectives"], "questions": []}

    if "Requirement Extraction Agent" in system:
        return [
            {
                "statement": "The system shall require step-up authentication for transfers "
                              "exceeding the approved risk threshold.",
                "business_justification": "Reduce fraud on large transfers.",
                "priority": "high",
                "acceptance_criteria": ["Second factor required above threshold."],
                "assumptions": [],
                "dependencies": [],
                "source_excerpt": "We need extra verification for big transfers.",
            },
            {
                "statement": "The system shall send an SMS after disbursement.",
                "business_justification": "",
                "priority": "medium",
                "acceptance_criteria": [],
                "assumptions": [],
                "dependencies": [],
                "source_excerpt": "",
            },
        ]

    if "Classification Agent" in system:
        if "step-up authentication" in prompt:
            return {"categories": ["security"]}
        return {"categories": ["functional"]}

    if "Compliance Agent" in system:
        return {"mappings": [{
            "evidence_index": 0,
            "required_control": "Require step-up authentication above the risk threshold.",
            "gap": None,
        }]}

    raise AssertionError(f"unexpected system prompt reached the fake LLM: {system[:60]}")


def test_pipeline_end_to_end_produces_validated_requirements_and_risks():
    llm = FakeLLMClient(responder=_responder)
    kb = KnowledgeBase()
    store = in_memory_store()

    result = run_pipeline(
        "Contact me at ravi.k@example.com. We need extra verification for big transfers. "
        "Customers should get an SMS when money is out.",
        stakeholder_role="security_officer",
        domain_tag="LOAN",
        llm=llm, kb=kb, store=store,
    )

    assert [r.id for r in result.requirements] == ["FR-LOAN-001", "FR-LOAN-002"]

    req1, req2 = result.requirements
    # req1 is well-formed (has acceptance criteria, justification, source, a
    # grounded compliance mapping) -> ready for human review, not clarification
    assert req1.approval_status == ApprovalStatus.PENDING_REVIEW
    assert req1.categories
    assert req1.compliance_mappings and req1.compliance_mappings[0].gap is None

    # req2 is missing acceptance criteria, justification and source -> sent back
    assert req2.approval_status == ApprovalStatus.NEEDS_CLARIFICATION

    assert len(result.risks) == 2
    assert {r.related_requirement_id for r in result.risks} == {"FR-LOAN-001", "FR-LOAN-002"}

    # PII from the transcript was masked for every LLM call...
    for system, prompt in llm.calls:
        assert "ravi.k@example.com" not in prompt

    # ...but restored in the final, human-facing requirement fields.
    assert store.get_requirement("FR-LOAN-001") is not None
    assert result.events_logged > 0


def test_ask_clarifying_questions_false_skips_interaction_agent():
    def responder(system, prompt):
        if "Stakeholder Interaction Agent" in system:
            raise AssertionError("interaction agent should not have been called")
        if "Requirement Extraction Agent" in system:
            return []
        raise AssertionError(f"unexpected call: {system[:40]}")

    llm = FakeLLMClient(responder=responder)
    result = run_pipeline(
        "Some transcript.", stakeholder_role="ops",
        llm=llm, kb=KnowledgeBase(), store=in_memory_store(),
        ask_clarifying_questions=False,
    )
    assert result.requirements == []
    assert result.clarification.questions == []


def test_on_stage_callback_is_invoked_for_every_stage():
    llm = FakeLLMClient(responder=lambda system, prompt: [] if "Extraction" in system else {})
    stages: list[str] = []
    run_pipeline(
        "Some transcript.", stakeholder_role="ops",
        llm=llm, kb=KnowledgeBase(), store=in_memory_store(),
        ask_clarifying_questions=False, on_stage=stages.append,
    )
    assert len(stages) >= 6
    assert any("Extracting" in s for s in stages)
    assert any("quality checks" in s for s in stages)


def test_empty_transcript_is_rejected_before_any_model_call():
    llm = FakeLLMClient(responses=[])
    with pytest.raises(ValueError, match="empty"):
        run_pipeline("   \n", stakeholder_role="ops", llm=llm, kb=KnowledgeBase(), store=in_memory_store())
    assert llm.calls == []


def test_reanalysis_continues_numbering_instead_of_overwriting():
    store = in_memory_store()
    kwargs = dict(stakeholder_role="security_officer", domain_tag="LOAN", kb=KnowledgeBase(), store=store)
    first = run_pipeline("We need extra verification for big transfers.", llm=FakeLLMClient(responder=_responder), **kwargs)
    second = run_pipeline("We need extra verification for big transfers.", llm=FakeLLMClient(responder=_responder), **kwargs)
    assert [r.id for r in first.requirements] == ["FR-LOAN-001", "FR-LOAN-002"]
    assert [r.id for r in second.requirements] == ["FR-LOAN-003", "FR-LOAN-004"]
    assert len(store.all_requirements()) == 4
