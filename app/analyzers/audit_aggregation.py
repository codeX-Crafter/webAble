import hashlib
import json
from collections import defaultdict
from dataclasses import dataclass
from typing import Literal, Sequence

from app.analyzers.finding_normalization import (
    EvidenceCorrelation,
    NormalizedHorizontalOverflowFinding,
)


EvidencePriority = Literal[
    "direct_geometry_match", "possible_contributor", "unmatched"
]
AggregationStatus = Literal["available", "partial", "unavailable"]


@dataclass(frozen=True)
class AuditFindingGroup:
    group_id: str
    rule_id: str
    selector: str
    priority: EvidencePriority
    explanation: str
    affected_viewports: list[str]
    findings: list[NormalizedHorizontalOverflowFinding]


@dataclass(frozen=True)
class AuditFindingAggregation:
    status: AggregationStatus
    findings: list[AuditFindingGroup]
    details: list[str]


_PRIORITY_ORDER: dict[EvidenceCorrelation, int] = {
    "direct_geometry_match": 0,
    "possible_contributor": 1,
    "unmatched": 2,
}


def aggregate_audit_findings(
    findings: Sequence[NormalizedHorizontalOverflowFinding],
    *,
    normalization_statuses: Sequence[str] = (),
) -> AuditFindingAggregation:
    """Group normalized findings by rule and selector across viewport captures."""
    grouped: dict[
        tuple[str, str], list[NormalizedHorizontalOverflowFinding]
    ] = defaultdict(list)
    for finding in findings:
        grouped[(finding.rule_id, finding.selector)].append(finding)

    groups = []
    for (rule_id, selector), group_findings in sorted(grouped.items()):
        priority = min(
            (finding.evidence_correlation for finding in group_findings),
            key=_PRIORITY_ORDER.__getitem__,
        )
        explanation = _priority_explanation(priority)
        viewport_order: dict[str, int] = {}
        for finding in group_findings:
            viewport_order.setdefault(finding.viewport_name, len(viewport_order))
        ordered_findings = sorted(
            group_findings,
            key=lambda finding: (
                viewport_order[finding.viewport_name],
                finding.viewport_width,
                finding.finding_id,
            ),
        )
        groups.append(
            AuditFindingGroup(
                group_id=_group_id(rule_id, selector),
                rule_id=rule_id,
                selector=selector,
                priority=priority,
                explanation=explanation,
                affected_viewports=list(
                    dict.fromkeys(
                        finding.viewport_name for finding in ordered_findings
                    )
                ),
                findings=ordered_findings,
            )
        )

    incomplete = [
        status for status in normalization_statuses if status != "available"
    ]
    if not normalization_statuses or not any(
        status == "available" for status in normalization_statuses
    ):
        status: AggregationStatus = "unavailable"
    elif incomplete:
        status = "partial"
    else:
        status = "available"

    details = (
        [
            "Some viewport findings could not be normalized; available groups contain only successfully normalized evidence."
        ]
        if status == "partial"
        else []
    )
    if status == "unavailable":
        details.append(
            "No normalized viewport findings were available for audit aggregation."
        )
    return AuditFindingAggregation(status=status, findings=groups, details=details)


def _group_id(rule_id: str, selector: str) -> str:
    identity = {"rule_id": rule_id, "selector": selector}
    digest = hashlib.sha256(
        json.dumps(identity, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()[:16]
    return f"{rule_id}:group:{digest}"


def _priority_explanation(priority: EvidencePriority) -> str:
    if priority == "direct_geometry_match":
        return (
            "At least one viewport has an element geometry that directly matches document-level overflow; this is consistency evidence, not proof of causation."
        )
    if priority == "possible_contributor":
        return (
            "The grouped elements are possible overflow contributors, but their geometry does not directly match document-level overflow."
        )
    return (
        "Document-level overflow evidence was unavailable for the grouped element findings."
    )
