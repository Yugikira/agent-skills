## What it does

`kb-consolidate` audits `wiki/concepts/`, `wiki/constructs/`, and `wiki/variables/` to keep a growing Knowledge Base clean. Using its reference rules (`references/consolidation-rules.md`), it flags duplicate or algebraically equivalent variables (Canonical + Cross-Link merges), non-proxy variables, duplicate consequences split by qualifiers, misplaced moderators, behavioral responses, or validity tests, unfiltered tables exceeding 5 entries (oldest + newest top-journal filter), and high-similarity concept pairs for manual review.

## When to reach for it

Invoke it explicitly with `/kb-consolidate` (or scoped with `--concepts`, `--constructs`, `--variables`, or a specific page name) after ingesting batches of papers (typically every 10+ papers) or when wiki tables become cluttered. The agent will not invoke it automatically.

## Common questions

**Will `/kb-consolidate` overwrite my wiki pages without asking?**
No. Phase 4 outputs a structured Consolidation Audit Report and pauses for explicit user approval (`Apply these fixes? (Y/n)`) before modifying any wiki page. High-similarity concept pairs (>70%) are never auto-merged.

**How are alternative variable formulas preserved when merging?**
The canonical variable page retains combined sources, alternative operationalizations become short cross-link pages pointing to the canonical `.md` file, and the parent concept table notes each variant formula type.

## It's working if

- Misclassified variables (such as control covariates or validation outcomes listed as direct proxies) and misplaced moderators/validity tests are caught cleanly.
- No wiki files are modified prior to user approval.
- After approved edits, all relative Markdown file links remain valid under `kb_lint.py`.
