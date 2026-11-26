import pytest

from finreq.agents.approval import (
    SDLC_APPROVER_ROLES, InvalidApprovalAction, record_sdlc_signoff, sdlc_signoffs,
)
from finreq.models import ApprovalStatus, Requirement, RequirementCategory, RiskLevel
from finreq.sdlc import FACTORS, MODELS, derive_factors, rank, render_plan, workflow
from finreq.storage import in_memory_store


def _top(overrides) -> str:
    return rank(derive_factors([], overrides))[0].key


# One case per row of the spec's own condition table (problem statement step 14).
def test_stable_requirements_with_strict_verification_favour_v_model_or_waterfall():
    top = _top(dict(requirement_stability=0.9, regulatory_criticality=0.9, change_frequency=0.1,
                    continuous_delivery=0.1, formal_verification=0.9, documentation_needs=0.9,
                    stakeholder_availability=0.2, schedule_pressure=0.2, technical_uncertainty=0.2,
                    legacy_dependence=0.8, failure_consequence=0.8))
    assert top in ("v_model", "waterfall")


def test_frequently_changing_low_regulation_favours_agile():
    top = _top(dict(requirement_stability=0.2, regulatory_criticality=0.1, security_risk=0.2,
                    change_frequency=0.9, continuous_delivery=0.9, stakeholder_availability=0.9,
                    formal_verification=0.1, schedule_pressure=0.9, technical_uncertainty=0.7,
                    documentation_needs=0.1, failure_consequence=0.2, legacy_dependence=0.1))
    assert top == "agile"


def test_high_regulation_with_evolving_requirements_favours_a_hybrid():
    top = _top(dict(requirement_stability=0.3, regulatory_criticality=0.9, security_risk=0.9,
                    change_frequency=0.8, continuous_delivery=0.8, stakeholder_availability=0.7,
                    failure_consequence=0.9, complexity=0.7, legacy_dependence=0.3))
    assert top in ("agile_devsecops", "agile_v_model", "devsecops")


def test_high_technical_uncertainty_favours_spiral():
    top = _top(dict(technical_uncertainty=0.95, requirement_stability=0.2, complexity=0.9,
                    failure_consequence=0.9, continuous_delivery=0.2, schedule_pressure=0.1,
                    security_risk=0.7, regulatory_criticality=0.4, change_frequency=0.5))
    assert top == "spiral"


def test_large_project_with_new_technology_and_shifting_goals_favours_iterative():
    assert _top(dict(complexity=0.9, technical_uncertainty=0.8, change_frequency=0.8, continuous_delivery=0.3,
                     stakeholder_availability=0.3, failure_consequence=0.4, documentation_needs=0.6)) == "iterative"


def test_clear_requirements_with_early_partial_release_favours_incremental():
    assert _top(dict(requirement_stability=0.9, complexity=0.8, schedule_pressure=0.9, change_frequency=0.4,
                     continuous_delivery=0.4, technical_uncertainty=0.4, formal_verification=0.4,
                     legacy_dependence=0.4)) == "incremental"


def test_short_schedule_small_low_risk_build_with_users_on_hand_favours_rad():
    assert _top(dict(schedule_pressure=0.95, stakeholder_availability=0.9, technical_uncertainty=0.1, complexity=0.2,
                     regulatory_criticality=0.1, security_risk=0.2, failure_consequence=0.2, documentation_needs=0.1,
                     legacy_dependence=0.1, formal_verification=0.1, requirement_stability=0.7, change_frequency=0.6,
                     continuous_delivery=0.4)) == "rad"


def test_ranking_covers_every_model_sorted_with_reasons():
    ranking = rank(derive_factors([]))
    assert {s.key for s in ranking} == set(MODELS)
    assert [s.score for s in ranking] == sorted((s.score for s in ranking), reverse=True)
    biased = rank(derive_factors([], {"change_frequency": 1.0, "continuous_delivery": 1.0}))
    assert biased[0].supports  # a non-neutral profile always explains itself


