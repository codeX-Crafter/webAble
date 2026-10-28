from dataclasses import dataclass
from typing import Literal, Sequence

from app.analyzers.audit_aggregation import (
    AuditFindingAggregation,
    AuditFindingGroup,
    EvidencePriority,
)
from app.capture.responsive import ViewportCaptureResult


SummaryStatus = Literal["available", "partial", "unavailable"]

_PRIORITY_ORDER: dict[EvidencePriority, int] = {
    "direct_geometry_match": 0,
    "possible_contributor": 1,
    "unmatched": 2,
}


@dataclass(frozen=True)
class ViewportMeasurement:
    name: str
    width: int
    overflow_px: int


@dataclass(frozen=True)
class DocumentOverflowSummary:
    status: SummaryStatus
    detected: bool | None
    affected_viewports: list[str]
    measurements: list[ViewportMeasurement]


@dataclass(frozen=True)
class IssueViewport:
    name: str
    width: int


@dataclass(frozen=True)
class IssueMeasurement:
    finding_id: str
    viewport_name: str
    viewport_width: int
    element_overflow_px: float
    document_overflow_px: int | None
    evidence_correlation: str


@dataclass(frozen=True)
class AuditSummaryIssue:
    group_id: str
    rule_id: str
    selector: str
    priority: EvidencePriority
    title: str
    affected_viewports: list[IssueViewport]
    measurements: list[IssueMeasurement]
    explanation: str


@dataclass(frozen=True)
class AuditSummary:
    status: SummaryStatus
    horizontal_overflow_detected: bool | None
    affected_viewports: list[str]
    document_level_overflow: DocumentOverflowSummary
    issues: list[AuditSummaryIssue]
    limitations: list[str]


def build_audit_summary(
    audit_findings: AuditFindingAggregation,
    viewport_results: Sequence[ViewportCaptureResult],
) -> AuditSummary:
    """Summarize document overflow and normalized element evidence separately."""
    measurements: list[ViewportMeasurement] = []
    available_document_measurements = 0
    incomplete_document_measurements = False
    affected_viewports: list[str] = []
    limitations: list[str] = []

    for result in viewport_results:
        page_overflow = result.horizontal_overflow
        if page_overflow is None:
            incomplete_document_measurements = True
            continue
        available_document_measurements += 1
        measurements.append(
            ViewportMeasurement(
                name=result.name,
                width=result.viewport.width,
                overflow_px=page_overflow.overflow_px,
            )
        )
        if page_overflow.potential_horizontal_overflow:
            affected_viewports.append(result.name)

    if available_document_measurements == 0:
        document_status: SummaryStatus = "unavailable"
        document_detected: bool | None = None
    elif incomplete_document_measurements:
        document_status = "partial"
        document_detected = True if affected_viewports else None
    else:
        document_status = "available"
        document_detected = bool(affected_viewports)

    issues = [
        _summarize_group(group)
        for group in sorted(
            audit_findings.findings,
            key=lambda group: (
                _PRIORITY_ORDER[group.priority],
                group.rule_id,
                group.selector,
                group.group_id,
            ),
        )
    ]

    for result in viewport_results:
        if result.capture_outcome not in {"completed"}:
            limitations.append(
                f"{result.name} ({result.viewport.width}px) capture: {result.capture_outcome}."
            )
        if result.overflow_analysis_status not in {"available"}:
            limitations.append(
                f"{result.name} ({result.viewport.width}px) document-level overflow analysis: {result.overflow_analysis_status}."
            )
        if result.element_overflow_diagnosis.status != "available":
            limitations.append(
                f"{result.name} ({result.viewport.width}px) element diagnosis: {result.element_overflow_diagnosis.status}."
            )
        if result.finding_normalization.status != "available":
            limitations.append(
                f"{result.name} ({result.viewport.width}px) finding normalization: {result.finding_normalization.status}."
            )
    if audit_findings.status != "available":
        limitations.append(f"Audit finding aggregation: {audit_findings.status}.")
    limitations.extend(audit_findings.details)

    if (
        document_status == "available"
        and audit_findings.status == "available"
        and not limitations
    ):
        summary_status: SummaryStatus = "available"
    elif document_status == "unavailable" and not issues:
        summary_status = "unavailable"
    else:
        summary_status = "partial"

    return AuditSummary(
        status=summary_status,
        horizontal_overflow_detected=document_detected,
        affected_viewports=affected_viewports,
        document_level_overflow=DocumentOverflowSummary(
            status=document_status,
            detected=document_detected,
            affected_viewports=affected_viewports,
            measurements=measurements,
        ),
        issues=issues,
        limitations=list(dict.fromkeys(limitations)),
    )


def _summarize_group(group: AuditFindingGroup) -> AuditSummaryIssue:
    findings = sorted(
        group.findings,
        key=lambda finding: (
            -finding.viewport_width,
            finding.viewport_name,
            finding.finding_id,
        ),
    )
    viewports: list[IssueViewport] = []
    seen_viewports: set[tuple[str, int]] = set()
    for finding in findings:
        key = (finding.viewport_name, finding.viewport_width)
        if key not in seen_viewports:
            seen_viewports.add(key)
            viewports.append(
                IssueViewport(name=finding.viewport_name, width=finding.viewport_width)
            )

    explanations = {
        "direct_geometry_match": (
            "Element geometry is consistent with document-level overflow in at least one listed viewport; this does not prove that the element caused the overflow."
        ),
        "possible_contributor": (
            "The listed element measurements are possible overflow contributors, but geometry does not establish that they caused document-level overflow."
        ),
        "unmatched": (
            "Element candidates were measured, but reliable document-level evidence was unavailable for comparison."
        ),
    }
    return AuditSummaryIssue(
        group_id=group.group_id,
        rule_id=group.rule_id,
        selector=group.selector,
        priority=group.priority,
        title=f"Potential horizontal overflow: {group.selector}",
        affected_viewports=viewports,
        measurements=[
            IssueMeasurement(
                finding_id=finding.finding_id,
                viewport_name=finding.viewport_name,
                viewport_width=finding.viewport_width,
                element_overflow_px=finding.element_overflow_px,
                document_overflow_px=finding.document_overflow_px,
                evidence_correlation=finding.evidence_correlation,
            )
            for finding in findings
        ],
        explanation=explanations[group.priority],
    )
