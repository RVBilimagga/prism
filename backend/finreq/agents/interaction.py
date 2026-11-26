"""Stakeholder interaction agent.

Conducts an adaptive interview rather than a fixed questionnaire: given the
stakeholder's (already masked) input so far, it decides which of the spec's
standard topic areas are under-covered or vague and proposes targeted
follow-up questions. The orchestrator surfaces these to the human in the
loop (CLI); their answers are appended to the transcript and the
pipeline re-runs extraction, so the "interview" happens across pipeline
runs rather than inside a single LLM call.
"""
from __future__ import annotations

from pydantic import BaseModel, Field

from finreq.agents.base import Agent
from finreq.llm import unwrap_single

TOPIC_AREAS = [
    "business objectives",
    "users and roles",
    "existing workflow",
    "inputs, outputs and business rules",
    "exceptional conditions",
    "data collection and retention",
    "authentication and authorisation",
    "financial transaction limits",
    "audit and reporting requirements",
    "performance and availability",
    "integration with existing systems",
    "regulatory and security constraints",
    "expected project schedule and budget",
]

_SYSTEM = """You are the Stakeholder Interaction Agent in a financial-sector \
requirements-engineering assistant. You never invent facts about the \
stakeholder's business; you only identify which of the given topic areas \
are missing, vague, or inconsistent in the transcript, and propose a short, \
concrete follow-up question for each. Respond with JSON only."""


class ClarificationQuestion(BaseModel):
    topic: str
    question: str
    reason: str


class InteractionResult(BaseModel):
    covered_topics: list[str] = Field(default_factory=list)
    questions: list[ClarificationQuestion] = Field(default_factory=list)


class StakeholderInteractionAgent(Agent):
    name = "stakeholder_interaction"

    def run(self, masked_transcript: str, stakeholder_role: str) -> InteractionResult:
        prompt = (
            f"Stakeholder role: {stakeholder_role}\n\n"
            f"Transcript so far (sensitive values already masked as [LABEL_n]):\n"
            f"---\n{masked_transcript}\n---\n\n"
            f"Topic areas to consider: {', '.join(TOPIC_AREAS)}\n\n"
            "Return JSON: {\"covered_topics\": [...], \"questions\": "
            "[{\"topic\": ..., \"question\": ..., \"reason\": ...}, ...]}.\n"
            "Only include a question for a topic that is missing, vague, or "
            "internally inconsistent. Do not ask about a topic that is "
            "already answered clearly. Ask at most 5 questions."
        )
        data = unwrap_single(self.call_llm_json(_SYSTEM, prompt))
        return InteractionResult.model_validate(data)
