"""Classification agent: multi-label categorisation of each requirement
across the 13 dimensions the spec lists (business, functional, security,
privacy, regulatory, performance, ...). One requirement may get several
categories.
"""
from __future__ import annotations

from finreq.agents.base import Agent
from finreq.llm import unwrap_single
from finreq.models import Requirement, RequirementCategory

_SYSTEM = """You are the Classification Agent in a financial-sector \
requirements-engineering assistant. You assign zero or more categories to \
a requirement from a fixed list. A requirement may belong to several \
categories at once (multi-label). Respond with JSON only."""

_CATEGORY_LIST = ", ".join(c.value for c in RequirementCategory)


class ClassificationAgent(Agent):
    name = "classification"

    def run(self, requirement: Requirement) -> list[RequirementCategory]:
        prompt = (
            f"Allowed categories: {_CATEGORY_LIST}\n\n"
            f"Requirement: \"{requirement.statement}\"\n"
            f"Justification: \"{requirement.business_justification}\"\n\n"
            'Return JSON: {"categories": ["...", ...]} using only values '
            "from the allowed list, most relevant first."
        )
        data = unwrap_single(self.call_llm_json(_SYSTEM, prompt))
        raw_categories = data.get("categories", []) if isinstance(data, dict) else data
        categories: list[RequirementCategory] = []
        for c in raw_categories:
            try:
                cat = RequirementCategory(str(c).lower().strip())
            except ValueError:
                continue
            if cat not in categories:
                categories.append(cat)
        if not categories:
            categories = [RequirementCategory.FUNCTIONAL]
        return categories

    def classify_all(self, requirements: list[Requirement]) -> None:
        """Mutates each requirement's `categories` in place."""
        for req in requirements:
            req.categories = self.run(req)
