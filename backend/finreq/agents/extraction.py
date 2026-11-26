"""Requirement extraction agent.

Turns free-text stakeholder input into the standard requirement record
shape (spec section 8). Extraction only — classification into the 13
requirement categories is a separate agent (classification.py) so each
agent keeps one responsibility.
"""
from __future__ import annotations

from pydantic import BaseModel, Field

from finreq.agents.base import Agent
from finreq.models import Priority, Requirement

_SYSTEM = """You are the Requirement Extraction Agent in a financial-sector \
requirements-engineering assistant. You extract explicit, atomic \
requirements ONLY from what the stakeholder actually said — never invent \
numbers, thresholds, or rules not present in the text. Each requirement \
statement should be phrased as a single testable "The system shall ..." \
sentence. Respond with JSON only."""


class ExtractedRequirement(BaseModel):
    statement: str
    business_justification: str = ""
    priority: str = "medium"
    acceptance_criteria: list[str] = Field(default_factory=list)
    assumptions: list[str] = Field(default_factory=list)
    dependencies: list[str] = Field(default_factory=list)
    source_excerpt: str = ""


class ExtractionAgent(Agent):
    name = "requirement_extraction"

    def run(self, masked_transcript: str, stakeholder_role: str,
            domain_tag: str, start_seq: int = 1) -> list[Requirement]:
        prompt = (
            f"Stakeholder role: {stakeholder_role}\n\n"
            f"Transcript (sensitive values already masked as [LABEL_n]):\n"
            f"---\n{masked_transcript}\n---\n\n"
            "Extract every distinct requirement as a JSON array. Each item: "
            '{"statement": "The system shall ...", "business_justification": '
            '"...", "priority": "critical|high|medium|low", '
            '"acceptance_criteria": ["..."], "assumptions": ["..."], '
            '"dependencies": ["..."], "source_excerpt": "verbatim sentence(s) '
            'from the transcript this came from"}. '
            "If acceptance criteria are not stated, infer at most one obvious "
            "one from the statement itself, do not leave it empty unless "
            "truly impossible. Return only the JSON array, no other keys."
        )
        raw = self.call_llm_json(_SYSTEM, prompt)
        items = raw if isinstance(raw, list) else raw.get("requirements", [])

        requirements: list[Requirement] = []
        for i, item in enumerate(items):
            parsed = ExtractedRequirement.model_validate(item)
            try:
                priority = Priority(parsed.priority.lower())
            except ValueError:
                priority = Priority.MEDIUM
            req = Requirement(
                id=Requirement.new_id(domain_tag, start_seq + i),
                statement=parsed.statement,
                source_stakeholder=stakeholder_role,
                source_excerpt=parsed.source_excerpt,
                business_justification=parsed.business_justification,
                priority=priority,
                dependencies=parsed.dependencies,
                assumptions=parsed.assumptions,
                acceptance_criteria=parsed.acceptance_criteria,
            )
            requirements.append(req)
        return requirements
