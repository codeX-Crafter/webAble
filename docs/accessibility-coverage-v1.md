# WCAG coverage matrix v1 — superseded

This historical matrix has been superseded by the generated
[WCAG 2.2 Level A/AA coverage inventory](./wcag-22-coverage-inventory.md)
and its machine-readable [JSON inventory](./wcag-22-coverage-inventory.json).
Use those files as the current source for criterion titles, levels, axe rule
associations, package-enabled state, scanner selection, classifications, and
limitations.

The original v1 inventory used a simplified yes/no mapping and did not clearly
distinguish rules tagged for a criterion from rules that were both enabled by
axe-core and selected by WebAble's configured runOnly tags. It also risked
suggesting broader criterion coverage than an axe tag establishes. The current
inventory derives metadata from the installed pinned axe-core package and
labels every mapped criterion `partial`; it makes no conformance claim.
