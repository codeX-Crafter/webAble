from __future__ import annotations

import asyncio
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal, Protocol

from app.capture.url_safety import sanitize_url

AccessibilityScanStatus = Literal[
    "available", "partial", "unavailable", "not_attempted"
]

AXE_CORE_VERSION = "4.14.0"
AXE_CORE_SCRIPT = (
    Path(__file__).resolve().parents[2]
    / "node_modules"
    / "axe-core"
    / "axe.min.js"
)
WCAG_AA_TAGS = (
    "wcag2a",
    "wcag2aa",
    "wcag21a",
    "wcag21aa",
    "wcag22aa",
)
SCAN_TIMEOUT_SECONDS = 20
ACCESSIBILITY_SCAN_TIMEOUT_SECONDS = SCAN_TIMEOUT_SECONDS
MAX_RULES_PER_RESULT = 500
MAX_NODES_PER_RULE = 100
MAX_CHECKS_PER_NODE = 30
MAX_TOTAL_NODES = 1_000
MAX_RELATED_NODES_PER_CHECK = 20
MAX_SNIPPET_LENGTH = 2_000
_VALUE_ATTRIBUTE = re.compile(
    r"""(\bvalue\s*=\s*)(["']).*?\2""", re.IGNORECASE | re.DOTALL
)
_URL_ATTRIBUTE = re.compile(
    r"""(\b(?:href|src|action)\s*=\s*)(["'])(.*?)\2""",
    re.IGNORECASE | re.DOTALL,
)


@dataclass(frozen=True)
class AxeCheckEvidence:
    check_id: str
    impact: str | None
    message: str
    data: dict | list | str | int | float | bool | None
    related_nodes: list[dict]


@dataclass(frozen=True)
class AxeNodeEvidence:
    target: list[str | list[str]]
    html: str
    impact: str | None
    failure_summary: str | None
    any_checks: list[AxeCheckEvidence]
    all_checks: list[AxeCheckEvidence]
    none_checks: list[AxeCheckEvidence]


@dataclass(frozen=True)
class AxeRuleEvidence:
    rule_id: str
    description: str
    impact: str | None
    help: str
    help_url: str
    tags: list[str]
    nodes: list[AxeNodeEvidence]
    failure_summaries: list[str]


@dataclass(frozen=True)
class AccessibilityScanResult:
    status: AccessibilityScanStatus
    axe_version: str | None = None
    violations: list[AxeRuleEvidence] = field(default_factory=list)
    incomplete: list[AxeRuleEvidence] = field(default_factory=list)
    passes: list[AxeRuleEvidence] = field(default_factory=list)
    inapplicable: list[AxeRuleEvidence] = field(default_factory=list)
    details: list[str] = field(default_factory=list)


class AccessibilityPage(Protocol):
    async def add_script_tag(self, *, content: str) -> object:
        ...

    async def evaluate(self, expression: str, argument: list[str]) -> dict:
        ...


async def scan_accessibility(
    page: AccessibilityPage,
    *,
    script_path: Path = AXE_CORE_SCRIPT,
    timeout_seconds: int = SCAN_TIMEOUT_SECONDS,
) -> AccessibilityScanResult:
    """Run WCAG A/AA tagged axe rules on an already loaded Playwright page."""
    try:
        script = script_path.read_text(encoding="utf-8")
    except OSError:
        return AccessibilityScanResult(
            status="unavailable",
            details=[
                "The pinned axe-core script is unavailable; install JavaScript dependencies with npm ci."
            ],
        )

    try:
        await page.add_script_tag(content=script)
        raw_result = await asyncio.wait_for(
            page.evaluate(
                """async (tags) => {
                    if (!window.axe || typeof window.axe.run !== "function") {
                        throw new Error("axe-core did not initialize.");
                    }
                    return window.axe.run(document, {
                        runOnly: {type: "tag", values: tags}
                    });
                }""",
                list(WCAG_AA_TAGS),
            ),
            timeout=timeout_seconds,
        )
    except TimeoutError:
        return AccessibilityScanResult(
            status="unavailable",
            details=["The accessibility engine exceeded its time limit."],
        )
    except Exception as error:
        return AccessibilityScanResult(
            status="unavailable",
            details=[
                f"The accessibility engine could not complete ({type(error).__name__})."
            ],
        )

    try:
        collections = {
            key: raw_result[key]
            for key in ("violations", "incomplete", "passes", "inapplicable")
        }
        details: list[str] = []
        normalized = {}
        remaining_nodes = MAX_TOTAL_NODES
        for key, rules in collections.items():
            if not isinstance(rules, list):
                raise TypeError("axe result collections must be lists.")
            if len(rules) > MAX_RULES_PER_RESULT:
                details.append(
                    f"The {key} collection was limited to {MAX_RULES_PER_RESULT} rules."
                )
            normalized_rules = []
            for rule in rules[:MAX_RULES_PER_RESULT]:
                node_limit = min(MAX_NODES_PER_RULE, remaining_nodes)
                normalized_rule = _rule_evidence(rule, details, node_limit)
                normalized_rules.append(normalized_rule)
                remaining_nodes -= len(normalized_rule.nodes)
            normalized[key] = normalized_rules
        axe_version = raw_result.get("testEngine", {}).get("version")
        if axe_version != AXE_CORE_VERSION:
            details.append(
                "The reported axe-core version did not match the pinned package version."
            )
        return AccessibilityScanResult(
            status="partial" if details else "available",
            axe_version=axe_version,
            violations=normalized["violations"],
            incomplete=normalized["incomplete"],
            passes=normalized["passes"],
            inapplicable=normalized["inapplicable"],
            details=details,
        )
    except (KeyError, TypeError, ValueError):
        return AccessibilityScanResult(
            status="unavailable",
            details=["The accessibility engine returned an invalid result structure."],
        )


