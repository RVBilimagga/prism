from finreq.agents.security import SecurityPrivacyAgent
from finreq.models import ComplianceMapping, QualityIssueType, Requirement, RequirementCategory


def _req(statement, mappings=None):
    return Requirement(
        id="FR-LOAN-001", statement=statement, source_stakeholder="x",
        compliance_mappings=mappings or [],
    )


def test_tags_security_category_from_keyword():
    req = _req("The system shall require step-up authentication for large transfers.")
    SecurityPrivacyAgent(ctx=None).run(req)
    assert RequirementCategory.SECURITY in req.categories


def test_tags_privacy_category_from_keyword():
    req = _req("The system shall obtain consent before storing personal data.")
    SecurityPrivacyAgent(ctx=None).run(req)
    assert RequirementCategory.PRIVACY in req.categories


def test_flags_missing_control_when_no_supporting_mapping():
    req = _req("The system shall encrypt data at rest.")
    SecurityPrivacyAgent(ctx=None).run(req)
    assert any(i.issue_type == QualityIssueType.MISSING_CONTROL for i in req.quality_issues)


def test_no_flag_when_supporting_mapping_present():
    mapping = ComplianceMapping(
        regulation_or_policy="Sample Policy", jurisdiction="x",
        required_control="Encrypt data at rest using AES-256.", gap=None, confidence=0.9,
    )
    req = _req("The system shall encrypt data at rest.", mappings=[mapping])
    SecurityPrivacyAgent(ctx=None).run(req)
    assert not any(i.issue_type == QualityIssueType.MISSING_CONTROL for i in req.quality_issues)


def test_non_sensitive_requirement_untouched():
    req = _req("The system shall display the account balance on the home screen.")
    SecurityPrivacyAgent(ctx=None).run(req)
    assert req.categories == []
    assert req.quality_issues == []
