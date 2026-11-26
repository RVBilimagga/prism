"""Security and privacy agent.

Rule-based, deliberately: it flags security/privacy-sensitive requirements
by keyword even when the classification agent missed them, and — acting as
a second, independent check on top of the compliance agent — flags any
security/privacy-sensitive requirement that ended up with no supporting
compliance control at all (a defense-in-depth review, not a duplicate of
compliance mapping: it catches the case where retrieval found *nothing*
relevant, which compliance.py already turns into a gap, and also the case
where compliance found something for a *different* aspect of the
requirement but never actually covered the security-sensitive part).
"""
from __future__ import annotations

from finreq.agents.base import Agent
from finreq.models import QualityIssue, QualityIssueType, Requirement, RequirementCategory

_SECURITY_KEYWORDS = [
    "authentic", "encrypt", "password", "access control", "role-based",
    "mfa", "multi-factor", "step-up", "session", "token", "firewall",
    "vulnerab", "penetration", "intrusion", "audit log",
]
_PRIVACY_KEYWORDS = [
    "personal data", "pii", "consent", "data retention", "anonymiz",
    "mask", "erasure", "right to be forgotten", "sensitive data",
]


class SecurityPrivacyAgent(Agent):
    name = "security_privacy"

    def run(self, requirement: Requirement) -> None:
        """Mutates `categories` and `quality_issues` on the requirement."""
        lower = requirement.statement.lower()
        is_security = any(k in lower for k in _SECURITY_KEYWORDS)
        is_privacy = any(k in lower for k in _PRIVACY_KEYWORDS)

        if is_security and RequirementCategory.SECURITY not in requirement.categories:
            requirement.categories.append(RequirementCategory.SECURITY)
        if is_privacy and RequirementCategory.PRIVACY not in requirement.categories:
            requirement.categories.append(RequirementCategory.PRIVACY)

        if is_security or is_privacy:
            has_supporting_control = any(
                m.required_control and not m.gap for m in requirement.compliance_mappings
            )
            if not has_supporting_control:
                requirement.quality_issues.append(QualityIssue(
                    issue_type=QualityIssueType.MISSING_CONTROL,
                    detail="Requirement touches a security- or privacy-sensitive action but has no "
                           "supporting compliance control on record; a security or compliance "
                           "officer should review before approval.",
                ))

    def review_all(self, requirements: list[Requirement]) -> None:
        for req in requirements:
            self.run(req)
