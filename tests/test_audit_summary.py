from app.analyzers.audit_aggregation import aggregate_audit_findings
from app.analyzers.audit_summary import build_audit_summary
from app.analyzers.finding_normalization import (
    NormalizedHorizontalOverflowFinding,
)
from app.analyzers.horizontal_overflow import HorizontalOverflowResult
from app.capture.models import ViewportDimensions
from app.capture.responsive import (
    ElementOverflowDiagnosisResult,
    FindingNormalizationResult,
    ViewportCaptureResult,
)


def normalized(
    selector: str,
    viewport_name: str,
    viewport_width: int,
    correlation: str,
    element_overflow: float,
    document_overflow: int | None,
) -> NormalizedHorizontalOverflowFinding:
    return NormalizedHorizontalOverflowFinding(
        finding_id=f"{selector}:{viewport_name}",
        rule_id="horizontal_overflow",
        viewport_name=viewport_name,
        viewport_width=viewport_width,
        tag_name="div",
        selector=selector,
        left=0,
        right=viewport_width + element_overflow,
        width=viewport_width + element_overflow,
        element_overflow_px=element_overflow,
        document_overflow_px=document_overflow,
        status="potential_horizontal_overflow",
        evidence_correlation=correlation,
        explanation="Geometry evidence.",
    )


def viewport_result(
    name: str,
    width: int,
    *,
    document_overflow: int | None,
    normalization_status: str = "available",
    capture_outcome: str = "completed",
) -> ViewportCaptureResult:
    overflow = (
        HorizontalOverflowResult(
            scroll_width=width + document_overflow,
            visible_width=width,
            overflow_px=document_overflow,
            potential_horizontal_overflow=document_overflow > 0,
        )
        if document_overflow is not None
        else None
    )
    return ViewportCaptureResult(
        name=name,
        viewport=ViewportDimensions(width=width, height=800),
        capture_outcome=capture_outcome,
        horizontal_overflow=overflow,
        overflow_analysis_status=(
            "available" if overflow is not None else "missing_dimensions"
        ),
        screenshot_ref="screenshots/test.png",
        element_overflow_diagnosis=ElementOverflowDiagnosisResult(
            status="available"
        ),
        finding_normalization=FindingNormalizationResult(
            status=normalization_status
        ),
    )


def test_summary_sorts_issues_by_evidence_then_selector():
    findings = [
        normalized("#z-unmatched", "mobile", 390, "unmatched", 30, None),
        normalized("#b-possible", "mobile", 390, "possible_contributor", 40, 20),
        normalized("#z-direct", "tablet", 768, "direct_geometry_match", 100, 100),
        normalized("#a-direct", "mobile", 390, "direct_geometry_match", 50, 50),
    ]
    aggregation = aggregate_audit_findings(
        findings, normalization_statuses=["available"]
    )
    viewports = [
        viewport_result("desktop", 1365, document_overflow=0),
        viewport_result("tablet", 768, document_overflow=100),
        viewport_result("mobile", 390, document_overflow=50),
    ]

    summary = build_audit_summary(aggregation, viewports)

    assert [issue.selector for issue in summary.issues] == [
        "#a-direct",
        "#z-direct",
        "#b-possible",
        "#z-unmatched",
    ]
    assert [issue.priority for issue in summary.issues] == [
        "direct_geometry_match",
        "direct_geometry_match",
        "possible_contributor",
        "unmatched",
    ]


def test_summary_separates_document_measurements_from_element_candidates():
    findings = [
        normalized("#wide-table", "tablet", 768, "direct_geometry_match", 132, 132),
        normalized("#wide-table", "mobile", 390, "direct_geometry_match", 510, 510),
    ]
    aggregation = aggregate_audit_findings(
        findings, normalization_statuses=["available", "available"]
    )
    viewports = [
        viewport_result("desktop", 1365, document_overflow=0),
        viewport_result("tablet", 768, document_overflow=132),
        viewport_result("mobile", 390, document_overflow=510),
    ]

    summary = build_audit_summary(aggregation, viewports)
    issue = summary.issues[0]

    assert summary.horizontal_overflow_detected is True
    assert summary.affected_viewports == ["tablet", "mobile"]
    assert [
        (measurement.name, measurement.width, measurement.overflow_px)
        for measurement in summary.document_level_overflow.measurements
    ] == [
        ("desktop", 1365, 0),
        ("tablet", 768, 132),
        ("mobile", 390, 510),
    ]
    assert issue.title == "Potential horizontal overflow: #wide-table"
    assert [(item.name, item.width) for item in issue.affected_viewports] == [
        ("tablet", 768),
        ("mobile", 390),
    ]
    assert [item.element_overflow_px for item in issue.measurements] == [132, 510]
    assert all(
        item.evidence_correlation == "direct_geometry_match"
        for item in issue.measurements
    )
    assert "does not prove" in issue.explanation
    assert summary.status == "available"
    assert summary.limitations == []


def test_empty_findings_still_summarize_successful_no_overflow():
    aggregation = aggregate_audit_findings(
        [], normalization_statuses=["available", "available"]
    )
    summary = build_audit_summary(
        aggregation,
        [
            viewport_result("desktop", 1365, document_overflow=0),
            viewport_result("tablet", 768, document_overflow=0),
        ],
    )

    assert summary.status == "available"
    assert summary.horizontal_overflow_detected is False
    assert summary.affected_viewports == []
    assert summary.issues == []
    assert summary.limitations == []


def test_partial_failures_are_reported_as_limitations_not_issues():
    finding = normalized(
        "#wide-table", "tablet", 768, "direct_geometry_match", 132, 132
    )
    aggregation = aggregate_audit_findings(
        [finding], normalization_statuses=["available", "unavailable"]
    )
    summary = build_audit_summary(
        aggregation,
        [
            viewport_result("tablet", 768, document_overflow=132),
            viewport_result(
                "mobile",
                390,
                document_overflow=None,
                normalization_status="unavailable",
                capture_outcome="capture_failed",
            ),
        ],
    )

    assert summary.status == "partial"
    assert len(summary.issues) == 1
    assert summary.issues[0].selector == "#wide-table"
    assert summary.horizontal_overflow_detected is True
    assert any("mobile (390px) capture: capture_failed" in item for item in summary.limitations)
    assert any("finding normalization: unavailable" in item for item in summary.limitations)


def test_no_results_available_reports_summary_unavailable():
    aggregation = aggregate_audit_findings(
        [], normalization_statuses=["unavailable"]
    )
    summary = build_audit_summary(
        aggregation,
        [
            viewport_result(
                "mobile",
                390,
                document_overflow=None,
                normalization_status="unavailable",
                capture_outcome="capture_failed",
            )
        ],
    )

    assert summary.status == "unavailable"
    assert summary.horizontal_overflow_detected is None
    assert summary.document_level_overflow.status == "unavailable"
    assert summary.issues == []
    assert summary.limitations
