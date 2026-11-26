"""Conflict-detection agent.

Cross-requirement checks: near-duplicate statements and outright
contradictions (spec step 10's "duplication" and step 12's conflicting
stakeholder expectations). Uses the same TF-IDF + cosine-similarity
approach as retrieval.py, deliberately, so the whole prototype has one
similarity mechanism to reason about and test.

Contradiction is checked *before* duplication for any pair above the
near-duplicate threshold: two requirements that are identical except for a
negation or a differing numeric threshold ("within 2 seconds" vs "within 5
seconds") are highly similar by TF-IDF, but they are a conflict, not a
duplicate, and must be flagged as such rather than silently merged.
"""
from __future__ import annotations

import re

from sklearn.metrics.pairwise import cosine_similarity

from finreq.agents.base import Agent
from finreq.config import SETTINGS
from finreq.models import QualityIssue, QualityIssueType, Requirement
from finreq.retrieval import DOMAIN_STOP_WORDS, TfidfVectorizer

_NEGATIONS = (" not ", "n't ", "must not", "shall not", "should not", "may not", "cannot", "no longer")


def _looks_contradictory(a: str, b: str) -> bool:
    a_l, b_l = f" {a.lower()} ", f" {b.lower()} "
    a_neg = any(n in a_l for n in _NEGATIONS)
    b_neg = any(n in b_l for n in _NEGATIONS)
    if a_neg != b_neg:
        return True
    a_nums = set(re.findall(r"\d+(?:\.\d+)?", a))
    b_nums = set(re.findall(r"\d+(?:\.\d+)?", b))
    return bool(a_nums and b_nums and a_nums != b_nums)


class ConflictDetectionAgent(Agent):
    name = "conflict_detection"

    def run(self, requirements: list[Requirement]) -> None:
        """Mutates `duplicate_of`, `conflicts_with` and `quality_issues` on
        the requirements in place."""
        n = len(requirements)
        if n < 2:
            return

        vectorizer = TfidfVectorizer(stop_words=DOMAIN_STOP_WORDS)
        matrix = vectorizer.fit_transform([r.statement for r in requirements])
        sims = cosine_similarity(matrix)

        for i in range(n):
            for j in range(i + 1, n):
                score = float(sims[i][j])
                if score < SETTINGS.near_duplicate_similarity_threshold:
                    continue

                a, b = requirements[i], requirements[j]
                if _looks_contradictory(a.statement, b.statement):
                    a.conflicts_with.append(b.id)
                    b.conflicts_with.append(a.id)
                    a.quality_issues.append(QualityIssue(
                        issue_type=QualityIssueType.CONFLICTING_EXPECTATIONS,
                        detail=f"Conflicts with {b.id}: '{b.statement}' (similarity {score:.2f}).",
                        related_requirement_id=b.id,
                    ))
                    b.quality_issues.append(QualityIssue(
                        issue_type=QualityIssueType.CONFLICTING_EXPECTATIONS,
                        detail=f"Conflicts with {a.id}: '{a.statement}' (similarity {score:.2f}).",
                        related_requirement_id=a.id,
                    ))
                elif score >= SETTINGS.duplicate_similarity_threshold:
                    b.duplicate_of = a.id
                    b.quality_issues.append(QualityIssue(
                        issue_type=QualityIssueType.DUPLICATION,
                        detail=f"Near-identical to {a.id} (similarity {score:.2f}).",
                        related_requirement_id=a.id,
                    ))
