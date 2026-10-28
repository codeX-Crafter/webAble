from dataclasses import replace
from typing import Protocol

from app.analyzers.element_horizontal_overflow import (
    ElementHorizontalOverflowEvidence,
)
from app.analyzers.element_layout_models import (
    ElementLayoutEvidence,
    LayoutHypothesis,
    LayoutMeasurement,
)


class LayoutPageEvaluator(Protocol):
    async def evaluate(self, expression: str, arg: dict) -> list[dict]:
        ...


_MAX_ANCESTORS = 5
_MAX_CHILDREN = 8
_MAX_INSPECTED_DESCENDANTS = 50
_MAX_DESCENDANT_DEPTH = 3

_COLLECT_LAYOUT_EVIDENCE = """({selectors, viewportWidth, limits}) => {
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

    const measurementFor = (element) => {
        const rect = element.getBoundingClientRect();
        const style = getComputedStyle(element);
        return {
            tagName: element.tagName.toLowerCase(),
            selector: selectorFor(element),
            left: rect.left,
            right: rect.right,
            width: rect.width,
            scrollWidth: element.scrollWidth,
            clientWidth: element.clientWidth,
            displayType: style.display,
            overflowX: style.overflowX
        };
    };

    const scrollable = (element) => {
        const style = getComputedStyle(element);
        return ["auto", "scroll", "overlay"].includes(style.overflowX) &&
            element.scrollWidth > element.clientWidth;
    };

    return selectors.map((selector) => {
        try {
            let element;
            try {
                element = document.querySelector(selector);
            } catch (_selectorError) {
                return {selector, status: "unavailable", error: "Selector is invalid."};
            }
            if (!element) {
                return {selector, status: "unavailable", error: "Element no longer exists."};
            }

            try {
                const style = getComputedStyle(element);
                const rect = element.getBoundingClientRect();
                const ancestors = [];
                const scrollableContexts = [];
                let ancestor = element.parentElement;
                while (ancestor && ancestors.length < limits.maxAncestors) {
                    ancestors.push(measurementFor(ancestor));
                    if (scrollable(ancestor)) {
                        scrollableContexts.push(selectorFor(ancestor));
                    }
                    ancestor = ancestor.parentElement;
                }

                const oversizedChildren = [];
                const initialChildren = Array.from(element.children);
                let descendantsTruncated =
                    initialChildren.length > limits.maxInspectedDescendants;
                const queue = initialChildren
                    .slice(0, limits.maxInspectedDescendants)
                    .map((child) => ({
                        element: child,
                        depth: 1
                    }));
                let inspected = 0;
                while (
                    queue.length > 0 &&
                    inspected < limits.maxInspectedDescendants &&
                    oversizedChildren.length < limits.maxChildren
                ) {
                    const item = queue.shift();
                    inspected += 1;
                    const child = item.element;
                    const childRect = child.getBoundingClientRect();
                    if (childRect.right > viewportWidth && childRect.width > 0) {
                        oversizedChildren.push(measurementFor(child));
                    }
                    if (item.depth < limits.maxDescendantDepth) {
                        const descendants = Array.from(child.children);
                        const remainingQueueCapacity =
                            limits.maxInspectedDescendants - inspected - queue.length;
                        if (descendants.length > remainingQueueCapacity) {
                            descendantsTruncated = true;
                        }
                        queue.push(
                            ...descendants
                                .slice(0, Math.max(0, remainingQueueCapacity))
                                .map((descendant) => ({
                                    element: descendant,
                                    depth: item.depth + 1
                                }))
                        );
                    }
                }

                let current = element;
                let horizontalScrollingEnabled = false;
                let scrollContextCount = 0;
                let scrollContextLimited = false;
                while (current && scrollContextCount <= limits.maxAncestors) {
                    if (scrollable(current)) horizontalScrollingEnabled = true;
                    current = current.parentElement;
                    scrollContextCount += 1;
                }
                scrollContextLimited = current !== null;

                const hypotheses = [];
                if (rect.width > viewportWidth || style.width.endsWith("px") &&
                    parseFloat(style.width) > viewportWidth) {
                    hypotheses.push({
                        label: "wide_element_or_fixed_width",
                        explanation: "The measured element width exceeds the viewport; this may contribute to horizontal overflow.",
                        supportingMeasurements: [
                            `element width ${rect.width}px`,
                            `viewport width ${viewportWidth}px`,
                            `computed width ${style.width}`
                        ]
                    });
                }
                if (oversizedChildren.length > 0) {
                    hypotheses.push({
                        label: "oversized_descendant",
                        explanation: "One or more inspected descendants extend beyond the viewport and may contribute to the element's layout overflow.",
                        supportingMeasurements: oversizedChildren.map((child) =>
                            `${child.selector} right edge ${child.right}px`
                        )
                    });
                }
                const layoutParent = ancestors.find((item) =>
                    item.displayType.includes("flex") ||
                    item.displayType.includes("grid")
                );
                if (layoutParent) {
                    hypotheses.push({
                        label: "flex_or_grid_layout_context",
                        explanation: "The element is inside a flex or grid layout; sizing constraints in that context may be relevant.",
                        supportingMeasurements: [
                            `layout parent ${layoutParent.selector}`,
                            `parent display ${layoutParent.displayType}`,
                            `element min-width ${style.minWidth}`
                        ]
                    });
                }
                if (horizontalScrollingEnabled) {
                    hypotheses.push({
                        label: "horizontal_scrolling_enabled",
                        explanation: "Horizontal scrolling is enabled on the element or an ancestor; the overflow may be intentionally scrollable.",
                        supportingMeasurements: scrollableContexts.length > 0
                            ? scrollableContexts
                            : [`element overflow-x ${style.overflowX}`]
                    });
                }

                return {
                    selector,
                    status: "available",
                    scrollWidth: element.scrollWidth,
                    clientWidth: element.clientWidth,
                    left: rect.left,
                    right: rect.right,
                    width: rect.width,
                    computedWidth: style.width,
                    minWidth: style.minWidth,
                    maxWidth: style.maxWidth,
                    position: style.position,
                    overflowX: style.overflowX,
                    displayType: style.display,
                    ancestors,
                    oversizedChildren,
                    horizontalScrollingEnabled,
                    scrollableContextSelectors: scrollableContexts,
                    hypotheses,
                    collectionLimited:
                        ancestor !== null ||
                        descendantsTruncated ||
                        queue.length > 0 ||
                        scrollContextLimited
                };
            } catch (_measurementError) {
                return {
                    selector,
                    status: "unavailable",
                    error: "Computed layout evidence could not be collected."
                };
            }
        } catch (_elementError) {
            return {selector, status: "unavailable", error: "Element inspection failed."};
        }
    });
}"""


