# WebAble accessibility coverage matrix — WCAG 2.2 A/AA v1.0

**Baseline:** WCAG 2.2 Level A and AA, W3C Recommendation  
**Matrix version:** 1.0 (2026-10-28)  
**Engine:** axe-core 4.14.0, run against rendered content at each captured viewport

Standards and engine references:
[WCAG 2.2 Recommendation](https://www.w3.org/TR/WCAG22/),
[W3C evaluation guidance](https://www.w3.org/WAI/test-evaluate/),
[WCAG 2.2 Understanding documents](https://www.w3.org/WAI/WCAG22/Understanding/),
[axe-core API and tag definitions](https://github.com/dequelabs/axe-core/blob/develop/doc/API.md),
and [axe-core rule descriptions](https://github.com/dequelabs/axe-core/blob/develop/doc/rule-descriptions.md).

This matrix is a traceability inventory, not a conformance claim. WCAG success
criteria are technology-neutral; axe rule tags describe a rule's stated mapping
and do not establish that the rule covers every situation within a criterion.
The scanner enables axe rules tagged `wcag2a`, `wcag2aa`, `wcag21a`,
`wcag21aa`, or `wcag22aa`. It preserves the exact criterion tags returned with
each axe rule (for example `wcag111`). A criterion is **not** recorded as covered
when no matching result is returned: the applicable rule may not have run, may
not exist, or may not have emitted that result.

W3C states that evaluation tools cannot alone determine whether a site meets
accessibility standards and that knowledgeable human evaluation is required.
`available` means the axe run completed; it does not mean that violations are
absent, that all criteria were tested, or that a page is accessible.

## Result semantics and collected evidence

| Result collection | Meaning |
|---|---|
| `violations` | Axe classified a rule result as a failure. It is an automated finding, scoped to the rule and supplied evidence. |
| `incomplete` | Axe could not determine a result confidently; human review is required. This is not a violation. |
| `passes` | Axe rule checks passed for the nodes it reports. This does not prove the entire criterion passes. |
| `inapplicable` | Axe determined that the rule did not apply to the scanned content. This is not a page-wide pass. |
| `unavailable` / `not_attempted` | The engine did not produce a usable result; never reinterpret as an empty successful scan. |

For each returned rule WebAble preserves rule ID, description, impact, help,
help URL, tags, affected node targets, bounded HTML snippets, node impact,
rule-specific failure summaries, and axe `any`/`all`/`none` check evidence.
Impact is axe's impact label, not a confidence score. Incomplete results remain
separate from violations. HTML snippets are bounded and redact `value`
attributes and credential-like URL query values; snippets can still contain
user-authored text.

## Criterion inventory

Abbreviations: **P** = principle (Perceivable, Operable, Understandable,
Robust); **Auto** = automation outlook (Automatable signal, Partial, Manual);
**Axe coverage** = enabled tagged rule exists in the pinned engine; a page result
is present only when that rule runs and returns the criterion tag;
**Evidence** = rule/tag, target, snippet, checks, and failure
summary when axe supplies them; **Limit** = missing output means untested, and
automated results do not decide full criterion conformance. The method is the
current axe tag-filtered scan plus focused fixture testing where listed; other
methods are future work requiring validation against W3C Understanding and
Techniques documents.

For axe-core 4.14.0, inspection of enabled rules selected by the configured
version/level tags found criterion tags for: `wcag111`, `wcag122`, `wcag131`,
`wcag135`, `wcag141`, `wcag1412`, `wcag142`, `wcag143`, `wcag144`, `wcag211`,
`wcag221`, `wcag222`, `wcag241`, `wcag242`, `wcag244`, `wcag253`, `wcag311`,
`wcag312`, `wcag332`, and `wcag412`. Other A/AA criterion tags in this matrix
had no enabled selected rule in that pinned version. A tag is only a rule
mapping, not a guarantee of full criterion coverage. Axe can return additional
tags for other criteria on a rule selected because it also has an A/AA version
tag; this matrix inventories A/AA only.

| Criterion | Name | Level | P | Auto | Enabled axe tag in v1.0 | Check / evidence method | Inconclusive or remaining limitation |
|---|---|---:|---|---|---|---|---|
| 1.1.1 | Non-text Content | A | Perceivable | Partial | Yes: `wcag111` | Axe node evidence; fixture checks missing image alternative | Usefulness/equivalence of text alternatives requires human judgment |
| 1.2.1 | Audio-only and Video-only (Prerecorded) | A | Perceivable | Manual | No enabled tag in 4.14.0 | Axe output if tagged; future media/player review | Media alternatives and synchronized content need human review |
| 1.2.2 | Captions (Prerecorded) | A | Perceivable | Manual | Yes: `wcag122` | Future inspection of media and caption synchronization | Caption accuracy and completeness are semantic |
| 1.2.3 | Audio Description or Media Alternative (Prerecorded) | A | Perceivable | Manual | No enabled tag in 4.14.0 | Future media alternative review | Meaningful visual information and equivalence require human review |
| 1.2.4 | Captions (Live) | AA | Perceivable | Manual | No enabled tag in 4.14.0 | Future live-media evaluation | Requires live content and caption quality review |
| 1.2.5 | Audio Description (Prerecorded) | AA | Perceivable | Manual | No enabled tag in 4.14.0 | Future media and audio-description review | Accurate description cannot be inferred from markup |
| 1.3.1 | Info and Relationships | A | Perceivable | Partial | Yes: `wcag131` | Axe structure/ARIA rule evidence where mapped | Visual and programmatic relationships may differ in context |
| 1.3.2 | Meaningful Sequence | A | Perceivable | Manual | No enabled tag in 4.14.0 | Future reading-order review | Meaning depends on intended presentation |
| 1.3.3 | Sensory Characteristics | A | Perceivable | Manual | No enabled tag in 4.14.0 | Future content review | Instructions and meaning need contextual interpretation |
| 1.3.4 | Orientation | AA | Perceivable | Partial | No enabled tag in 4.14.0 | Future rotate/reflow viewport tests | Device orientation behavior is not established by static DOM |
| 1.3.5 | Identify Input Purpose | AA | Perceivable | Partial | Yes: `wcag135` | Axe form metadata evidence where mapped | Input purpose may depend on personal-data context |
| 1.4.1 | Use of Color | A | Perceivable | Partial | Yes: `wcag141` | Future visual/content review; axe where tagged | Color's meaning and redundant cues need context |
| 1.4.2 | Audio Control | A | Perceivable | Partial | Yes: `wcag142` | Future timed audio/player inspection | Duration, playback behavior, and control usability need interaction |
| 1.4.3 | Contrast (Minimum) | AA | Perceivable | Partial | Yes: `wcag143` | Axe contrast result; local low/high contrast fixtures | Backgrounds, images, overlays, and text rendered dynamically can be incomplete |
| 1.4.4 | Resize Text | AA | Perceivable | Partial | Yes: `wcag144` | Future browser zoom/text-resize testing | Requires rendering and content usability checks at increased text size |
| 1.4.5 | Images of Text | AA | Perceivable | Manual | No enabled tag in 4.14.0 | Future visual content review | Determining whether text is essential or replaceable is contextual |
| 1.4.10 | Reflow | AA | Perceivable | Partial | No enabled tag in 4.14.0 | Existing viewport capture is not a reflow conformance test; future zoom/reflow checks | Must evaluate content at required zoom and both writing directions |
| 1.4.11 | Non-text Contrast | AA | Perceivable | Partial | No enabled tag in 4.14.0 | Axe where supported; future component-state contrast review | Boundaries, states, and adjacent colors require rendered/contextual review |
| 1.4.12 | Text Spacing | AA | Perceivable | Partial | Yes: `wcag1412` | Future injected text-spacing style and clipping review | Requires checking content/function after styles change |
| 1.4.13 | Content on Hover or Focus | AA | Perceivable | Partial | No enabled tag in 4.14.0 | Future keyboard/pointer interaction tests | Dismissal, persistence, and hover/focus behavior require interaction |
| 2.1.1 | Keyboard | A | Operable | Manual | Yes: `wcag211` | Future keyboard traversal and operation tests | Static markup cannot show whether every function works by keyboard |
| 2.1.2 | No Keyboard Trap | A | Operable | Manual | No enabled tag in 4.14.0 | Future keyboard interaction tests | Requires entering/leaving interactive components |
| 2.1.4 | Character Key Shortcuts | A | Operable | Manual | No enabled tag in 4.14.0 | Future keyboard shortcut interaction review | Shortcuts and user-configurable controls need runtime behavior |
| 2.2.1 | Timing Adjustable | A | Operable | Manual | Yes: `wcag221` | Future timed-session interaction review | Timers, exceptions, and adjustment choices need user-flow context |
| 2.2.2 | Pause, Stop, Hide | A | Operable | Partial | Yes: `wcag222` | Future moving/blinking content and control review | Motion duration and control effectiveness require observation |
| 2.3.1 | Three Flashes or Below Threshold | A | Perceivable | Manual | No enabled tag in 4.14.0 | Future media/frame analysis | Accurate flash frequency/area requires temporal visual measurement |
| 2.4.1 | Bypass Blocks | A | Operable | Partial | Yes: `wcag241` | Axe landmark/skip-link signals where tagged | A link's actual bypass and repeated-block behavior need review |
| 2.4.2 | Page Titled | A | Operable | Automatable signal | Yes: `wcag242` | Axe title rule; document title fixture | Title quality and distinction between pages are contextual |
| 2.4.3 | Focus Order | A | Operable | Manual | No enabled tag in 4.14.0 | Future keyboard focus sequence testing | Order's meaning and operation require interaction |
| 2.4.4 | Link Purpose (In Context) | A | Operable | Partial | Yes: `wcag244` | Axe link-name signals; future context review | Whether purpose is clear in surrounding content is semantic |
| 2.4.5 | Multiple Ways | AA | Operable | Manual | No enabled tag in 4.14.0 | Future multi-page/site navigation inventory | Requires a representative set of pages and navigation methods |
| 2.4.6 | Headings and Labels | AA | Operable | Partial | No enabled tag in 4.14.0 | Axe name/heading signals; content review | Whether wording accurately describes content or purpose is contextual |
| 2.4.7 | Focus Visible | AA | Operable | Manual | No enabled tag in 4.14.0 | Future keyboard focus and visual-state inspection | Requires interactions and visual comparison of focus states |
| 2.4.11 | Focus Not Obscured (Minimum) | AA | Operable | Partial | No enabled tag in 4.14.0 | Future focus/scroll geometry and occlusion tests | Sticky overlays and focus state need browser interaction |
| 2.5.1 | Pointer Gestures | A | Operable | Manual | No enabled tag in 4.14.0 | Future pointer gesture alternatives testing | Gesture equivalence requires operating the interface |
| 2.5.2 | Pointer Cancellation | A | Operable | Manual | No enabled tag in 4.14.0 | Future pointer down/up/cancel interaction tests | Event timing and cancellation behavior are dynamic |
| 2.5.3 | Label in Name | A | Operable | Partial | Yes: `wcag253` | Axe accessible-name checks where tagged | Spoken-label usability needs human/assistive-technology review |
| 2.5.4 | Motion Actuation | A | Operable | Manual | No enabled tag in 4.14.0 | Future device-motion and alternative-control review | Requires device capabilities and interaction |
| 2.5.7 | Dragging Movements | AA | Operable | Manual | No enabled tag in 4.14.0 | Future pointer/touch interaction and single-pointer alternative tests | Alternative operation must be exercised |
| 2.5.8 | Target Size (Minimum) | AA | Operable | Partial | No enabled tag in 4.14.0 | Axe target-size signal where tagged; geometry tests | Exceptions, spacing, and overlapping targets need contextual validation |
| 3.1.1 | Language of Page | A | Understandable | Automatable signal | Yes: `wcag311` | Axe document language rule; fixture has `lang` | Correctness of declared language may differ from actual page language |
| 3.1.2 | Language of Parts | AA | Understandable | Partial | Yes: `wcag312` | Axe language-markup signals where tagged | Identifying language changes in text needs language/content analysis |
| 3.2.1 | On Focus | A | Understandable | Manual | No enabled tag in 4.14.0 | Future keyboard focus interaction review | Unexpected context changes require observing behavior |
| 3.2.2 | On Input | A | Understandable | Manual | No enabled tag in 4.14.0 | Future form-control interaction tests | Context changes and user expectations need operation |
| 3.2.3 | Consistent Navigation | AA | Understandable | Manual | No enabled tag in 4.14.0 | Future comparison across a representative page set | Requires multiple pages and consistent-site context |
| 3.2.4 | Consistent Identification | AA | Understandable | Manual | No enabled tag in 4.14.0 | Future comparison of repeated components across pages | Similar functionality and identification are semantic |
| 3.2.6 | Consistent Help | AA | Understandable | Manual | No enabled tag in 4.14.0 | Future comparison of help mechanisms across pages | Requires page-set coverage and help-function interpretation |
| 3.3.1 | Error Identification | A | Understandable | Partial | No enabled tag in 4.14.0 | Axe form signals; future invalid-submit flow tests | Error detection and textual identification need interaction/context |
| 3.3.2 | Labels or Instructions | A | Understandable | Partial | Yes: `wcag332` | Axe label rules; local labeled/unlabeled control fixture | Instructions may be visually or contextually associated |
| 3.3.3 | Error Suggestion | AA | Understandable | Manual | No enabled tag in 4.14.0 | Future invalid-input and error-message review | Suggestions must be accurate and appropriate to the input |
| 3.3.4 | Error Prevention (Legal, Financial, Data) | AA | Understandable | Manual | No enabled tag in 4.14.0 | Future transaction/commitment workflow testing | Must identify covered actions and test correction/confirmation safeguards |
| 3.3.7 | Redundant Entry | A | Understandable | Manual | No enabled tag in 4.14.0 | Future multi-step form workflow testing | Requires understanding of prior steps and permitted reuse |
| 3.3.8 | Accessible Authentication (Minimum) | AA | Understandable | Manual | No enabled tag in 4.14.0 | Future authentication flow and cognitive-function review | Alternative authentication path/exceptions require human evaluation |
| 4.1.2 | Name, Role, Value | A | Robust | Partial | Yes: `wcag412` | Axe ARIA/name/role/value rules; broken relationship fixture | Dynamic custom widgets and assistive-technology behavior require interaction |
| 4.1.3 | Status Messages | AA | Robust | Partial | No enabled tag in 4.14.0 | Axe live-region signals where tagged; future state-change tests | Whether messages are announced at the right time needs assistive technology |

WCAG 2.2 Success Criterion **4.1.1 Parsing** was removed from WCAG 2.2 and is
not an applicable row in this matrix. AAA criteria are outside this milestone.

## Current automated implementation and tests

The scan runs after the existing navigation, settling, metadata, screenshot, and
other page checks, on the same live Playwright page. It injects the locally
installed, pinned `axe-core` bundle and calls `axe.run` with the five WCAG A/AA
version tags listed above. Best-practice-only and AAA-only rules are not selected.
Returned per-rule tags are authoritative for the result's stated mapping; WebAble
does not maintain a hand-authored axe-rule-to-criterion mapping.

Local browser fixtures assert the behavior of `label`, `button-name`,
`aria-required-parent`, `image-alt`, and `color-contrast`, including passing
semantic markup. The low-contrast fixture is expected in axe's `incomplete`
collection, not promoted to a violation; the passing contrast example remains in
`passes`. An ambiguous image alternative is included to demonstrate that
alternative-text usefulness is not decided by this scan.

## Installation, limits, and next coverage work

Install the JavaScript engine with `npm ci`; install Python dependencies with
`python -m pip install -r requirements.txt` and Chromium with
`python -m playwright install chromium`. The pinned axe-core package is
distributed under its upstream MPL-2.0 license. A missing bundle or execution
error is reported as unavailable, not as zero violations.

The engine only observes the rendered state at scan time. Hidden menus/dialogs,
post-interaction states, keyboard operation and focus order, zoom/reflow,
live-media quality, motion/flashing, the meaning of alternatives, cross-page
consistency, authentication, and assistive-technology announcements remain
untested or require manual review, media analysis, interaction, or assistive
technology. Passing axe checks and empty violations do not establish WCAG
conformance or accessibility.

Future work should first add an explicit, reviewed criterion-to-rule coverage
inventory generated from the pinned axe rule metadata and validated against
W3C Understanding/Techniques and ACT rules. Then add focused keyboard/focus
scenarios with trustworthy state transitions. Browser/media/assistive-
technology checks should remain separately scoped and must not be inferred from
static axe results.
