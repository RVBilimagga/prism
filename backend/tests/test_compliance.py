from finreq.agents.base import AgentContext
from finreq.agents.compliance import ComplianceAgent
from finreq.llm import FakeLLMClient
from finreq.models import Requirement
from finreq.retrieval import KnowledgeBase
from finreq.storage import in_memory_store


def _ctx(llm):
    return AgentContext(llm=llm, kb=KnowledgeBase(), store=in_memory_store())


def test_relevant_requirement_gets_grounded_mapping():
    llm = FakeLLMClient(responses=[{
        "mappings": [{
            "evidence_index": 0,
            "required_control": "Require step-up authentication above the risk threshold.",
            "gap": None,
        }],
    }])
    req = Requirement(
        id="FR-LOAN-001",
        statement="The system shall require step-up authentication for large transactions.",
        source_stakeholder="security_officer",
    )
    ComplianceAgent(_ctx(llm)).run(req)

    assert len(req.compliance_mappings) == 1
    mapping = req.compliance_mappings[0]
    assert mapping.gap is None
    assert mapping.evidence
    assert req.applicable_regulations == [mapping.regulation_or_policy]
    assert req.confidence_score > 0


def test_low_similarity_requirement_escalates_as_gap_without_calling_llm():
    llm = FakeLLMClient(responses=[])  # must not be called
    req = Requirement(
        id="FR-LOAN-002",
        statement="The system shall play a chime sound on login for aesthetic reasons.",
        source_stakeholder="ux_designer",
    )
    ComplianceAgent(_ctx(llm)).run(req)

    assert len(req.compliance_mappings) == 1
    assert req.compliance_mappings[0].gap is not None
    assert any(i.issue_type.value == "missing_control" for i in req.quality_issues)
    assert llm.calls == []


def test_llm_judging_evidence_irrelevant_produces_gap():
    llm = FakeLLMClient(responses=[{"mappings": []}])
    req = Requirement(
        id="FR-LOAN-003",
        statement="The system shall require step-up authentication for large transactions.",
        source_stakeholder="security_officer",
    )
    ComplianceAgent(_ctx(llm)).run(req)
    assert req.compliance_mappings[0].gap is not None
