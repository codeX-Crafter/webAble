import pytest

from app.analyzers.element_horizontal_overflow import (
    ElementHorizontalOverflowEvidence,
)
from app.analyzers.finding_normalization import (
    GEOMETRY_TOLERANCE_PX,
    normalize_horizontal_overflow_findings,
)
from app.analyzers.horizontal_overflow import HorizontalOverflowResult


def element(
    selector: str,
    *,
    viewport_width: int = 390,
    tag_name: str = "div",
    left: float = 0,
    right: float = 500,
    width: float = 500,
    overflow_px: float = 110,
) -> ElementHorizontalOverflowEvidence:
    return ElementHorizontalOverflowEvidence(
        tag_name=tag_name,
        selector=selector,
        left=left,
        right=right,
        width=width,
        viewport_width=viewport_width,
        overflow_px=overflow_px,
        status="potential_overflow_source",
        scrollable_context_detected=False,
        scrollable_container_selector=None,
    )


def page_overflow(overflow_px: int) -> HorizontalOverflowResult:
    return HorizontalOverflowResult(
        scroll_width=390 + overflow_px,
        visible_width=390,
        overflow_px=overflow_px,
        potential_horizontal_overflow=overflow_px > 0,
    )


def normalize(findings, *, viewport_name="mobile", width=390, doc=None):
    return normalize_horizontal_overflow_findings(
        findings,
        viewport_name=viewport_name,
        viewport_width=width,
        document_overflow=doc,
    )


def test_finding_ids_are_deterministic_for_same_context():
    raw = [element("#wide")]

    first = normalize(raw, doc=page_overflow(110))[0]
    second = normalize(raw, doc=page_overflow(110))[0]

    assert first.finding_id == second.finding_id
    assert first.finding_id.startswith("horizontal_overflow:")


def test_finding_ids_include_viewport_context():
    raw = [element("#wide")]

    mobile = normalize(raw, viewport_name="mobile", width=390)[0]
    tablet = normalize(
        [element("#wide", viewport_width=768, right=900, width=900, overflow_px=132)],
        viewport_name="tablet",
        width=768,
    )[0]

    assert mobile.selector == tablet.selector
    assert mobile.finding_id != tablet.finding_id


def test_exact_geometry_is_classified_as_direct_match():
    finding = normalize([element("#wide")], doc=page_overflow(110))[0]

    assert finding.evidence_correlation == "direct_geometry_match"
    assert finding.document_overflow_px == 110
    assert "does not establish causation" in finding.explanation
    assert finding.status == "potential_horizontal_overflow"


def test_nonmatching_element_is_a_possible_contributor():
    finding = normalize(
        [element("#wide", right=520, width=520, overflow_px=130)],
        doc=page_overflow(110),
    )[0]

    assert finding.evidence_correlation == "possible_contributor"
    assert finding.element_overflow_px == 130
    assert finding.document_overflow_px == 110


def test_geometry_within_document_tolerance_matches():
    doc = page_overflow(110)
    finding = normalize(
        [
            element(
                "#wide",
                right=390 + 110 + GEOMETRY_TOLERANCE_PX,
                width=390 + 110 + GEOMETRY_TOLERANCE_PX,
                overflow_px=110 + GEOMETRY_TOLERANCE_PX,
            )
        ],
        doc=doc,
    )[0]

    assert finding.evidence_correlation == "direct_geometry_match"


def test_missing_document_evidence_is_unmatched():
    finding = normalize([element("#wide")], doc=None)[0]

    assert finding.evidence_correlation == "unmatched"
    assert finding.document_overflow_px is None


def test_zero_document_overflow_preserves_discrepancy():
    finding = normalize([element("#wide")], doc=page_overflow(0))[0]

    assert finding.evidence_correlation == "possible_contributor"
    assert finding.document_overflow_px == 0
    assert "measured zero" in finding.explanation


def test_duplicate_nested_or_equivalent_selector_is_deduplicated():
    findings = normalize(
        [
            element("#wrapper"),
            element("#wrapper > span"),
            element("#wrapper"),
        ],
        doc=page_overflow(110),
    )

    assert len(findings) == 1
    assert findings[0].selector == "#wrapper"


def test_distinct_elements_with_identical_measurements_remain_separate():
    findings = normalize(
        [element("#first"), element("#second")],
        doc=page_overflow(110),
    )

    assert len(findings) == 2
    assert {finding.selector for finding in findings} == {"#first", "#second"}
    assert len({finding.finding_id for finding in findings}) == 2


def test_overlapping_but_unrelated_selectors_are_not_deduplicated():
    findings = normalize(
        [
            element("#first", left=0, right=510, width=510, overflow_px=120),
            element("#second", left=10, right=510, width=500, overflow_px=120),
        ],
        doc=page_overflow(120),
    )

    assert len(findings) == 2


def test_mismatched_viewport_evidence_is_rejected():
    with pytest.raises(ValueError, match="does not match"):
        normalize([element("#wide", viewport_width=768)], width=390)
