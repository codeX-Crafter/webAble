from dataclasses import dataclass


@dataclass(frozen=True)
class HorizontalOverflowResult:
    scroll_width: int
    visible_width: int
    overflow_px: int
    potential_horizontal_overflow: bool


def analyze_horizontal_overflow(
    scroll_width: int, visible_width: int
) -> HorizontalOverflowResult:
    """Compare measured document and viewport widths without diagnosing a cause."""
    for name, value in (
        ("scroll_width", scroll_width),
        ("visible_width", visible_width),
    ):
        if isinstance(value, bool) or not isinstance(value, int):
            raise TypeError(f"{name} must be an integer.")
        if value < 0:
            raise ValueError(f"{name} must be non-negative.")

    overflow_px = max(0, scroll_width - visible_width)
    return HorizontalOverflowResult(
        scroll_width=scroll_width,
        visible_width=visible_width,
        overflow_px=overflow_px,
        potential_horizontal_overflow=overflow_px > 0,
    )
