from dataclasses import dataclass, field
from typing import Literal


ElementLayoutStatus = Literal["available", "unavailable"]


@dataclass(frozen=True)
class LayoutMeasurement:
    tag_name: str
    selector: str
    left: float
    right: float
    width: float
    scroll_width: int
    client_width: int
    display_type: str
    overflow_x: str


@dataclass(frozen=True)
class LayoutHypothesis:
    label: str
    explanation: str
    supporting_measurements: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class ElementLayoutEvidence:
    scroll_width: int
    client_width: int
    left: float
    right: float
    width: float
    computed_width: str
    min_width: str
    max_width: str
    position: str
    overflow_x: str
    display_type: str
    ancestors: list[LayoutMeasurement]
    oversized_children: list[LayoutMeasurement]
    horizontal_scrolling_enabled: bool
    scrollable_context_selectors: list[str]
    hypotheses: list[LayoutHypothesis]
    collection_limited: bool
