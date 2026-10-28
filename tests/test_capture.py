import asyncio
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
from playwright.async_api import async_playwright

from app.analyzers.element_horizontal_overflow import (
    diagnose_element_horizontal_overflow,
)
from app.analyzers.element_layout_evidence import enrich_element_layout_evidence
from app.capture.runner import BrowserCapture
from app.capture.responsive import capture_responsive_viewports
from app.capture.storage import LocalScreenshotStorage
from app.capture.url_safety import PublicURLSafetyValidator, UnsafeURL, sanitize_url


FIXTURES = Path(__file__).parent / "fixtures"


class FixtureHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        path = urlparse(self.path).path
        if path == "/missing.png":
            self.send_error(404)
            return
        if path == "/valid.svg":
            body = b'<svg xmlns="http://www.w3.org/2000/svg" width="12" height="12"></svg>'
            self.send_response(200)
            self.send_header("Content-Type", "image/svg+xml")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return
        if path == "/timeout":
            self.send_response(200)
            self.send_header("Content-Type", "text/html")
            self.end_headers()
            self.wfile.write(b"<html><head><title>Slow</title>")
            self.wfile.flush()
            threading.Event().wait(1)
            return

        fixture = {
            "/normal": "normal.html",
            "/overflow": "overflow.html",
            "/responsive-overflow": "responsive_overflow.html",
            "/layout-fixed-width": "layout_fixed_width.html",
            "/layout-oversized-descendant": "layout_oversized_descendant.html",
            "/layout-flex-grid": "layout_flex_grid.html",
            "/layout-horizontal-scroll": "layout_horizontal_scroll.html",
            "/delayed": "delayed.html",
            "/failed-resource": "failed_resource.html",
            "/javascript-error": "javascript_error.html",
            "/blocked-resource": "blocked_resource.html",
            "/functional-ux": "functional_ux.html",
            "/accessibility": "accessibility.html",
        }.get(path, "normal.html")
        body = (FIXTURES / fixture).read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_HEAD(self):
        path = urlparse(self.path).path
        if path == "/redirect-to-ok":
            self.send_response(302)
            self.send_header("Location", "/normal")
            self.end_headers()
            return
        if path == "/redirect-to-private":
            self.send_response(302)
            self.send_header("Location", "http://private.invalid/private-link")
            self.end_headers()
            return
        if path == "/broken-link":
            self.send_error(404)
            return
        if path == "/slow-link":
            threading.Event().wait(2)
        if path == "/missing.png":
            self.send_error(404)
            return
        if path == "/valid.svg":
            self.send_response(200)
            self.send_header("Content-Type", "image/svg+xml")
            self.end_headers()
            return
        if path == "/private-link":
            self.send_response(200)
            self.end_headers()
            return
        if path == "/normal":
            self.send_response(200)
            self.end_headers()
            return
        self.send_error(404)

    def log_message(self, format, *args):
        pass


class LocalhostValidator:
    async def validate(self, url: str) -> str:
        return url


class BlocksTestExternalHost(LocalhostValidator):
    async def validate(self, url: str) -> str:
        if urlparse(url).hostname == "private.invalid":
            raise UnsafeURL("The URL resolves to a prohibited network destination.")
        return url