def test_ranking_orders_by_unrounded_score():
    # Regression: these factors (FinReq's own profile) put Agile-DevSecOps at
    # 64.2 and Agile-V-Model at 63.7. Both round to 64; ranking used to sort
    # the rounded value and let dict order pick the winner.
    factors = derive_factors([], dict(
        requirement_stability=0.8, regulatory_criticality=1.0, security_risk=1.0, complexity=0.6,
        legacy_dependence=0.1, change_frequency=0.8, continuous_delivery=0.3, stakeholder_availability=0.9,
        formal_verification=0.6, failure_consequence=0.3, schedule_pressure=0.8, technical_uncertainty=0.8,
        documentation_needs=0.9))
    assert [s.key for s in rank(factors)[:2]] == ["agile_devsecops", "agile_v_model"]


def test_derive_factors_from_requirements():
    reqs = [
        Requirement(id="FR-1", statement="s", source_stakeholder="x",
                    categories=[RequirementCategory.REGULATORY], risk_level=RiskLevel.CRITICAL,
                    approval_status=ApprovalStatus.NEEDS_CLARIFICATION),
        Requirement(id="FR-2", statement="s", source_stakeholder="x",
                    categories=[RequirementCategory.INTEGRATION], risk_level=RiskLevel.LOW,
                    approval_status=ApprovalStatus.PENDING_REVIEW),
    ]
    f = derive_factors(reqs)
    assert f["regulatory_criticality"] == 0.5
    assert f["security_risk"] == 0.5
    assert f["requirement_stability"] == 0.5
    assert f["legacy_dependence"] == 0.5
    assert f["schedule_pressure"] == 0.5  # not derivable: stays neutral until a human sets it


def test_overrides_are_clamped_and_validated():
    assert derive_factors([], {"schedule_pressure": 7})["schedule_pressure"] == 1.0
    with pytest.raises(ValueError, match="unknown SDLC factor"):
        derive_factors([], {"budget": 0.5})
    with pytest.raises(ValueError, match="must be a number"):
        derive_factors([], {"schedule_pressure": "high"})


def test_every_workflow_ends_with_compliance_approved_deployment():
    for key in MODELS:
        phases = workflow(key)
        names = [p.name for p in phases]
        assert "Deployment" in names
        assert "Compliance approval" in phases[names.index("Deployment")].activities


def test_signoff_requires_all_four_roles_and_rejects_others():
    store = in_memory_store()
    with pytest.raises(InvalidApprovalAction):
        record_sdlc_signoff(store, "agile_v_model", "business_analyst", scope="run-1")
    for role in SDLC_APPROVER_ROLES[:-1]:
        record_sdlc_signoff(store, "agile_v_model", role, scope="run-1")
    assert sdlc_signoffs(store, "agile_v_model", scope="run-1") == set(SDLC_APPROVER_ROLES[:-1])
    assert sdlc_signoffs(store, "waterfall", scope="run-1") == set()
    # Regression: a second analysis choosing the same model starts unsigned.
    assert sdlc_signoffs(store, "agile_v_model", scope="run-2") == set()


def test_render_plan_reports_override_and_signoff_status():
    factors = derive_factors([])
    ranking = rank(factors)
    chosen = ranking[-1].key  # deliberately not the top pick
    plan = render_plan(ranking, chosen, factors, set(), SDLC_APPROVER_ROLES)
    assert f"Chosen model: {ranking[-1].name}" in plan
    assert "a reviewer chose" in plan
    assert "awaiting sign-off" in plan
    assert len([line for line in plan.splitlines() if line.startswith("| ") and "%" in line]) == len(MODELS)
    baselined = render_plan(ranking, ranking[0].key, factors, set(SDLC_APPROVER_ROLES), SDLC_APPROVER_ROLES)
    assert "Status: baselined" in baselined
    assert len(FACTORS) == 13
