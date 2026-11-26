"""Human-approval gate.

Not an LLM agent. Every mandatory human-in-the-loop decision from the
spec's "Non-negotiable constraints" (requirement baselines, regulatory
interpretations, high-risk security requirements, conflicting stakeholder
decisions, changes to approved requirements) funnels through
`record_decision`, which is the only place `approval_status` changes after
`ValidationAgent` — and every call writes an `ApprovalRecord`, so the full
accept/reject/modify/regenerate history is reconstructable later.

The SDLC choice is the other mandatory gate (spec step 14): it is final
only once every role in `SDLC_APPROVER_ROLES` has signed it off.
"""
from __future__ import annotations

from finreq.models import ApprovalRecord, ApprovalStatus, Requirement
from finreq.storage import Store

SDLC_APPROVER_ROLES = ("project_manager", "architect", "security_lead", "compliance_officer")

_ACTION_TO_STATUS = {
    "accept": ApprovalStatus.APPROVED,
    "reject": ApprovalStatus.REJECTED,
    "modify": ApprovalStatus.PENDING_REVIEW,
    "regenerate": ApprovalStatus.NEEDS_REGENERATION,
}


class InvalidApprovalAction(ValueError):
    pass


def record_decision(
    store: Store,
    requirement: Requirement,
    action: str,
    actor_role: str,
    note: str = "",
) -> ApprovalRecord:
    """Apply a human decision to `requirement`, persist it, and return the
    `ApprovalRecord` written to the audit trail.

    `action` must be one of "accept", "reject", "modify", "regenerate" —
    the four actions the spec requires a human be able to take on any AI
    output.
    """
    if action not in _ACTION_TO_STATUS:
        raise InvalidApprovalAction(
            f"unknown approval action '{action}'; must be one of {sorted(_ACTION_TO_STATUS)}"
        )

    record = ApprovalRecord(
        target_type="requirement",
        target_id=requirement.id,
        action=action,
        actor_role=actor_role,
        note=note,
    )
    requirement.approval_status = _ACTION_TO_STATUS[action]

    store.save_approval(record)
    store.save_requirement(requirement)
    return record


def _sdlc_target(scope: str, model_key: str) -> str:
    return f"{scope}:{model_key}"


def record_sdlc_signoff(store: Store, model_key: str, actor_role: str, note: str = "", *, scope: str) -> ApprovalRecord:
    """One approver signs off the chosen SDLC model for one analysis.

    `scope` (the analysis id) is required: sign-offs keyed by model alone
    leaked from one analysis to the next whenever both chose the same model."""
    if actor_role not in SDLC_APPROVER_ROLES:
        raise InvalidApprovalAction(
            f"'{actor_role}' cannot sign off the SDLC choice; approvers are {', '.join(SDLC_APPROVER_ROLES)}"
        )
    record = ApprovalRecord(target_type="sdlc_recommendation", target_id=_sdlc_target(scope, model_key),
                            action="accept", actor_role=actor_role, note=note)
    store.save_approval(record)
    return record


def sdlc_signoffs(store: Store, model_key: str, *, scope: str) -> set[str]:
    """Roles that have signed off `model_key` for the analysis `scope`."""
    return {a.actor_role for a in store.approvals_for(_sdlc_target(scope, model_key))
            if a.target_type == "sdlc_recommendation"}