def _rule_evidence(
    rule: dict, details: list[str], node_limit: int
) -> AxeRuleEvidence:
    if not isinstance(rule, dict):
        raise TypeError("axe rule result must be an object.")
    raw_nodes = rule.get("nodes", [])
    if not isinstance(raw_nodes, list):
        raise TypeError("axe rule nodes must be a list.")
    if len(raw_nodes) > node_limit:
        details.append(
            f"Rule {rule.get('id', 'unknown')} node evidence was limited to {node_limit} nodes."
        )
    nodes = [
        _node_evidence(node, details)
        for node in raw_nodes[:node_limit]
    ]
    return AxeRuleEvidence(
        rule_id=str(rule["id"]),
        description=str(rule.get("description", "")),
        impact=rule.get("impact"),
        help=str(rule.get("help", "")),
        help_url=str(rule.get("helpUrl", "")),
        tags=[str(tag) for tag in rule.get("tags", [])],
        nodes=nodes,
        failure_summaries=[
            node.failure_summary for node in nodes if node.failure_summary
        ],
    )


def _node_evidence(node: dict, details: list[str]) -> AxeNodeEvidence:
    if not isinstance(node, dict):
        raise TypeError("axe node result must be an object.")
    html = _bounded_html(str(node.get("html", "")), details)

    checks = {
        key: [
            _check_evidence(check, details)
            for check in node.get(key, [])[:MAX_CHECKS_PER_NODE]
        ]
        for key in ("any", "all", "none")
    }
    if any(len(node.get(key, [])) > MAX_CHECKS_PER_NODE for key in checks):
        details.append("One or more axe check lists were truncated.")
    return AxeNodeEvidence(
        target=node.get("target", []),
        html=html,
        impact=node.get("impact"),
        failure_summary=node.get("failureSummary"),
        any_checks=checks["any"],
        all_checks=checks["all"],
        none_checks=checks["none"],
    )


def _sanitize_snippet_url(value: str) -> str:
    return sanitize_url(value)


def _sanitize_html(html: str) -> str:
    html = _VALUE_ATTRIBUTE.sub(r"\1\2[redacted]\2", html)
    return _URL_ATTRIBUTE.sub(
        lambda match: (
            f"{match.group(1)}{match.group(2)}"
            f"{_sanitize_snippet_url(match.group(3))}{match.group(2)}"
        ),
        html,
    )


def _bounded_html(html: str, details: list[str]) -> str:
    html = _sanitize_html(html)
    if len(html) > MAX_SNIPPET_LENGTH:
        details.append("One or more HTML evidence snippets were truncated.")
        return html[:MAX_SNIPPET_LENGTH] + "..."
    return html


def _check_evidence(check: dict, details: list[str]) -> AxeCheckEvidence:
    if not isinstance(check, dict):
        raise TypeError("axe check result must be an object.")
    raw_related_nodes = check.get("relatedNodes", [])
    if len(raw_related_nodes) > MAX_RELATED_NODES_PER_CHECK:
        details.append("One or more axe related-node lists were truncated.")
    return AxeCheckEvidence(
        check_id=str(check.get("id", "")),
        impact=check.get("impact"),
        message=str(check.get("message", "")),
        data=check.get("data"),
        related_nodes=[
            {
                **related_node,
                "html": _bounded_html(
                    str(related_node.get("html", "")), details
                ),
            }
            for related_node in raw_related_nodes[:MAX_RELATED_NODES_PER_CHECK]
            if isinstance(related_node, dict)
        ],
    )
