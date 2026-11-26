"""The coordinator/orchestrator.

There is no separate "Coordinator agent" class — this module *is* the
coordinator: it owns the shared `AgentContext`, calls every other agent in
the fixed order the spec's pipeline requires (step 4: ingest -> extract ->
classify -> quality-check -> compliance/security -> risk -> validate), and
writes every requirement, risk and audit event to storage before handing
back to whatever's asking (CLI, API, tests).

SDLC selection and generation are intentionally NOT part of this pipeline
yet — deferred per project decision until an SDLC approach is chosen; see
ARCHITECTURE.md.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Optional

from finreq.agents.base import AgentContext
from finreq.agents.classification import ClassificationAgent
from finreq.agents.compliance import ComplianceAgent
from finreq.agents.conflict import ConflictDetectionAgent
from finreq.agents.extraction import ExtractionAgent
from finreq.agents.interaction import InteractionResult, StakeholderInteractionAgent
from finreq.agents.quality import QualityCheckAgent
from finreq.agents.risk import RiskAnalysisAgent
from finreq.agents.security import SecurityPrivacyAgent
from finreq.agents.validation import ValidationAgent
from finreq.llm import LLMClient, OllamaClient
from finreq.masking import MaskingResult, mask_text
from finreq.models import Requirement, RiskItem
from finreq.retrieval import KnowledgeBase
from finreq.storage import Store, in_memory_store

_UNMASK_FIELDS = ("statement", "source_excerpt", "business_justification")
_UNMASK_LIST_FIELDS = ("acceptance_criteria", "assumptions", "dependencies")


@dataclass
class PipelineResult:
    requirements: list[Requirement]
    risks: list[RiskItem]
    clarification: InteractionResult
    masking: MaskingResult
    events_logged: int = 0


def _unmask_requirement(req: Requirement, masking: MaskingResult) -> None:
    """Restores real values into human-facing fields after every LLM call
    is done, so masked placeholders never reach a review UI or generated
    artefact unnecessarily — while every prompt sent to the model stayed
    masked."""
    for f in _UNMASK_FIELDS:
        setattr(req, f, masking.unmask(getattr(req, f)))
    for f in _UNMASK_LIST_FIELDS:
        setattr(req, f, [masking.unmask(v) for v in getattr(req, f)])


def run_pipeline(
    raw_transcript: str,
    stakeholder_role: str,
    domain_tag: str = "LOAN",
    llm: LLMClient | None = None,
    kb: KnowledgeBase | None = None,
    store: Store | None = None,
    ask_clarifying_questions: bool = True,
    start_seq: int | None = None,
    on_stage: Optional[Callable[[str], None]] = None,
) -> PipelineResult:
    """Runs every agent in order and returns the final requirements/risks.

    `on_stage`, if given, is called with a short human-readable label
    right before each stage starts (e.g. "Extracting requirements...") —
    purely a UI hook (the server's stage progress) with no effect on the
    pipeline itself.
    """
    def _announce(label: str) -> None:
        if on_stage:
            on_stage(label)

    if not raw_transcript.strip():
        raise ValueError("The transcript is empty; there is nothing to analyse.")

    llm = llm or OllamaClient()
    kb = kb or KnowledgeBase()
    store = store or in_memory_store()
    if start_seq is None:
        # Continue numbering after anything already stored for this prefix, so a
        # re-analysis never overwrites an earlier requirement (and its approvals).
        prefix = Requirement.new_id(domain_tag, 0)[:-3]
        taken = [int(r.id[len(prefix):]) for r in store.all_requirements()
                 if r.id.startswith(prefix) and r.id[len(prefix):].isdigit()]
        start_seq = max(taken, default=0) + 1
    ctx = AgentContext(llm=llm, kb=kb, store=store, domain_tag=domain_tag)

    _announce("Masking sensitive data...")
    masking = mask_text(raw_transcript)
    ctx.log("orchestrator", "ingest", {
        "stakeholder_role": stakeholder_role,
        "masked_value_count": len(masking.mapping),
    })

    clarification = InteractionResult()
    if ask_clarifying_questions:
        _announce("Checking for missing or vague information...")
        clarification = StakeholderInteractionAgent(ctx).run(masking.masked_text, stakeholder_role)

    _announce("Extracting requirements...")
    requirements = ExtractionAgent(ctx).run(
        masking.masked_text, stakeholder_role, domain_tag, start_seq=start_seq
    )

    _announce(f"Classifying {len(requirements)} requirement(s)...")
    ClassificationAgent(ctx).classify_all(requirements)

    _announce("Running quality checks (ambiguity, completeness, testability)...")
    QualityCheckAgent(ctx).check_all(requirements)

    _announce("Checking for duplicates and conflicts...")
    ConflictDetectionAgent(ctx).run(requirements)

    _announce("Mapping requirements to policies and regulations...")
    compliance_agent = ComplianceAgent(ctx)
    for req in requirements:
        compliance_agent.run(req)

    _announce("Reviewing security and privacy coverage...")
    SecurityPrivacyAgent(ctx).review_all(requirements)

    _announce("Assessing risk...")
    risks = RiskAnalysisAgent().assess_all(requirements)

    _announce("Validating and routing for approval...")
    ValidationAgent().validate_all(requirements)

    _announce("Restoring masked values and saving...")
    for req in requirements:
        _unmask_requirement(req, masking)
        store.save_requirement(req)
    for risk in risks:
        store.save_risk(risk)

    ctx.log("orchestrator", "complete", {
        "requirement_count": len(requirements),
        "risk_count": len(risks),
    })

    return PipelineResult(
        requirements=requirements,
        risks=risks,
        clarification=clarification,
        masking=masking,
        events_logged=len(store.all_events()),
    )
