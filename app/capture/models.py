from dataclasses import dataclass, field
from datetime import datetime
from typing import Literal


NavigationStatus = Literal["completed", "timeout", "failed"]
ReadinessStatus = Literal["ready", "partial", "unavailable"]
CaptureOutcome = Literal["completed", "partial", "navigation_timeout"]


@dataclass(frozen=True)
class ViewportDimensions:
    width: int
    height: int


@dataclass(frozen=True)
class DocumentDimensions:
    scroll_width: int | None
    scroll_height: int | None
    visible_width: int | None
    visible_height: int | None


@dataclass(frozen=True)
class FailedRequest:
    url: str
    resource_type: str
    error: str | None


@dataclass
class BrowserEvidence:
    requested_url: str
    final_url: str | None
    page_title: str | None
    viewport: ViewportDimensions
    document: DocumentDimensions
    screenshot_ref: str | None
    navigation_duration_ms: int
    settling_duration_ms: int
    browser_name: str
    scanned_at: datetime
    console_errors: list[str] = field(default_factory=list)
    uncaught_page_errors: list[str] = field(default_factory=list)
    failed_requests: list[FailedRequest] = field(default_factory=list)
    navigation_status: NavigationStatus = "failed"
    readiness_status: ReadinessStatus = "unavailable"
    outcome: CaptureOutcome = "partial"
    details: list[str] = field(default_factory=list)
