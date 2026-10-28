from app.analyzers.audit_aggregation import aggregate_audit_findings
from app.analyzers.finding_normalization import (
    NormalizedHorizontalOverflowFinding,
)


def finding(
    selector: str,
    viewport_name: str,
    viewport_width: int,
    finding_id: str,
    correlation: str = "direct_geometry_match",
) -> NormalizedHorizontalOverflowFinding:
    return NormalizedHorizontalOverflowFinding(
        finding_id=finding_id,
        rule_id="horizontal_overflow",
        viewport_name=viewport_name,
        viewport_width=viewport_width,
        tag_name="table" if selector == "#wide-table" else "nav",
        selector=selector,
        left=0,
        right=900,
        width=900,
        element_overflow_px=900 - viewport_width,
        document_overflow_px=900 - viewport_width,
        status="potential_horizontal_overflow",
        evidence_correlation=correlation,
        explanation="Measured geometry.",
    )


def test_table_is_grouped_across_tablet_and_mobile_and_mobile_nav_separate():
    aggregation = aggregate_audit_findings(
        [
            finding("#wide-table", "tablet", 768, "table-tablet"),
            finding("#wide-table", "mobile", 390, "table-mobile"),
            finding(
                "#main-navigation",
                "mobile",
                390,
                "navigation-mobile",
                "possible_contributor",
            ),
        ],
        normalization_statuses=["available", "available", "available"],
    )

    assert aggregation.status == "available"
    assert len(aggregation.findings) == 2
    table_group = next(
        group for group in aggregation.findings if group.selector == "#wide-table"
    )
    navigation_group = next(
        group
        for group in aggregation.findings
        if group.selector == "#main-navigation"
    )
    assert table_group.affected_viewports == ["tablet", "mobile"]
    assert [item.finding_id for item in table_group.findings] == [
        "table-tablet",
        "table-mobile",
    ]
    assert table_group.priority == "direct_geometry_match"
    assert len(navigation_group.findings) == 1
    assert navigation_group.affected_viewports == ["mobile"]
    assert navigation_group.priority == "possible_contributor"


def test_grouping_is_stable_and_prioritizes_direct_geometry():
    inputs = [
        finding("#wide-table", "tablet", 768, "table-tablet", "possible_contributor"),
        finding("#wide-table", "mobile", 390, "table-mobile"),
    ]

    first = aggregate_audit_findings(inputs, normalization_statuses=["available"])
    second = aggregate_audit_findings(inputs, normalization_statuses=["available"])

    assert first == second
    assert first.findings[0].group_id == second.findings[0].group_id
    assert first.findings[0].priority == "direct_geometry_match"
    assert "not proof of causation" in first.findings[0].explanation


def test_empty_findings_are_successfully_aggregated():
    result = aggregate_audit_findings(
        [], normalization_statuses=["available", "available"]
    )

    assert result.status == "available"
    assert result.findings == []
    assert result.details == []


def test_partial_normalization_keeps_available_groups():
    result = aggregate_audit_findings(
        [finding("#wide-table", "tablet", 768, "table-tablet")],
        normalization_statuses=["available", "unavailable", "not_attempted"],
    )

    assert result.status == "partial"
    assert len(result.findings) == 1
    assert result.findings[0].affected_viewports == ["tablet"]
    assert result.details


def test_all_normalization_failures_are_reported_unavailable():
    result = aggregate_audit_findings(
        [], normalization_statuses=["unavailable", "not_attempted"]
    )

    assert result.status == "unavailable"
    assert result.findings == []
    assert result.details


def test_unmatched_evidence_gets_review_priority():
    result = aggregate_audit_findings(
        [finding("#wide-table", "mobile", 390, "table-mobile", "unmatched")],
        normalization_statuses=["available"],
    )

    assert result.findings[0].priority == "unmatched"
