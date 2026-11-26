import os

from finreq.artifacts import generate_all_artifacts, render_open_issues, render_user_stories
from finreq.models import (
    ApprovalStatus, ComplianceMapping, Priority, QualityIssue, QualityIssueType,
    Requirement, RequirementCategory, RiskItem, RiskLevel,
)


def _reqs():
    r1 = Requirement(
        id="FR-LOAN-001",
        statement="The system shall require step-up authentication for large transfers.",
        source_stakeholder="security_officer",
        source_excerpt="We need extra verification for big transfers.",
        business_justification="Reduce fraud.",
        priority=Priority.HIGH,
        categories=[RequirementCategory.SECURITY],
        acceptance_criteria=["Second factor required above threshold."],
        approval_status=ApprovalStatus.PENDING_REVIEW,
    )
    r2 = Requirement(
        id="FR-LOAN-002",
        statement="The system shall notify the customer by SMS after disbursement.",
        source_stakeholder="ops_manager",
        source_excerpt="Customers should get an SMS when money is out.",
        approval_status=ApprovalStatus.NEEDS_CLARIFICATION,
        quality_issues=[QualityIssue(issue_type=QualityIssueType.INCOMPLETENESS, detail="no acceptance criteria")],
    )
    return [r1, r2]


def test_render_user_stories_contains_each_requirement_and_role():
    text = render_user_stories(_reqs())
    assert "FR-LOAN-001" in text
    assert "security_officer" in text
    assert "FR-LOAN-002" in text


def test_render_open_issues_lists_only_blocking_requirements():
    text = render_open_issues(_reqs())
    assert "FR-LOAN-002" in text
    assert "FR-LOAN-001" not in text  # pending_review with no issues isn't "open"


def test_generate_all_artifacts_writes_expected_files(tmp_path):
    risks = [RiskItem(
        related_requirement_id="FR-LOAN-001", category="security",
        description="d", likelihood="high", impact="high", risk_level=RiskLevel.HIGH,
    )]
    paths = generate_all_artifacts(_reqs(), risks, str(tmp_path))
    expected = {
        "requirements.csv", "traceability_matrix.csv", "compliance_matrix.csv",
        "risk_register.csv", "SRS.md", "user_stories.md",
        "assumptions_dependencies.md", "open_issues.md",
    }
    assert set(paths) == expected
    for path in paths.values():
        assert os.path.exists(path)
        assert os.path.getsize(path) > 0


def test_compliance_matrix_has_one_row_per_mapping(tmp_path):
    reqs = _reqs()
    reqs[0].compliance_mappings = [
        ComplianceMapping(regulation_or_policy="Policy A", jurisdiction="x", required_control="c1", confidence=0.9),
        ComplianceMapping(regulation_or_policy="Policy B", jurisdiction="x", required_control="c2", confidence=0.8),
    ]
    paths = generate_all_artifacts(reqs, [], str(tmp_path))
    import pandas as pd
    df = pd.read_csv(paths["compliance_matrix.csv"])
    assert len(df) == 2
    assert set(df["requirement_id"]) == {"FR-LOAN-001"}
