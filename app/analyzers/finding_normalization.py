import hashlib
import json
import math
from dataclasses import dataclass
from typing import Literal, Sequence

from app.analyzers.element_horizontal_overflow import (
    ElementHorizontalOverflowEvidence,
)
from app.analyzers.horizontal_overflow import HorizontalOverflowResult


RULE_ID = "horizontal_overflow"
GEOMETRY_TOLERANCE_PX = 2.0
EvidenceCorrelation = Literal[
    "direct_geometry_match", "possible_contributor", "unmatched"
]
NormalizedFindingStatus = Literal["potential_horizontal_overflow"]


@dataclass(frozen=True)
class NormalizedHorizontalOverflowFinding:
    finding_id: str
    rule_id: str
    viewport_name: str
    viewport_width: int
    tag_name: str
    selector: str
    left: float
    right: float
    width: float
    element_overflow_px: float
    document_overflow_px: int | None
    status: NormalizedFindingStatus
    evidence_correlation: EvidenceCorrelation
    explanation: str


def normalize_horizontal_overflow_findings(
    findings: Sequence[ElementHorizontalOverflowEvidence],
    *,
    viewport_name: str,
    viewport_width: int,
    document_overflow: HorizontalOverflowResult | None,
) -> list[NormalizedHorizontalOverflowFinding]:
    """Normalize raw element evidence and correlate it with page-level geometry.

    Two-pixel tolerance allows for subpixel layout rounding. Deduplication only
    removes equal-geometry findings whose selectors are identical or express an
    ancestor/descendant selector path. Distinct overlapping elements remain.
    """
    if not viewport_name:
        raise ValueError("viewport_name must not be empty.")
    if isinstance(viewport_width, bool) or not isinstance(viewport_width, int):
        raise TypeError("viewport_width must be an integer.")
    if viewport_width <= 0:
        raise ValueError("viewport_width must be greater than zero.")

    unique_findings = _deduplicate_equivalent_findings(findings)
    normalized = []
    for finding in unique_findings:
        if finding.viewport_width != viewport_width:
            raise ValueError("Element finding viewport width does not match context.")
        finding_id = _finding_id(finding, viewport_name, viewport_width)
        document_overflow_px = (
            document_overflow.overflow_px if document_overflow is not None else None
        )
        correlation, explanation = _correlate(
            finding, viewport_width, document_overflow
        )
        normalized.append(
            NormalizedHorizontalOverflowFinding(
                finding_id=finding_id,
                rule_id=RULE_ID,
                viewport_name=viewport_name,
                viewport_width=viewport_width,
                tag_name=finding.tag_name,
                selector=finding.selector,
                left=finding.left,
                right=finding.right,
                width=finding.width,
                element_overflow_px=finding.overflow_px,
                document_overflow_px=document_overflow_px,
                status="potential_horizontal_overflow",
                evidence_correlation=correlation,
                explanation=explanation,
            )
        )
    return normalized


def _finding_id(
    finding: ElementHorizontalOverflowEvidence,
    viewport_name: str,
    viewport_width: int,
) -> str:
    identity = {
        "rule_id": RULE_ID,
        "selector": finding.selector,
        "viewport_name": viewport_name,
        "viewport_width": viewport_width,
    }
    digest = hashlib.sha256(
        json.dumps(identity, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()[:16]
    return f"{RULE_ID}:{digest}"


def _deduplicate_equivalent_findings(
    findings: Sequence[ElementHorizontalOverflowEvidence],
) -> list[ElementHorizontalOverflowEvidence]:
    unique: list[ElementHorizontalOverflowEvidence] = []
    for finding in findings:
        duplicate = any(
            _same_measurement(finding, existing)
            and _selectors_related(finding.selector, existing.selector)
            for existing in unique
        )
        if not duplicate:
            unique.append(finding)
    return unique


def _same_measurement(
    first: ElementHorizontalOverflowEvidence,
    second: ElementHorizontalOverflowEvidence,
) -> bool:
    return (
        first.viewport_width == second.viewport_width
        and first.tag_name == second.tag_name
        and all(
            math.isclose(
                first_value,
                second_value,
                abs_tol=GEOMETRY_TOLERANCE_PX,
                rel_tol=0,
            )
            for first_value, second_value in (
                (first.left, second.left),
                (first.right, second.right),
                (first.width, second.width),
                (first.overflow_px, second.overflow_px),
            )
        )
    )


def _selectors_related(first: str, second: str) -> bool:
    if first == second:
        return True
    first_parts = first.split(" > ")
    second_parts = second.split(" > ")
    shorter, longer = sorted(
        (first_parts, second_parts), key=len
    )
    return len(shorter) < len(longer) and longer[: len(shorter)] == shorter


def _correlate(
    finding: ElementHorizontalOverflowEvidence,
    viewport_width: int,
    document_overflow: HorizontalOverflowResult | None,
) -> tuple[EvidenceCorrelation, str]:
    if document_overflow is None:
        return (
            "unmatched",
            "No reliable document-level overflow measurement is available for this viewport.",
        )

    if document_overflow.overflow_px == 0:
        return (
            "possible_contributor",
            "The element extends beyond the viewport, but document-level overflow measured zero; the discrepancy is preserved.",
        )

    expected_right = viewport_width + document_overflow.overflow_px
    if (
        math.isclose(
            finding.right,
            expected_right,
            abs_tol=GEOMETRY_TOLERANCE_PX,
            rel_tol=0,
        )
        and math.isclose(
            finding.overflow_px,
            document_overflow.overflow_px,
            abs_tol=GEOMETRY_TOLERANCE_PX,
            rel_tol=0,
        )
    ):
        return (
            "direct_geometry_match",
            "The element's right edge and measured overflow are consistent with document-level overflow within 2 px; this does not establish causation.",
        )
    return (
        "possible_contributor",
        "The element extends beyond the viewport, but its geometry does not directly match document-level overflow within 2 px.",
    )