async def enrich_element_layout_evidence(
    page: LayoutPageEvaluator,
    findings: list[ElementHorizontalOverflowEvidence],
    viewport_width: int,
) -> list[ElementHorizontalOverflowEvidence]:
    """Attach bounded layout measurements without changing raw overflow evidence."""
    if not findings:
        return []

    selectors = list(dict.fromkeys(finding.selector for finding in findings))
    try:
        results = await page.evaluate(
            _COLLECT_LAYOUT_EVIDENCE,
            {
                "selectors": selectors,
                "viewportWidth": viewport_width,
                "limits": {
                    "maxAncestors": _MAX_ANCESTORS,
                    "maxChildren": _MAX_CHILDREN,
                    "maxInspectedDescendants": _MAX_INSPECTED_DESCENDANTS,
                    "maxDescendantDepth": _MAX_DESCENDANT_DEPTH,
                },
            },
        )
    except Exception:
        unavailable = {
            selector: (None, "Layout evidence evaluation failed.")
            for selector in selectors
        }
    else:
        unavailable = {}
        for result in results:
            selector = result["selector"]
            if result.get("status") != "available":
                unavailable[selector] = (
                    None,
                    result.get("error", "Layout evidence is unavailable."),
                )
            else:
                try:
                    unavailable[selector] = (
                        _layout_evidence(result),
                        None,
                    )
                except (KeyError, TypeError, ValueError):
                    unavailable[selector] = (
                        None,
                        "Layout evidence could not be interpreted.",
                    )

    enriched = []
    for finding in findings:
        evidence, detail = unavailable.get(
            finding.selector, (None, "Layout evidence was not returned.")
        )
        enriched.append(
            replace(
                finding,
                layout_evidence=evidence,
                layout_diagnosis_status="available" if evidence else "unavailable",
                layout_diagnosis_details=[detail] if detail else [],
            )
        )
    return enriched


def _layout_evidence(result: dict) -> ElementLayoutEvidence:
    return ElementLayoutEvidence(
        scroll_width=result["scrollWidth"],
        client_width=result["clientWidth"],
        left=result["left"],
        right=result["right"],
        width=result["width"],
        computed_width=result["computedWidth"],
        min_width=result["minWidth"],
        max_width=result["maxWidth"],
        position=result["position"],
        overflow_x=result["overflowX"],
        display_type=result["displayType"],
        ancestors=[_layout_measurement(item) for item in result["ancestors"]],
        oversized_children=[
            _layout_measurement(item) for item in result["oversizedChildren"]
        ],
        horizontal_scrolling_enabled=result["horizontalScrollingEnabled"],
        scrollable_context_selectors=result["scrollableContextSelectors"],
        hypotheses=[
            LayoutHypothesis(
                label=item["label"],
                explanation=item["explanation"],
                supporting_measurements=item["supportingMeasurements"],
            )
            for item in result["hypotheses"]
        ],
        collection_limited=result["collectionLimited"],
    )


def _layout_measurement(result: dict) -> LayoutMeasurement:
    return LayoutMeasurement(
        tag_name=result["tagName"],
        selector=result["selector"],
        left=result["left"],
        right=result["right"],
        width=result["width"],
        scroll_width=result["scrollWidth"],
        client_width=result["clientWidth"],
        display_type=result["displayType"],
        overflow_x=result["overflowX"],
    )
