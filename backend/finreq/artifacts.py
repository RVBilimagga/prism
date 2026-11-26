"""Documentation agent: turns validated requirements + risks into the
artefacts the spec asks for (step 12) — SRS, user stories, traceability
matrix, compliance-control matrix, risk register, and an open-issues list.
Every artefact keeps each row linked back to its requirement ID and
original stakeholder excerpt, per the spec's traceability requirement.
"""
from __future__ import annotations

import os

import pandas as pd

from finreq.models import ApprovalStatus, Requirement, RiskItem


def _gist(statement: str) -> str:
    text = statement.strip().rstrip(".")
    for prefix in ("The system shall ", "The system will ", "The system must "):
        if text.startswith(prefix):
            return text[len(prefix):]
    return text


def requirements_dataframe(requirements: list[Requirement]) -> pd.DataFrame:
    rows = []
    for r in requirements:
        rows.append({
            "id": r.id,
            "statement": r.statement,
            "categories": "; ".join(c.value for c in r.categories),
            "priority": r.priority.value,
            "risk_level": r.risk_level.value,
            "confidence_score": r.confidence_score,
            "approval_status": r.approval_status.value,
            "source_stakeholder": r.source_stakeholder,
            "business_justification": r.business_justification,
            "acceptance_criteria": " | ".join(r.acceptance_criteria),
            "applicable_regulations": "; ".join(r.applicable_regulations),
            "dependencies": "; ".join(r.dependencies),
            "assumptions": "; ".join(r.assumptions),
            "duplicate_of": r.duplicate_of or "",
            "conflicts_with": "; ".join(r.conflicts_with),
            "open_quality_issues": len(r.quality_issues),
        })
    return pd.DataFrame(rows)


def traceability_matrix_dataframe(requirements: list[Requirement]) -> pd.DataFrame:
    rows = [{
        "requirement_id": r.id,
        "statement": r.statement,
        "source_stakeholder": r.source_stakeholder,
        "source_excerpt": r.source_excerpt,
        "applicable_regulations": "; ".join(r.applicable_regulations),
        "generated_artifacts": "SRS, user_stories, risk_register, compliance_matrix",
        "approval_status": r.approval_status.value,
    } for r in requirements]
    return pd.DataFrame(rows)


def compliance_matrix_dataframe(requirements: list[Requirement]) -> pd.DataFrame:
    rows = []
    for r in requirements:
        for m in r.compliance_mappings:
            rows.append({
                "requirement_id": r.id,
                "regulation_or_policy": m.regulation_or_policy,
                "jurisdiction": m.jurisdiction,
                "required_control": m.required_control,
                "gap": m.gap or "",
                "confidence": m.confidence,
                "evidence_sources": "; ".join(e.source_id for e in m.evidence),
            })
    return pd.DataFrame(rows)


def risk_register_dataframe(risks: list[RiskItem]) -> pd.DataFrame:
    rows = [{
        "risk_id": r.id,
        "requirement_id": r.related_requirement_id,
        "category": r.category,
        "description": r.description,
        "likelihood": r.likelihood,
        "impact": r.impact,
        "risk_level": r.risk_level.value,
        "mitigation": r.mitigation,
    } for r in risks]
    return pd.DataFrame(rows)


def render_user_stories(requirements: list[Requirement]) -> str:
    lines = ["# User Stories\n"]
    for r in requirements:
        justification = r.business_justification or "the stated business need is met"
        lines.append(f"## {r.id}")
        lines.append(f"As a **{r.source_stakeholder}**, I want \"{_gist(r.statement)}\" "
                      f"so that {justification}.\n")
        if r.acceptance_criteria:
            lines.append("**Acceptance criteria:**")
            for ac in r.acceptance_criteria:
                lines.append(f"- {ac}")
        lines.append("")
    return "\n".join(lines)


def render_assumptions_and_dependencies(requirements: list[Requirement]) -> str:
    lines = ["# Assumptions and Dependency Register\n"]
    for r in requirements:
        if not r.assumptions and not r.dependencies:
            continue
        lines.append(f"## {r.id}")
        if r.assumptions:
            lines.append("**Assumptions:**")
            lines.extend(f"- {a}" for a in r.assumptions)
        if r.dependencies:
            lines.append("**Dependencies:**")
            lines.extend(f"- {d}" for d in r.dependencies)
        lines.append("")
    return "\n".join(lines)


