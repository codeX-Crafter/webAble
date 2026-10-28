import asyncio

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
