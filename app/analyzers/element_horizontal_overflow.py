from __future__ import annotations

from dataclasses import dataclass
from dataclasses import field
from typing import Literal, Protocol

from app.analyzers.element_layout_models import ElementLayoutEvidence


ElementOverflowStatus = Literal["potential_overflow_source"]


@dataclass(frozen=True)
class ElementHorizontalOverflowEvidence:
    tag_name: str
    selector: str
    left: float
    right: float
    width: float
    viewport_width: int
    overflow_px: float
    status: ElementOverflowStatus
    scrollable_context_detected: bool
    scrollable_container_selector: str | None
    layout_evidence: ElementLayoutEvidence | None = None
    layout_diagnosis_status: Literal["available", "unavailable", "not_attempted"] = (
        "not_attempted"
    )
    layout_diagnosis_details: list[str] = field(default_factory=list)


class PageEvaluator(Protocol):
    async def evaluate(self, expression: str, arg: int) -> list[dict]:
        ...


_FIND_OVERFLOWING_ELEMENTS = """(viewportWidth) => {
    const selectorFor = (element) => {
        if (element.id) return `#${CSS.escape(element.id)}`;

        const path = [];
        for (let current = element; current && current.nodeType === 1;
             current = current.parentElement) {
            if (current.id) {
                path.unshift(`#${CSS.escape(current.id)}`);
                break;
            }
            const tag = current.tagName.toLowerCase();
            const siblings = current.parentElement
                ? Array.from(current.parentElement.children)
                    .filter((sibling) => sibling.tagName === current.tagName)
                : [];
            path.unshift(
                siblings.length > 1
                    ? `${tag}:nth-of-type(${siblings.indexOf(current) + 1})`
                    : tag
            );
        }
        return path.join(" > ");
    };

    const scrollableContextFor = (element) => {
        for (let current = element; current;
             current = current.parentElement) {
            const style = getComputedStyle(current);
            if (
                ["auto", "scroll", "overlay"].includes(style.overflowX) &&
                current.scrollWidth > current.clientWidth
            ) {
                return current;
            }
        }
        return null;
    };

    const candidates = Array.from(document.querySelectorAll("*"))
        .filter((element) => !["HTML", "BODY"].includes(element.tagName))
        .map((element) => {
            const style = getComputedStyle(element);
            if (
                style.display === "none" ||
                style.visibility === "hidden" ||
                style.visibility === "collapse" ||
                style.contentVisibility === "hidden" ||
                Number(style.opacity) === 0 ||
                element.getClientRects().length === 0
            ) {
                return null;
            }
            const rect = element.getBoundingClientRect();
            if (
                rect.width <= 0 ||
                rect.height <= 0 ||
                rect.right <= viewportWidth
            ) {
                return null;
            }
            return { element, rect, selector: selectorFor(element) };
        })
        .filter(Boolean);

    const candidateElements = new Set(
        candidates.map((candidate) => candidate.element)
    );
    return candidates
        .filter(({ element }) => {
            for (
                let ancestor = element.parentElement;
                ancestor;
                ancestor = ancestor.parentElement
            ) {
                if (candidateElements.has(ancestor)) return false;
            }
            return true;
        })
        .map(({ element, rect, selector }) => {
            const scrollableContext = scrollableContextFor(element);
            return {
                tagName: element.tagName.toLowerCase(),
                selector,
                left: rect.left,
                right: rect.right,
                width: rect.width,
                overflowPx: rect.right - viewportWidth,
                scrollableContextDetected: scrollableContext !== null,
                scrollableContainerSelector: scrollableContext
                    ? selectorFor(scrollableContext)
                    : null
            };
        });
}"""


async def diagnose_element_horizontal_overflow(
    page: PageEvaluator, viewport_width: int
) -> list[ElementHorizontalOverflowEvidence]:
    """Return right-edge DOM geometry candidates without attributing a defect."""
    if isinstance(viewport_width, bool) or not isinstance(viewport_width, int):
        raise TypeError("viewport_width must be an integer.")
    if viewport_width <= 0:
        raise ValueError("viewport_width must be greater than zero.")

    elements = await page.evaluate(_FIND_OVERFLOWING_ELEMENTS, viewport_width)
    return [
        ElementHorizontalOverflowEvidence(
            tag_name=element["tagName"],
            selector=element["selector"],
            left=element["left"],
            right=element["right"],
            width=element["width"],
            viewport_width=viewport_width,
            overflow_px=element["overflowPx"],
            status="potential_overflow_source",
            scrollable_context_detected=element["scrollableContextDetected"],
            scrollable_container_selector=element["scrollableContainerSelector"],
        )
        for element in elements
    ]