def render_open_issues(requirements: list[Requirement]) -> str:
    lines = ["# Open Issues List\n",
             "Requirements below need clarification, a duplicate/conflict resolution, "
             "or a compliance gap closed before they can be approved.\n"]
    for r in requirements:
        blocking = (
            r.approval_status == ApprovalStatus.NEEDS_CLARIFICATION
            or r.duplicate_of
            or r.conflicts_with
            or any(m.gap for m in r.compliance_mappings)
        )
        if not blocking:
            continue
        lines.append(f"## {r.id} — {r.approval_status.value}")
        lines.append(f"Statement: {r.statement}")
        if r.duplicate_of:
            lines.append(f"- Possible duplicate of {r.duplicate_of}")
        if r.conflicts_with:
            lines.append(f"- Conflicts with: {', '.join(r.conflicts_with)}")
        for issue in r.quality_issues:
            lines.append(f"- [{issue.issue_type.value}] {issue.detail}")
        for m in r.compliance_mappings:
            if m.gap:
                lines.append(f"- [compliance gap: {m.regulation_or_policy}] {m.gap}")
        lines.append("")
    return "\n".join(lines)


def render_srs(requirements: list[Requirement], project_name: str = "Loan Processing") -> str:
    lines = [f"# Software Requirements Specification — {project_name}\n",
             "_Generated by the FinReq prototype pipeline. Every requirement below "
             "carries its approval status; only APPROVED requirements should be "
             "treated as a baseline._\n"]

    by_category: dict[str, list[Requirement]] = {}
    for r in requirements:
        cats = [c.value for c in r.categories] or ["uncategorised"]
        for c in cats:
            by_category.setdefault(c, []).append(r)

    for category in sorted(by_category):
        lines.append(f"## {category.replace('_', ' ').title()} Requirements\n")
        for r in by_category[category]:
            lines.append(f"### {r.id} [{r.approval_status.value}]")
            lines.append(r.statement)
            lines.append(f"- Priority: {r.priority.value}")
            lines.append(f"- Risk level: {r.risk_level.value}")
            lines.append(f"- Confidence: {r.confidence_score}")
            if r.acceptance_criteria:
                lines.append("- Acceptance criteria:")
                lines.extend(f"  - {ac}" for ac in r.acceptance_criteria)
            if r.applicable_regulations:
                lines.append(f"- Applicable regulations/policies: {', '.join(r.applicable_regulations)}")
            lines.append(f"- Source: {r.source_stakeholder} — \"{r.source_excerpt}\"")
            lines.append("")
    return "\n".join(lines)


def generate_all_artifacts(requirements: list[Requirement], risks: list[RiskItem],
                            output_dir: str, project_name: str = "Loan Processing",
                            sdlc_plan: str | None = None) -> dict[str, str]:
    """Writes every artefact to `output_dir` and returns {artifact_name: path}.
    `sdlc_plan` is the markdown from `sdlc.render_plan`, written when given."""
    os.makedirs(output_dir, exist_ok=True)
    paths: dict[str, str] = {}

    def _write_csv(name: str, df: pd.DataFrame) -> None:
        path = os.path.join(output_dir, name)
        df.to_csv(path, index=False)
        paths[name] = path

    def _write_text(name: str, text: str) -> None:
        path = os.path.join(output_dir, name)
        with open(path, "w", encoding="utf-8") as f:
            f.write(text)
        paths[name] = path

    _write_csv("requirements.csv", requirements_dataframe(requirements))
    _write_csv("traceability_matrix.csv", traceability_matrix_dataframe(requirements))
    _write_csv("compliance_matrix.csv", compliance_matrix_dataframe(requirements))
    _write_csv("risk_register.csv", risk_register_dataframe(risks))
    _write_text("SRS.md", render_srs(requirements, project_name))
    _write_text("user_stories.md", render_user_stories(requirements))
    _write_text("assumptions_dependencies.md", render_assumptions_and_dependencies(requirements))
    _write_text("open_issues.md", render_open_issues(requirements))
    if sdlc_plan:
        _write_text("sdlc_plan.md", sdlc_plan)
    return paths
