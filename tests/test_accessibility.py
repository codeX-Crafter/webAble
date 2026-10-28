import asyncio
import re
from pathlib import Path

from app.analyzers.accessibility import (
    AXE_CORE_SCRIPT,
    scan_accessibility,
)


class FailingAccessibilityPage:
    async def add_script_tag(self, *, content):
        raise RuntimeError("script injection failed")

    async def evaluate(self, _expression, _argument):
        raise AssertionError("evaluate must not run after script injection fails")


class TimingOutAccessibilityPage:
    async def add_script_tag(self, *, content):
        assert content

    async def evaluate(self, _expression, _argument):
        await asyncio.sleep(0.1)
        return {}


def test_missing_axe_bundle_is_explicitly_unavailable(tmp_path):
    result = asyncio.run(
        scan_accessibility(
            FailingAccessibilityPage(),
            script_path=tmp_path / "missing-axe.min.js",
        )
    )

    assert result.status == "unavailable"
    assert result.violations == []
    assert result.incomplete == []
    assert result.passes == []
    assert result.inapplicable == []
    assert "npm ci" in result.details[0]


def test_axe_execution_error_is_not_an_empty_success():
    result = asyncio.run(
        scan_accessibility(
            FailingAccessibilityPage(),
            script_path=AXE_CORE_SCRIPT,
        )
    )

    assert result.status == "unavailable"
    assert result.violations == []
    assert "RuntimeError" in result.details[0]


def test_axe_timeout_is_unavailable_not_an_empty_success():
    result = asyncio.run(
        scan_accessibility(
            TimingOutAccessibilityPage(),
            timeout_seconds=0.01,
        )
    )

    assert result.status == "unavailable"
    assert "time limit" in result.details[0]
    assert result.violations == []


def test_coverage_matrix_includes_every_wcag_22_a_and_aa_criterion():
    matrix_path = Path(__file__).parent.parent / "docs" / "accessibility-coverage-v1.md"
    text = matrix_path.read_text(encoding="utf-8")
    criterion_ids = re.findall(r"^\| (\d\.\d\.\d+) \|", text, re.MULTILINE)
    expected_ids = {
        "1.1.1",
        "1.2.1", "1.2.2", "1.2.3", "1.2.4", "1.2.5",
        "1.3.1", "1.3.2", "1.3.3", "1.3.4", "1.3.5",
        "1.4.1", "1.4.2", "1.4.3", "1.4.4", "1.4.5",
        "1.4.10", "1.4.11", "1.4.12", "1.4.13",
        "2.1.1", "2.1.2", "2.1.4",
        "2.2.1", "2.2.2", "2.3.1",
        "2.4.1", "2.4.2", "2.4.3", "2.4.4", "2.4.5",
        "2.4.6", "2.4.7", "2.4.11",
        "2.5.1", "2.5.2", "2.5.3", "2.5.4", "2.5.7", "2.5.8",
        "3.1.1", "3.1.2",
        "3.2.1", "3.2.2", "3.2.3", "3.2.4", "3.2.6",
        "3.3.1", "3.3.2", "3.3.3", "3.3.4", "3.3.7", "3.3.8",
        "4.1.2", "4.1.3",
    }

    assert len(criterion_ids) == 55
    assert len(criterion_ids) == len(set(criterion_ids))
    assert set(criterion_ids) == expected_ids

    supported = {
        "1.1.1", "1.2.2", "1.3.1", "1.3.5",
        "1.4.1", "1.4.2", "1.4.3", "1.4.4", "1.4.12",
        "2.1.1", "2.2.1", "2.2.2", "2.4.1", "2.4.2", "2.4.4",
        "2.5.3", "3.1.1", "3.1.2", "3.3.2", "4.1.2",
    }
    for line in text.splitlines():
        match = re.match(r"^\| (\d\.\d\.\d+) \|", line)
        if not match:
            continue
        criterion = match.group(1)
        assert (
            f"Yes: `wcag{criterion.replace('.', '')}`" in line
        ) == (criterion in supported)
