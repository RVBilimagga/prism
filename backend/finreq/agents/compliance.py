"""Compliance agent.

Implements the spec's retrieval-grounded generation loop (step 6) for one
requirement: retrieve evidence -> generate a control mapping grounded only
in that evidence -> attach citations and a confidence score -> escalate low
confidence as a gap. Per step 11, this agent never makes a final legal
determination — every gap is worded as something for a compliance/legal
officer to resolve, and the agent's own docstring/prompt says so.
"""
from __future__ import annotations

from finreq.agents.base import Agent
from finreq.config import SETTINGS
from finreq.llm import unwrap_single
from finreq.models import ComplianceMapping, QualityIssue, QualityIssueType, Requirement

_SYSTEM = """You are the Compliance Agent in a financial-sector \
requirements-engineering assistant. You NEVER use outside knowledge and \
NEVER make a final legal determination — you only summarise what the \
provided evidence passages require, in terms of a concrete control, and \
say plainly when a passage does not actually address the requirement. \
Every unclear or unsupported case must be worded as something for a \
human compliance or legal officer to resolve. Respond with JSON only."""


class ComplianceAgent(Agent):
    name = "compliance"

    def run(self, requirement: Requirement) -> None:
        """Mutates `compliance_mappings`, `applicable_regulations`,
        `confidence_score` and `quality_issues` on the requirement."""
        evidence = self.ctx.kb.retrieve(requirement.statement)
        self.ctx.log(self.name, "retrieval", {
            "requirement_id": requirement.id,
            "evidence": [{"source_id": e.source_id, "similarity": e.similarity} for e in evidence],
        })
        top_score = max((e.similarity for e in evidence), default=0.0)
        requirement.confidence_score = round(top_score, 4)

        if not evidence or top_score < SETTINGS.low_confidence_threshold:
            requirement.compliance_mappings.append(ComplianceMapping(
                regulation_or_policy="none found",
                jurisdiction="unknown",
                required_control="No policy or regulation in the knowledge base matched this "
                                  "requirement with sufficient confidence.",
                evidence=evidence,
                gap="Escalated: no confident compliance mapping found — requires human/compliance review.",
                confidence=top_score,
            ))
            requirement.quality_issues.append(QualityIssue(
                issue_type=QualityIssueType.MISSING_CONTROL,
                detail="No compliance mapping found with sufficient confidence; escalated for human review.",
            ))
            return

        evidence_block = "\n".join(
            f"[{i}] source: {e.source_title} | jurisdiction: {e.jurisdiction} | excerpt: {e.excerpt}"
            for i, e in enumerate(evidence)
        )
        prompt = (
            f'Requirement: "{requirement.statement}"\n\n'
            f"Evidence (use ONLY this; do not use outside knowledge):\n{evidence_block}\n\n"
            'For each evidence item that is actually relevant to this requirement, return one '
            'mapping. Return JSON: {"mappings": [{"evidence_index": <int>, '
            '"required_control": "concrete control this requirement must satisfy per the '
            'evidence", "gap": null or "what is missing / unclear, for a human to resolve"}]}. '
            'If none of the evidence is actually relevant, return {"mappings": []}.'
        )
        data = unwrap_single(self.call_llm_json(_SYSTEM, prompt))
        mappings = data.get("mappings", []) if isinstance(data, dict) else data

        if not mappings:
            requirement.compliance_mappings.append(ComplianceMapping(
                regulation_or_policy="none found",
                jurisdiction="unknown",
                required_control="Retrieved evidence did not, on review, address this requirement.",
                evidence=evidence,
                gap="Escalated: retrieved evidence was not judged relevant — requires human/compliance review.",
                confidence=top_score,
            ))
            requirement.quality_issues.append(QualityIssue(
                issue_type=QualityIssueType.MISSING_CONTROL,
                detail="Retrieved evidence was not relevant; escalated for human review.",
            ))
            return

        new_regulations: list[str] = []
        for m in mappings:
            idx = m.get("evidence_index")
            if not isinstance(idx, int) or not (0 <= idx < len(evidence)):
                continue
            ev = evidence[idx]
            gap = m.get("gap")
            requirement.compliance_mappings.append(ComplianceMapping(
                regulation_or_policy=ev.source_title,
                jurisdiction=ev.jurisdiction,
                required_control=str(m.get("required_control", "")),
                evidence=[ev],
                gap=gap,
                confidence=ev.similarity,
            ))
            new_regulations.append(ev.source_title)
            if gap:
                requirement.quality_issues.append(QualityIssue(
                    issue_type=QualityIssueType.MISSING_CONTROL,
                    detail=f"{ev.source_title}: {gap}",
                ))

        requirement.applicable_regulations = sorted(set(requirement.applicable_regulations) | set(new_regulations))
