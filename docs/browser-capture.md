# Browser capture foundation

Run `npm ci` to install the pinned local axe-core rules bundle. Then run the API
with `python run_server.py` after installing `requirements.txt` and
installing Playwright's Chromium browser with
`python -m playwright install chromium`. On Windows, the launcher selects the
Proactor event-loop policy and runs Uvicorn without reload; restart it manually
after backend code changes. The capture endpoint is `POST /captures` and accepts
a URL. Each request captures desktop (1365x768), tablet (768x1024), and mobile
(390x844) sequentially, returning a distinct screenshot reference for each
successful viewport. At most two multi-viewport requests run concurrently. The
overall request deadline allows for all three configured navigation and settling
periods, bounded link-check budget, and accessibility scan budget. Each successful
viewport response includes document-level horizontal overflow measurements and a separate
element-level diagnosis from the same live page; diagnosis failures do not
discard a successful capture or screenshot.
Each raw element candidate also carries bounded layout evidence when available:
its scroll/client widths, bounding geometry, computed sizing and positioning
styles, up to five ancestors, and up to eight oversized descendants from a bounded
three-level/50-node descendant scan. Flex/grid context and enabled horizontal
scrolling are recorded. Possible layout explanations are explicitly hypotheses
supported by these measurements, not root-cause claims. Stale selectors and
per-element style errors are reported as layout-evidence limitations without
discarding the raw candidate or failing the capture.
Normalized overflow findings preserve the raw element measurements and classify
their geometric relationship to document overflow. A direct geometry match requires
both the element's right edge and overflow amount to agree with the document-level
measurement within 2 px; it is not proof of causation. Other measured candidates
are marked `possible_contributor`, while missing page-level evidence is `unmatched`.
The finding ID is deterministic for the rule, selector, viewport name, and width.
Normalization removes only repeated measurements with the same tag and geometry
whose selectors are identical or one is an ancestor path of the other. It does not
deduplicate merely overlapping elements, and selector path equivalence is
conservative: semantically equivalent CSS selectors that use different syntax may
remain separate.
The response also includes audit-level `audit_findings`, grouping normalized
findings by exact rule identifier and selector across viewports while retaining
each viewport-specific finding and its measurements. A group is prioritized as
`direct_geometry_match` if any member has that classification; otherwise it uses
`possible_contributor` when present, or `unmatched`. These labels express
relative evidential support, not severity or a numeric score. Incomplete
normalization yields partial aggregation while preserving groups from available
viewports.
The response's `audit_summary` separately summarizes document-level overflow by
viewport and lists normalized element candidates as issues. Issues are ordered by
evidence class (`direct_geometry_match`, `possible_contributor`, then `unmatched`),
with rule, selector, and group ID as deterministic tie-breakers. Each issue includes
viewport widths, measured element/document overflow, its evidence classification,
and cautious wording that avoids claiming causation. Capture and analysis
limitations are listed separately from findings; missing measurements are not
reported as clean results.

Each successfully loaded viewport also includes a read-only `functional_ux_audit`.
It inspects rendered anchors and images from the existing live page. HTTP(S) link
destinations receive bounded `HEAD` checks; redirects are followed manually with
destination validation on every hop, up to five redirects. `404` and other
conclusive `4xx`/`5xx` responses and network failures are reported as observed
broken-link findings. Successful `2xx` responses are omitted. Authentication or
access denials, rate limiting, unsupported `HEAD`, timeouts, non-web URL schemes,
and prohibited destinations remain in the separate `inconclusive` list; they are
not represented as confirmed broken links. Checks are limited to 15 rendered
links and run concurrently with per-link deadlines; the API deadline accounts
for this bounded per-viewport check time.

Rendered images are reported as failed only when a non-empty source finishes with
`naturalWidth` equal to zero, or when an image with an accessible label has no
source. Images without a source and without enough content context are kept
inconclusive; explicitly decorative or hidden images are not flagged. Resources
that are still loading remain inconclusive. The audit never clicks links or uses
GET to check link destinations, and it does not submit forms. Because some servers
reject or handle `HEAD` differently from normal navigation, results are cautious
indicators rather than proof that a user-facing navigation will fail. Only
rendered anchors are checked, and the audit is repeated per viewport.

Each successfully loaded viewport also includes `accessibility_scan`, produced by
axe-core 4.14.0 on the same live Playwright page. It runs only rules tagged with
WCAG 2.0/2.1/2.2 Level A or AA tags; best-practice-only and AAA-only rules are
not selected. Rule tags, impact, descriptions, help, help URL, node selectors,
bounded/redacted HTML snippets, checks, and failure summaries are retained in
separate `violations`, `incomplete`, `passes`, and `inapplicable` collections.
An incomplete axe result is for human review, never a confirmed violation.
`available` means the engine completed, not that the page passed or conforms.
Execution failures and missing local axe assets are explicitly `unavailable`;
they do not discard capture, screenshot, overflow, layout, or functional UX
results. The full WCAG 2.2 A/AA criterion inventory and limitations are in
[accessibility-coverage-v1.md](./accessibility-coverage-v1.md).

Automated checks cannot decide whether alternative text is meaningful, whether
content order or instructions make sense, whether all keyboard flows work, or
whether media and dynamic interactions are accessible. Hidden states, zoom/reflow,
live media, assistive-technology output, and cross-page criteria are not evaluated
by this scan. A clean or empty violations collection is not evidence of WCAG
conformance. This use of axe-core is locally hosted and makes no service request
to Deque; however, the scanned site is untrusted content running in Chromium, and
the tool is not a substitute for expert/manual evaluation.

Each scan launches an isolated Chromium browser context, records browser errors,
waits for `DOMContentLoaded` with a 15-second default timeout, then waits 1.5 seconds
before collecting page dimensions and an initial-viewport screenshot. Configure these
intervals with `WEBABLE_NAVIGATION_TIMEOUT_MS` and `WEBABLE_SETTLING_PERIOD_MS`.
The settling period is a practical baseline for allowing common delayed updates; it is
not a guarantee that every dynamic page has finished loading.

Screenshots are stored locally under the ignored `output/screenshots/` directory.
The API returns only a relative screenshot reference; the storage interface can be
replaced with object storage later. Do not serve the output directory publicly.

URL checks reject non-HTTP(S) URLs, embedded credentials, local/internal hostnames,
and DNS results that are not public IP addresses. The same check runs before
navigation and for each browser request, including redirects. This is a useful
development safeguard, **not a public-deployment security guarantee**: Chromium
performs its own DNS resolution after the check, so DNS rebinding/time-of-check
versus time-of-use attacks are not fully prevented. Functional UX `HEAD` checks
validate every redirect hop, but the request client resolves the destination
again after validation, so the same network-level limitation applies. Deployments exposed to
untrusted users still need network-level egress controls or a validating proxy that
pins approved destinations and blocks private/internal address ranges. DNS lookups
also run in the application process. Browser HTTP interception does not validate
WebSocket connections or other browser-managed network paths. This implementation
has no authentication or multi-tenant screenshot isolation.

Evidence intentionally excludes HTML documents, response bodies, cookies, and
headers. URL fragments and embedded URL credentials are removed from recorded URLs,
and common credential-like query parameter values are redacted. Other query values
are preserved because they may be required to reproduce the requested page.