@pytest.fixture(scope="module")
def fixture_server():
    server = ThreadingHTTPServer(("127.0.0.1", 0), FixtureHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    yield f"http://127.0.0.1:{server.server_port}"
    server.shutdown()
    thread.join()
    server.server_close()


@pytest.fixture
def capture(tmp_path):
    return BrowserCapture(
        storage=LocalScreenshotStorage(tmp_path),
        url_validator=LocalhostValidator(),
        navigation_timeout_ms=300,
        settling_period_ms=50,
    )


def test_normal_fixture_collects_metadata_and_screenshot(fixture_server, capture):
    evidence = asyncio.run(
        capture.capture(f"{fixture_server}/normal?token=private#section", 800, 600)
    )
    assert evidence.outcome == "completed"
    assert evidence.page_title == "Normal fixture"
    assert evidence.requested_url.endswith("?token=%5Bredacted%5D")
    assert evidence.final_url.endswith("?token=%5Bredacted%5D")
    assert evidence.viewport.width == 800
    assert evidence.document.visible_width == 800
    assert evidence.screenshot_ref is not None
    assert (capture._storage._directory.parent / evidence.screenshot_ref).is_file()


def test_capture_endpoint_returns_200_for_local_fixture(
    fixture_server, tmp_path, monkeypatch
):
    import app.main as main

    monkeypatch.setattr(
        main,
        "capture_service",
        BrowserCapture(
            storage=LocalScreenshotStorage(tmp_path),
            url_validator=LocalhostValidator(),
            navigation_timeout_ms=1_000,
            settling_period_ms=50,
        ),
    )
    monkeypatch.setattr(main, "url_validator", LocalhostValidator())
    with TestClient(main.app) as client:
        response = client.post(
            "/captures",
            json={"url": f"{fixture_server}/responsive-overflow"},
        )
    assert response.status_code == 200
    viewports = response.json()["viewports"]
    assert [item["name"] for item in viewports] == ["desktop", "tablet", "mobile"]
    assert [item["viewport"] for item in viewports] == [
        {"width": 1365, "height": 768},
        {"width": 768, "height": 1024},
        {"width": 390, "height": 844},
    ]
    assert all(item["capture_outcome"] == "completed" for item in viewports)
    assert all(item["screenshot_ref"] for item in viewports)
    assert all("horizontal_overflow" in item for item in viewports)
    assert all("overflow_analysis_status" in item for item in viewports)
    assert all("element_overflow_diagnosis" in item for item in viewports)
    assert all("functional_ux_audit" in item for item in viewports)
    assert all(item["functional_ux_audit"]["status"] == "available" for item in viewports)
    assert all("accessibility_scan" in item for item in viewports)
    assert all(item["accessibility_scan"]["status"] == "available" for item in viewports)
    assert all(item["accessibility_scan"]["axe_version"] == "4.14.0" for item in viewports)
    assert all("finding_normalization" in item for item in viewports)
    audit_findings = response.json()["audit_findings"]
    assert audit_findings["status"] == "available"
    assert len(audit_findings["findings"]) == 1
    assert audit_findings["findings"][0]["selector"] == "#oversized"
    assert audit_findings["findings"][0]["affected_viewports"] == [
        "tablet",
        "mobile",
    ]
    audit_summary = response.json()["audit_summary"]
    assert audit_summary["status"] == "available"
    assert audit_summary["horizontal_overflow_detected"] is True
    assert audit_summary["affected_viewports"] == ["tablet", "mobile"]
    assert [issue["selector"] for issue in audit_summary["issues"]] == [
        "#oversized"
    ]
    assert len({item["screenshot_ref"] for item in viewports}) == 3
    for item in viewports:
        screenshot_path = tmp_path / item["screenshot_ref"]
        assert screenshot_path.is_file()
        assert screenshot_path.stat().st_size > 0
    assert viewports[0]["finding_normalization"]["findings"] == []
    for viewport in viewports[1:]:
        element_finding = viewport["element_overflow_diagnosis"]["findings"][0]
        assert element_finding["layout_diagnosis_status"] == "available"
        assert element_finding["layout_evidence"]["computed_width"] == "900px"
        assert element_finding["layout_evidence"]["display_type"] == "block"
        finding = viewport["finding_normalization"]["findings"][0]
        assert finding["selector"] == "#oversized"
        assert finding["viewport_name"] == viewport["name"]
        assert finding["evidence_correlation"] == "direct_geometry_match"


def test_responsive_pipeline_analyzes_local_overflow_fixture(capture, fixture_server):
    results = asyncio.run(
        capture_responsive_viewports(
            f"{fixture_server}/responsive-overflow",
            capture.capture,
            destination_validator=LocalhostValidator(),
        )
    )

    assert [
        (result.name, result.viewport.width, result.viewport.height)
        for result in results
    ] == [
        ("desktop", 1365, 768),
        ("tablet", 768, 1024),
        ("mobile", 390, 844),
    ]

    for result in results:
        assert result.capture_outcome == "completed", result.details
        assert result.overflow_analysis_status == "available"
        assert result.element_overflow_diagnosis.status == "available"
        assert result.finding_normalization.status == "available"
        assert result.horizontal_overflow is not None
        assert result.horizontal_overflow.overflow_px == (
            result.horizontal_overflow.scroll_width
            - result.horizontal_overflow.visible_width
        )
        assert result.horizontal_overflow.potential_horizontal_overflow is (
            result.horizontal_overflow.scroll_width
            > result.horizontal_overflow.visible_width
        )
        assert result.screenshot_ref is not None
        screenshot_path = capture._storage._directory.parent / result.screenshot_ref
        assert screenshot_path.is_file()
        assert screenshot_path.stat().st_size > 0

    assert results[0].horizontal_overflow.potential_horizontal_overflow is False
    assert results[1].horizontal_overflow.potential_horizontal_overflow is True
    assert results[2].horizontal_overflow.potential_horizontal_overflow is True
    assert results[0].element_overflow_diagnosis.findings == []
    for result in results[1:]:
        findings = result.element_overflow_diagnosis.findings
        assert len(findings) == 1
        assert findings[0].selector == "#oversized"
        assert findings[0].viewport_width == result.viewport.width
        assert findings[0].layout_diagnosis_status == "available"
        assert findings[0].layout_evidence.computed_width == "900px"
        normalized = result.finding_normalization.findings
        assert len(normalized) == 1
        assert normalized[0].selector == "#oversized"
        assert normalized[0].viewport_name == result.name
        assert normalized[0].evidence_correlation == "direct_geometry_match"


def test_functional_ux_audit_checks_links_and_images_locally(
    capture, fixture_server
):
    results = asyncio.run(
        capture_responsive_viewports(
            f"{fixture_server}/functional-ux",
            capture.capture,
            destination_validator=BlocksTestExternalHost(),
        )
    )

    from app.main import ResponsiveCaptureResponse

    response = ResponsiveCaptureResponse.from_results(
        f"{fixture_server}/functional-ux", results
    )
    serialized_audit = response.model_dump()["viewports"][0]["functional_ux_audit"]
    assert serialized_audit["findings"]
    assert serialized_audit["inconclusive"]

    for viewport in results:
        audit = viewport.functional_ux_audit
        assert audit.status == "partial"
        assert audit.checked_links == 7
        assert audit.checked_images == 2
        observed = {
            (finding.rule_id, finding.element_selector): finding
            for finding in audit.findings
        }
        broken = observed[("broken_link", "#broken-link")]
        assert broken.failure_category == "http_error"
        assert broken.status == "observed_failure"
        assert broken.accessible_label == "Broken destination"

        assert ("broken_link", "#redirect-link") not in observed
        assert ("broken_link", "#successful-link") not in observed
        assert ("failed_image", "#successful-image") not in observed

        inconclusive = {
            finding.element_selector: finding for finding in audit.inconclusive
        }
        assert inconclusive["#slow-link"].failure_category == "timeout"
        assert inconclusive["#private-link"].failure_category == "blocked_destination"
        assert inconclusive["#unsafe-redirect"].failure_category == "blocked_destination"
        assert observed[("broken_link", "#network-link")].failure_category == "network_failure"
        assert inconclusive["#empty-source"].failure_category == "missing_source"
        assert ("failed_image", "#missing-source") in observed
        assert observed[("failed_image", "#missing-source")].failure_category == "missing_source"
        assert ("failed_image", "#broken-image") in observed
        assert observed[("failed_image", "#broken-image")].failure_category == "resource_load_failure"
        assert "#decorative-empty" not in {
            finding.element_selector for finding in audit.inconclusive + audit.findings
        }


def test_accessibility_scan_preserves_axe_results_and_specific_evidence(
    capture, fixture_server
):
    from app.analyzers.accessibility import scan_accessibility
    from app.analyzers.accessibility import WCAG_AA_TAGS

    scans = []
    tagged_criteria = []

    async def run_scan():
        async def scan_live_page(page):
            scans.append(await scan_accessibility(page))
            tagged_criteria.extend(
                await page.evaluate(
                    """tags => [...new Set(
                        axe.getRules(tags)
                            .filter(rule => rule.enabled)
                            .flatMap(rule => rule.tags)
                            .filter(tag => /^wcag\\d{3,4}$/.test(tag))
                    )].sort()""",
                    list(WCAG_AA_TAGS),
                )
            )

        evidence = await capture.capture(
            f"{fixture_server}/accessibility",
            1365,
            768,
            page_callback=scan_live_page,
        )
        return evidence

    evidence = asyncio.run(run_scan())
    assert evidence.outcome == "completed"
    assert len(scans) == 1
    result = scans[0]
    assert result.status == "available", result.details
    assert result.axe_version == "4.14.0"
    assert tagged_criteria == [
        "wcag111",
        "wcag122",
        "wcag131",
        "wcag135",
        "wcag141",
        "wcag1412",
        "wcag142",
        "wcag143",
        "wcag144",
        "wcag211",
        "wcag213",
        "wcag221",
        "wcag222",
        "wcag241",
        "wcag242",
        "wcag244",
        "wcag253",
        "wcag311",
        "wcag312",
        "wcag332",
        "wcag412",
    ]
    assert result.inapplicable
    assert result.incomplete
    assert result.passes

    violations = {rule.rule_id: rule for rule in result.violations}
    assert "label" in violations
    assert any(
        "#unlabeled-input" in node.target
        for node in violations["label"].nodes
    )
    assert "button-name" in violations
    assert any(
        "#unnamed-button" in node.target
        for node in violations["button-name"].nodes
    )
    assert "aria-required-parent" in violations
    assert any(
        "#orphaned-listitem" in node.target
        for node in violations["aria-required-parent"].nodes
    )
    assert "image-alt" in violations
    assert any("#missing-alt" in node.target for node in violations["image-alt"].nodes)
    assert not any(
        "#subjective-alt" in node.target
        for node in violations["image-alt"].nodes
    )
    contrast = {
        rule.rule_id: rule for rule in result.incomplete
    }["color-contrast"]
    assert any("#low-contrast" in node.target for node in contrast.nodes)
    assert any(node.failure_summary for node in contrast.nodes)
    assert all(rule.impact for rule in result.violations)
    assert all(rule.help_url.startswith("https://") for rule in result.violations)
    assert all(rule.tags for rule in result.violations)
    assert all(
        node.html and node.target
        for rule in result.violations
        for node in rule.nodes
    )
    unlabeled_node = next(
        node
        for node in violations["label"].nodes
        if "#unlabeled-input" in node.target
    )
    assert "[redacted]" in unlabeled_node.html
    assert "fixture-secret" not in unlabeled_node.html
    assert violations["label"].description
    assert violations["label"].help
    assert any(
        rule.rule_id == "label"
        and any("#valid-input" in node.target for node in rule.nodes)
        for rule in result.passes
    )
    assert any(
        rule.rule_id == "image-alt"
        and any("#valid-image" in node.target for node in rule.nodes)
        for rule in result.passes
    )
    assert any(
        rule.rule_id == "color-contrast"
        and any("#sufficient-contrast" in node.target for node in rule.nodes)
        for rule in result.passes
    )
    assert any(
        any(tag == "wcag111" for tag in rule.tags)
        for rule in result.violations
    )
    assert "complete" not in result.status

    from app.main import ResponsiveCaptureResponse
    from app.capture.responsive import (
        ElementOverflowDiagnosisResult,
        FindingNormalizationResult,
        ViewportCaptureResult,
    )
    from app.capture.models import ViewportDimensions

    api_result = ViewportCaptureResult(
        name="desktop",
        viewport=ViewportDimensions(1365, 768),
        capture_outcome=evidence.outcome,
        horizontal_overflow=None,
        overflow_analysis_status="missing_dimensions",
        screenshot_ref=evidence.screenshot_ref,
        element_overflow_diagnosis=ElementOverflowDiagnosisResult(
            status="not_attempted"
        ),
        finding_normalization=FindingNormalizationResult(
            status="not_attempted"
        ),
        accessibility_scan=result,
    )
    serialized = ResponsiveCaptureResponse.from_results(
        evidence.requested_url, [api_result]
    ).model_dump()["viewports"][0]["accessibility_scan"]
    assert serialized["violations"][0]["nodes"][0]["target"]
    assert serialized["violations"][0]["tags"]
    assert all(
        collection in serialized
        for collection in ("violations", "incomplete", "passes", "inapplicable")
    )


def test_element_overflow_diagnosis_uses_real_geometry_and_filters_candidates(
    fixture_server,
):
    async def diagnose_at_viewports():
        async with async_playwright() as playwright:
            browser = await playwright.chromium.launch()
            results_by_width = {}
            try:
                for width, height in (
                    (1365, 768),
                    (768, 1024),
                    (390, 844),
                ):
                    context = await browser.new_context(
                        viewport={"width": width, "height": height}
                    )
                    try:
                        page = await context.new_page()
                        response = await page.goto(
                            f"{fixture_server}/responsive-overflow",
                            wait_until="domcontentloaded",
                        )
                        assert response is not None and response.ok
                        results_by_width[width] = (
                            await diagnose_element_horizontal_overflow(page, width)
                        )
                    finally:
                        await context.close()
            finally:
                await browser.close()
        return results_by_width

    results_by_width = asyncio.run(diagnose_at_viewports())

    assert not any(
        result.selector == "#oversized" for result in results_by_width[1365]
    )
    for width, expected_overflow in ((768, 132), (390, 510)):
        findings = results_by_width[width]
        oversized = [item for item in findings if item.selector == "#oversized"]
        assert len(oversized) == 1
        finding = oversized[0]
        assert finding.tag_name == "div"
        assert finding.viewport_width == width
        assert finding.left == pytest.approx(0, abs=1)
        assert finding.right == pytest.approx(900, abs=1)
        assert finding.width == pytest.approx(900, abs=1)
        assert finding.overflow_px == pytest.approx(expected_overflow, abs=1)
        assert finding.status == "potential_overflow_source"
        assert finding.scrollable_context_detected is False
        assert finding.scrollable_container_selector is None

    mobile_findings = results_by_width[390]
    assert all(item.selector != "#in-bounds" for item in mobile_findings)
    assert all(item.selector != "#hidden" for item in mobile_findings)
    assert all(item.selector != "#nested" for item in mobile_findings)
    assert [item.selector for item in mobile_findings].count("#oversized") == 1


def test_layout_evidence_covers_fixed_width_descendants_layout_and_scrolling(
    fixture_server,
):
    async def inspect_fixtures():
        async with async_playwright() as playwright:
            browser = await playwright.chromium.launch()
            results = {}
            try:
                for path in (
                    "/layout-fixed-width",
                    "/layout-oversized-descendant",
                    "/layout-flex-grid",
                    "/layout-horizontal-scroll",
                ):
                    context = await browser.new_context(
                        viewport={"width": 390, "height": 844}
                    )
                    try:
                        page = await context.new_page()
                        response = await page.goto(
                            f"{fixture_server}{path}",
                            wait_until="domcontentloaded",
                        )
                        assert response is not None and response.ok
                        raw = await diagnose_element_horizontal_overflow(page, 390)
                        results[path] = await enrich_element_layout_evidence(
                            page, raw, 390
                        )
                    finally:
                        await context.close()
            finally:
                await browser.close()
        return results

    results = asyncio.run(inspect_fixtures())

    fixed = next(item for item in results["/layout-fixed-width"] if item.selector == "#fixed-width")
    assert fixed.layout_diagnosis_status == "available"
    assert fixed.layout_evidence.computed_width == "900px"
    assert fixed.layout_evidence.width == pytest.approx(900)
    assert fixed.layout_evidence.scroll_width >= fixed.layout_evidence.client_width
    assert fixed.layout_evidence.position == "static"

    parent = next(
        item
        for item in results["/layout-oversized-descendant"]
        if item.selector == "#oversized-parent"
    )
    assert parent.layout_diagnosis_status == "available"
    assert any(
        child.selector == "#oversized-child"
        for child in parent.layout_evidence.oversized_children
    )
    assert any(
        hypothesis.label == "oversized_descendant"
        for hypothesis in parent.layout_evidence.hypotheses
    )

    flex_item = next(
        item
        for item in results["/layout-flex-grid"]
        if item.selector == "#flex-item"
    )
    assert any(
        ancestor.display_type == "flex"
        for ancestor in flex_item.layout_evidence.ancestors
    )
    assert any(
        hypothesis.label == "flex_or_grid_layout_context"
        for hypothesis in flex_item.layout_evidence.hypotheses
    )
    grid_item = next(
        item
        for item in results["/layout-flex-grid"]
        if item.selector == "#grid-item"
    )
    assert any(
        ancestor.display_type == "grid"
        for ancestor in grid_item.layout_evidence.ancestors
    )

    scroll_content = next(
        item
        for item in results["/layout-horizontal-scroll"]
        if item.selector == "#scroll-content"
    )
    assert scroll_content.layout_evidence.horizontal_scrolling_enabled is True
    assert "#scroll-container" in scroll_content.layout_evidence.scrollable_context_selectors
    assert any(
        hypothesis.label == "horizontal_scrolling_enabled"
        for hypothesis in scroll_content.layout_evidence.hypotheses
    )


def test_removed_selector_reports_layout_evidence_unavailable(fixture_server):
    async def inspect_removed_element():
        async with async_playwright() as playwright:
            browser = await playwright.chromium.launch()
            try:
                page = await browser.new_page(viewport={"width": 390, "height": 844})
                response = await page.goto(
                    f"{fixture_server}/layout-fixed-width",
                    wait_until="domcontentloaded",
                )
                assert response is not None and response.ok
                raw = await diagnose_element_horizontal_overflow(page, 390)
                await page.evaluate(
                    "() => document.querySelector('#fixed-width').remove()"
                )
                return await enrich_element_layout_evidence(page, raw, 390)
            finally:
                await browser.close()

    results = asyncio.run(inspect_removed_element())
    fixed = next(item for item in results if item.selector == "#fixed-width")

    assert fixed.layout_diagnosis_status == "unavailable"
    assert fixed.layout_evidence is None
    assert fixed.layout_diagnosis_details == ["Element no longer exists."]


def test_horizontal_overflow_is_recorded(fixture_server, capture):
    evidence = asyncio.run(capture.capture(f"{fixture_server}/overflow", 800, 600))
    assert evidence.document.scroll_width > evidence.document.visible_width


def test_delayed_dom_update_is_seen_after_settling(fixture_server, capture):
    evidence = asyncio.run(capture.capture(f"{fixture_server}/delayed", 800, 600))
    assert evidence.page_title == "Delayed fixture updated"


def test_failed_resource_is_captured(fixture_server, capture):
    evidence = asyncio.run(
        capture.capture(f"{fixture_server}/failed-resource", 800, 600)
    )
    assert any("/missing.png" in request.url for request in evidence.failed_requests)


def test_request_guard_blocks_prohibited_subresource(fixture_server, tmp_path):
    service = BrowserCapture(
        storage=LocalScreenshotStorage(tmp_path),
        url_validator=BlocksTestExternalHost(),
        settling_period_ms=50,
    )
    evidence = asyncio.run(
        service.capture(f"{fixture_server}/blocked-resource", 800, 600)
    )
    assert evidence.outcome == "partial"
    assert any("private.invalid" in request.url for request in evidence.failed_requests)


def test_uncaught_javascript_error_is_captured(fixture_server, capture):
    evidence = asyncio.run(
        capture.capture(f"{fixture_server}/javascript-error", 800, 600)
    )
    assert any("fixture boom" in error for error in evidence.uncaught_page_errors)


def test_navigation_timeout_returns_explicit_outcome(fixture_server, capture):
    evidence = asyncio.run(capture.capture(f"{fixture_server}/timeout", 800, 600))
    assert evidence.outcome == "navigation_timeout"
    assert evidence.navigation_status == "timeout"
    assert evidence.details


def test_capture_failure_still_closes_browser_resources(tmp_path, monkeypatch):
    import app.capture.runner as runner

    closed = []

    class FakeResource:
        async def close(self):
            closed.append(type(self).__name__)

    class FakePage(FakeResource):
        def on(self, *_args):
            pass

        async def route(self, *_args):
            pass

    class FakeContext(FakeResource):
        async def new_page(self):
            return FakePage()

    class FakeBrowser(FakeResource):
        async def new_context(self, **_kwargs):
            return FakeContext()

    class FakeChromium:
        async def launch(self):
            return FakeBrowser()

    class FakePlaywright:
        chromium = FakeChromium()

    class FakeManager:
        async def __aenter__(self):
            return FakePlaywright()

        async def __aexit__(self, *_args):
            return False

    monkeypatch.setattr(runner, "async_playwright", lambda: FakeManager())
    service = BrowserCapture(
        storage=LocalScreenshotStorage(tmp_path),
        url_validator=LocalhostValidator(),
    )
    with pytest.raises(AttributeError):
        asyncio.run(service.capture("http://example.com", 800, 600))
    assert closed == ["FakePage", "FakeContext", "FakeBrowser"]


def test_public_url_validator_rejects_embedded_credentials():
    with pytest.raises(UnsafeURL, match="credentials"):
        asyncio.run(
            PublicURLSafetyValidator().validate("https://user:pass@example.com/")
        )


def test_public_url_validator_rejects_loopback():
    with pytest.raises(UnsafeURL, match="prohibited network destination"):
        asyncio.run(PublicURLSafetyValidator().validate("http://127.0.0.1/"))


def test_recorded_urls_remove_credentials_and_redact_tokens():
    recorded = sanitize_url(
        "https://user:pass@example.com/path?token=secret&view=full#fragment"
    )
    assert recorded == (
        "https://example.com/path?token=%5Bredacted%5D&view=full"
    )


def test_api_returns_structured_invalid_url_outcome():
    from app.main import CaptureRequest, create_capture

    with pytest.raises(HTTPException) as raised:
        asyncio.run(create_capture(CaptureRequest(url="ftp://example.com")))
    assert raised.value.status_code == 400
    assert raised.value.detail["outcome"] == "invalid_or_prohibited_url"
