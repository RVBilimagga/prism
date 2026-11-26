"""Quality-check agent.

Deterministic, rule-based checks for ambiguity, incompleteness, missing
source, undefined terminology and infeasibility (spec step 10). Kept
rule-based rather than LLM-based on purpose: these checks need to be
explainable and reproducible, which is exactly the trait the spec's
"explainability" challenge calls for, and it keeps this agent fast and
free to run on every requirement without a model call.

Duplication and inconsistency/conflict checks are cross-requirement and
live in conflict.py instead, since they need to compare requirements
against each other rather than judge one in isolation.
"""
from __future__ import annotations

import re

from finreq.agents.base import Agent
from finreq.models import QualityIssue, QualityIssueType, Requirement

_VAGUE_TERMS = [
    "some", "several", "appropriate", "appropriately", "adequate",
    "adequately", "reasonable", "reasonably", "fast", "quickly",
    "user-friendly", "efficient", "efficiently", "sufficient",
    "sufficiently", "timely", "etc", "and so on", "as needed",
    "if necessary", "as appropriate", "in a timely manner", "robust",
    "robustly", "seamless", "seamlessly", "easy to use",
]
_MODAL_VERBS = ("shall", "must", "will", "should")
_KNOWN_ACRONYMS = {
    "KYC", "SRS", "API", "SDLC", "PII", "KPI", "SMS", "OTP", "ID", "IFSC",
    "PAN", "AES", "SLA", "UI", "UX", "SQL", "IP", "HTTP", "HTTPS", "URL",
    "JSON", "PDF", "CSV", "GDPR", "AML", "KFS",
}
_INFEASIBLE_PATTERNS = [
    r"\b100%\s*accuracy\b",
    r"\bzero\s*downtime\b",
    r"\bzero\s*errors?\b",
    r"\binstantly\b",
    r"\bwithin\s*0\s*seconds\b",
    r"\bnever\s*fail(s|ing)?\b",
    r"\balways\s*available\b",
]


class QualityCheckAgent(Agent):
    name = "quality_check"

    def run(self, requirement: Requirement) -> list[QualityIssue]:
        issues: list[QualityIssue] = []
        statement = requirement.statement or ""
        lower = statement.lower()

        matched_vague = [t for t in _VAGUE_TERMS if re.search(rf"\b{re.escape(t)}\b", lower)]
        if matched_vague:
            issues.append(QualityIssue(
                issue_type=QualityIssueType.AMBIGUITY,
                detail=f"Vague/unquantified term(s) found: {', '.join(matched_vague)}. "
                       "Replace with a measurable, testable value.",
            ))

        if not any(re.search(rf"\b{m}\b", lower) for m in _MODAL_VERBS):
            issues.append(QualityIssue(
                issue_type=QualityIssueType.AMBIGUITY,
                detail="Statement has no obligation term (shall/must/will/should); "
                       "it is unclear whether this is mandatory.",
            ))

        if not requirement.acceptance_criteria:
            issues.append(QualityIssue(
                issue_type=QualityIssueType.INCOMPLETENESS,
                detail="No acceptance criteria defined; the requirement cannot be verified as-is.",
            ))

        if not requirement.business_justification.strip():
            issues.append(QualityIssue(
                issue_type=QualityIssueType.INCOMPLETENESS,
                detail="No business justification recorded.",
            ))

        if not requirement.source_excerpt.strip():
            issues.append(QualityIssue(
                issue_type=QualityIssueType.MISSING_SOURCE,
                detail="No verbatim source excerpt links this requirement back to the stakeholder transcript.",
            ))

        for acronym in set(re.findall(r"\b[A-Z]{2,}\b", statement)):
            if acronym not in _KNOWN_ACRONYMS:
                issues.append(QualityIssue(
                    issue_type=QualityIssueType.UNDEFINED_TERMINOLOGY,
                    detail=f"Term '{acronym}' is not defined in the project glossary.",
                ))

        for pattern in _INFEASIBLE_PATTERNS:
            if re.search(pattern, lower):
                issues.append(QualityIssue(
                    issue_type=QualityIssueType.INFEASIBILITY,
                    detail=f"Statement asserts an absolute guarantee ('{pattern}') that is "
                           "typically infeasible to verify or deliver; consider a bounded target instead.",
                ))

        if not requirement.acceptance_criteria and matched_vague:
            issues.append(QualityIssue(
                issue_type=QualityIssueType.NOT_TESTABLE,
                detail="Requirement has no acceptance criteria and uses vague language; "
                       "it cannot currently be tested.",
            ))

        return issues

    def check_all(self, requirements: list[Requirement]) -> None:
        """Mutates each requirement's `quality_issues` in place."""
        for req in requirements:
            req.quality_issues = self.run(req)
