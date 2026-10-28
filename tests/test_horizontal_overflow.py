import pytest

from app.analyzers.horizontal_overflow import analyze_horizontal_overflow


def test_equal_widths_have_no_potential_overflow():
    result = analyze_horizontal_overflow(scroll_width=800, visible_width=800)

    assert result.scroll_width == 800
    assert result.visible_width == 800
    assert result.overflow_px == 0
    assert result.potential_horizontal_overflow is False


def test_narrower_content_has_no_potential_overflow():
    result = analyze_horizontal_overflow(scroll_width=640, visible_width=800)

    assert result.overflow_px == 0
    assert result.potential_horizontal_overflow is False


def test_wider_content_reports_overflow_amount():
    result = analyze_horizontal_overflow(scroll_width=1024, visible_width=800)

    assert result.overflow_px == 224
    assert result.potential_horizontal_overflow is True


@pytest.mark.parametrize(
    ("scroll_width", "visible_width", "expected_overflow"),
    [
        (0, 0, 0),
        (0, 320, 0),
        (321, 320, 1),
    ],
)
def test_zero_and_boundary_widths(
    scroll_width, visible_width, expected_overflow
):
    result = analyze_horizontal_overflow(
        scroll_width=scroll_width, visible_width=visible_width
    )

    assert result.overflow_px == expected_overflow
    assert result.potential_horizontal_overflow is (expected_overflow > 0)


@pytest.mark.parametrize(
    ("scroll_width", "visible_width", "error"),
    [
        (-1, 320, ValueError),
        (320, -1, ValueError),
        (320.5, 320, TypeError),
        (320, "320", TypeError),
        (True, 320, TypeError),
    ],
)
def test_invalid_dimensions_are_rejected(scroll_width, visible_width, error):
    with pytest.raises(error):
        analyze_horizontal_overflow(scroll_width, visible_width)
