"""SDLC selection engine (problem statement steps 13-15).

Deterministic multi-criteria decision analysis, no LLM call: the
recommendation has to be explainable to the four people who must sign it
off (spec step 14), so every score is a weighted sum the reader can redo
by hand from the factor table, and every "why" line names the factors
that moved the score most.

Four factors are derived from the analysed requirements (the rest of the
project profile -- schedule, team, delivery model -- isn't in a stakeholder
transcript, so a human supplies it). Output is a ranked list, never one
label, per the spec.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from finreq.models import ApprovalStatus, Requirement, RequirementCategory, RiskLevel

FACTOR_LABELS = {
    "requirement_stability": "Requirement stability",
    "regulatory_criticality": "Regulatory criticality",
    "security_risk": "Security risk",
    "complexity": "Project complexity and size",
    "legacy_dependence": "Legacy-system dependence",
    "change_frequency": "Expected frequency of change",
    "continuous_delivery": "Need for continuous delivery",
    "stakeholder_availability": "Stakeholder availability",
    "formal_verification": "Need for formal verification",
    "failure_consequence": "Consequence of failure",
    "schedule_pressure": "Budget and schedule pressure",
    "technical_uncertainty": "Technical uncertainty",
    "documentation_needs": "Testing and documentation needs",
}
FACTORS = tuple(FACTOR_LABELS)
DERIVED_FACTORS = ("requirement_stability", "regulatory_criticality", "security_risk", "legacy_dependence")

# How much each factor matters overall (1 = normal, 2 = decisive).
_WEIGHTS = dict(zip(FACTORS, (2, 2, 2, 1, 1, 2, 2, 1, 1, 2, 1, 1, 1)))

# Per model, per factor (same order as FACTORS): +1 favours a high value,
# -1 favours a low value, 0 indifferent. Checked against the spec's own
# condition table in tests/test_sdlc.py.
MODELS = {
    #                      stab reg sec cmp leg chg cd stk  fv fail sch unc doc
    "waterfall":       ("Waterfall",                (1, 1, 0, -1, 1, -1, -1, -1, 1, 0, -1, -1, 1)),
    "v_model":         ("V-Model",                  (1, 1, 1, 0, 1, -1, -1, -1, 1, 1, -1, -1, 1)),
    "spiral":          ("Spiral",                   (-1, 0, 1, 1, 0, 0, -1, 0, 0, 1, -1, 1, 0)),
    "agile":           ("Agile",                    (-1, -1, -1, 0, -1, 1, 1, 1, -1, -1, 1, 1, -1)),
    "devsecops":       ("DevSecOps",                (0, 1, 1, 0, -1, 1, 1, 0, 0, 1, 1, 0, 0)),
    "agile_v_model":   ("Agile–V-Model hybrid",     (-1, 1, 1, 1, 0, 1, 0, 1, 1, 1, 0, 0, 1)),
    "agile_devsecops": ("Agile–DevSecOps hybrid",   (-1, 1, 1, 1, -1, 1, 1, 1, 0, 1, 1, 1, 0)),
    # Standard "when to use" conditions. Iterative: a large system refined in whole-system
    # cycles while the team learns new technology and goals shift. Incremental: requirements
    # clear up front, a large system delivered in parts, early partial release. RAD: a short
    # timebox with users always on hand, low technical risk, a small modular build, light
    # documentation; unsuited to regulated, security-critical or high-consequence work.
    "iterative":       ("Iterative",                (0, 0, 0, 1, 0, 1, 0, 0, 0, 0, 0, 1, 0)),
    "incremental":     ("Incremental",              (1, 0, 0, 1, 0, 0, 0, 0, 0, 0, 1, 0, 0)),
    "rad":             ("RAD",                      (0, -1, -1, -1, -1, 1, 0, 1, -1, -1, 1, -1, -1)),
}

_REGULATED = {RequirementCategory.REGULATORY, RequirementCategory.PRIVACY, RequirementCategory.AUDIT_REPORTING}


@dataclass
class SDLCScore:
    key: str
    name: str
    score: float                   # 0-100 fit, one decimal
    supports: list[str] = field(default_factory=list)
    against: list[str] = field(default_factory=list)


def derive_factors(requirements: list[Requirement], overrides: dict | None = None) -> dict[str, float]:
    """Factor values in [0, 1]. Derived ones come from the requirements;
    everything else defaults to 0.5 (no information) until `overrides`
    (the human-supplied project profile) sets it."""
    factors = dict.fromkeys(FACTORS, 0.5)
    if requirements:
        n = len(requirements)

        def share(pred) -> float:
            return round(sum(1 for r in requirements if pred(r)) / n, 2)

        factors["regulatory_criticality"] = share(lambda r: bool(set(r.categories) & _REGULATED))
        factors["security_risk"] = share(lambda r: r.risk_level in (RiskLevel.HIGH, RiskLevel.CRITICAL))
        factors["requirement_stability"] = round(1 - share(
            lambda r: r.approval_status == ApprovalStatus.NEEDS_CLARIFICATION
            or bool(r.conflicts_with) or bool(r.duplicate_of)), 2)
        factors["legacy_dependence"] = share(lambda r: RequirementCategory.INTEGRATION in r.categories)

    for name, value in (overrides or {}).items():
        if name not in factors:
            raise ValueError(f"unknown SDLC factor '{name}'; expected one of {', '.join(FACTORS)}")
        if not isinstance(value, (int, float)) or isinstance(value, bool):
            raise ValueError(f"SDLC factor '{name}' must be a number between 0 and 1, got {value!r}")
        factors[name] = min(max(float(value), 0.0), 1.0)
    return factors


def _fit(pref: int, value: float) -> float:
    return value if pref == 1 else 1 - value if pref == -1 else 0.5


def _describe(name: str, value: float) -> str:
    level = "high" if value >= 0.67 else "low" if value <= 0.33 else "moderate"
    return f"{FACTOR_LABELS[name]} is {level} ({value:.2f})"


def rank(factors: dict[str, float]) -> list[SDLCScore]:
    total = sum(_WEIGHTS.values())
    scored = []
    for key, (name, prefs) in MODELS.items():
        fits = {f: _fit(p, factors[f]) for f, p in zip(FACTORS, prefs)}
        raw = 100 * sum(_WEIGHTS[f] * fits[f] for f in FACTORS) / total
        # Contribution relative to an indifferent (0.5) fit: what pushed this model up or down.
        pull = sorted(((_WEIGHTS[f] * (fits[f] - 0.5), f) for f in FACTORS), reverse=True)
        scored.append((raw, SDLCScore(
            key=key, name=name, score=round(raw, 1),
            supports=[_describe(f, factors[f]) for c, f in pull[:3] if c > 0],
            against=[_describe(f, factors[f]) for c, f in pull[::-1][:2] if c < 0],
        )))
    # Sort on the unrounded score: two models can round to the same percentage.
    return [s for _, s in sorted(scored, key=lambda pair: -pair[0])]


@dataclass
class Phase:
    name: str
    activities: list[str]
    roles: list[str]
    deliverables: list[str]
    exit_gate: str
    repeats: bool = False


# Financial-sector controls are written into the phases themselves (spec
# step 15's examples: threat modelling in design, static security testing in
# implementation, transaction-integrity testing in validation, compliance
# approval before deployment) rather than bolted on per model.
_PHASES = {
    "planning": Phase("Planning", ["Agree scope, budget and schedule", "Baseline the risk register"],
                      ["Project manager", "Business analyst"], ["Project plan", "Risk register"],
                      "Project manager and compliance officer sign off scope"),
    "requirements": Phase("Requirements", ["Stakeholder interviews analysed with FinReq",
                                           "Resolve clarifications and conflicts"],
                          ["Business analyst", "Product owner", "Compliance officer"],
                          ["SRS", "Traceability matrix", "Compliance-control matrix"],
                          "Requirement baseline approved by a human reviewer"),
    "design": Phase("Design", ["Architecture design", "Threat modelling"], ["Architect", "Security lead"],
                    ["Architecture document", "Threat model"], "Security lead reviews the threat model"),
    "implementation": Phase("Implementation", ["Build", "Static security testing (SAST)", "Peer review"],
                            ["Developers"], ["Code", "SAST report"], "No open high-severity SAST findings"),
    "testing": Phase("Verification", ["Unit, integration and system tests traced to design"], ["QA"],
                     ["Test reports"], "Every requirement has a passing test"),
    "validation": Phase("Validation", ["User acceptance testing", "Transaction-integrity testing"],
                        ["Business users", "QA"], ["UAT sign-off"], "Stakeholders accept the release"),
    "risk_analysis": Phase("Risk analysis", ["Prototype the riskiest component", "Evaluate and re-plan"],
                           ["Architect", "Risk manager"], ["Prototype", "Risk assessment"],
                           "Residual risk accepted before the next cycle", repeats=True),
    "sprint": Phase("Sprint", ["Backlog refinement", "Build and test the increment", "Review and retrospective"],
                    ["Product owner", "Delivery team"], ["Working increment", "Updated backlog"],
                    "Definition of done met; changed requirements re-approved", repeats=True),
    "pipeline": Phase("Secure delivery pipeline", ["Automated build and tests", "SAST and dependency scanning",
                                                   "Policy-as-code compliance checks"],
                      ["DevSecOps engineer"], ["Pipeline run evidence"], "All automated gates green", repeats=True),
    "deployment": Phase("Deployment", ["Compliance approval", "Release with rollback plan"],
                        ["Release manager", "Compliance officer"], ["Release notes", "Compliance approval record"],
                        "Compliance approval recorded before production"),
    "operations": Phase("Operations", ["Monitoring", "Audit logging", "Incident response"], ["Operations"],
                        ["Monitoring reports", "Audit logs"], "Periodic audit review"),
    "iteration": Phase("Iteration", ["Refine the design and threat model for this cycle",
                                     "Build and test the whole system version, with SAST",
                                     "Review the version with stakeholders and re-plan"],
                       ["Architect", "Developers", "QA"], ["System version", "Iteration review"],
                       "Version reviewed; changed requirements re-approved", repeats=True),
    "increment": Phase("Increment", ["Build the next increment, with SAST", "Integration and regression tests",
                                     "Release the increment to users"],
                       ["Developers", "QA"], ["Working increment", "Release notes"],
                       "Increment passes regression and security tests", repeats=True),
    "user_design": Phase("User design", ["Joint design workshops with users", "Prototype and refine"],
                         ["Business users", "Designers"], ["Approved prototype"],
                         "Users accept the prototype", repeats=True),
    "rapid_construction": Phase("Rapid construction", ["Build from reusable components",
                                                       "Static security testing (SAST)", "Integration tests"],
                                ["Developers", "QA"], ["Code", "SAST report"],
                                "No open high-severity SAST findings"),
}
_MODEL_PHASES = {
    "waterfall": ["planning", "requirements", "design", "implementation", "testing", "deployment", "operations"],
    "v_model": ["planning", "requirements", "design", "implementation", "testing", "validation", "deployment"],
    "spiral": ["planning", "risk_analysis", "design", "implementation", "validation", "deployment"],
    "agile": ["planning", "sprint", "deployment"],
    "devsecops": ["planning", "pipeline", "deployment", "operations"],
    "agile_v_model": ["requirements", "design", "sprint", "testing", "validation", "deployment"],
    "agile_devsecops": ["planning", "sprint", "pipeline", "deployment", "operations"],
    "iterative": ["planning", "requirements", "iteration", "validation", "deployment", "operations"],
    "incremental": ["planning", "requirements", "design", "increment", "deployment", "operations"],
    "rad": ["planning", "user_design", "rapid_construction", "deployment"],
}


def workflow(model_key: str) -> list[Phase]:
    return [_PHASES[p] for p in _MODEL_PHASES[model_key]]


def render_plan(ranking: list[SDLCScore], chosen_key: str, factors: dict[str, float],
                signed_by: set[str], approver_roles: tuple[str, ...]) -> str:
    """Markdown SDLC plan: ranking, decision factors, the chosen model's
    workflow, and sign-off status."""
    chosen = next(s for s in ranking if s.key == chosen_key)
    top = ranking[0]
    lines = ["# SDLC recommendation\n", "| Model | Fit |", "|---|---|"]
    lines += [f"| {s.name} | {s.score}% |" for s in ranking]
    lines.append(f"\n## Chosen model: {chosen.name}\n")
    if chosen.key != top.key:
        lines.append(f"Recommended model was {top.name} ({top.score}%); a reviewer chose {chosen.name} instead.\n")
    lines += [f"- In favour: {s}" for s in chosen.supports] + [f"- Against: {s}" for s in chosen.against]
    lines += ["\n## Decision factors\n", "| Factor | Value | Source |", "|---|---|---|"]
    lines += [f"| {FACTOR_LABELS[f]} | {factors[f]:.2f} | "
              f"{'derived from requirements' if f in DERIVED_FACTORS else 'project profile'} |" for f in FACTORS]
    lines.append("\n## Workflow\n")
    for i, phase in enumerate(workflow(chosen_key), 1):
        lines.append(f"### {i}. {phase.name}{' (repeats each iteration)' if phase.repeats else ''}\n")
        lines.append(f"- Activities: {'; '.join(phase.activities)}")
        lines.append(f"- Roles: {', '.join(phase.roles)}")
        lines.append(f"- Deliverables: {', '.join(phase.deliverables)}")
        lines.append(f"- Exit gate: {phase.exit_gate}\n")
    lines.append("## Sign-off\n")
    lines += [f"- {role.replace('_', ' ').capitalize()}: {'signed' if role in signed_by else 'pending'}"
              for role in approver_roles]
    status = "baselined" if set(approver_roles) <= signed_by else "awaiting sign-off"
    lines.append(f"\nStatus: {status}.")
    return "\n".join(lines) + "\n"
