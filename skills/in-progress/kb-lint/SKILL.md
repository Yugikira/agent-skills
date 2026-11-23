---
name: kb-lint
description: Health check for the Knowledge Base wiki and paper summaries. Runs kb_lint.py and rg-first checks to find broken [[wikilinks]], true incoming-link orphan pages, stale summaries, and conflicting variable interpretations. Use for /kb-lint.
disable-model-invocation: true
---

# kb-lint - Knowledge Base Health Check

Run deterministic and semantic health checks on the Knowledge Base (`wiki/` and `source/summary/`). Supports `--kb-dir <path>` or `.kb_root` when invoked from an external workspace.

## Usage Patterns

- `/kb-lint` - Full health check (all 5 checks)
- `/kb-lint --quick` - Quick check (`kb_lint.py` for broken wikilinks and true orphan pages only)
- `/kb-lint --contradictions` - Focus on conflicting variable interpretations across papers

## Check 1 & Check 2: Broken Wikilinks & True Orphan Wiki Pages

Run the unified linter script (no `_index.md` files required; an orphan is defined as a wiki page in `wiki/{category}/*.md` with **zero incoming `[[wikilinks]]`** from any summary or other wiki page). Omit `--kb-dir` when inside the KB root (on Windows, use `python` if `python3` is unmapped):

```bash
python3 "<skill_dir>/scripts/kb_lint.py" --kb-dir "<kb_root>"
```

**Fix approach**:
- **Broken wikilinks**: Create the missing target wiki page if warranted, fix typos/category paths, or replace with `[no wiki]` if the variable/method was intentionally skipped.
- **True orphan pages**: Link the page from the appropriate paper summary (`source/summary/{citekey}_summary.md`) or parent concept page (`wiki/concepts/{concept}.md`), or merge/delete if redundant.

## Check 3: Missing Concept/Variable Pages Referenced in Summaries (`rg`-First)

Find any `[[concepts/...]]`, `[[variables/...]]`, `[[constructs/...]]`, `[[methods/...]]`, or `[[theories/...]]` links in `source/summary/*.md` whose target file does not yet exist:

```bash
rg -o "\[\[(concepts|variables|constructs|methods|theories)/[^\]]+\]\]" "<kb_root>/source/summary"
```
(This is also automatically reported under `Broken Wikilinks` by `kb_lint.py`.)

## Check 4: Stale Claims (`rg`-First)

Inspect `processed: YYYY-MM-DD` in `source/summary/*.md` frontmatter to flag summaries older than 6 months that may need consolidation:

```bash
rg -n "^processed:" "<kb_root>/source/summary"
```

## Check 5: Conflicting Variable Interpretations (`--contradictions`)

Scan `## Interpretations` across `wiki/variables/*.md` using `rg`:

```bash
rg -n -A 10 "^## Interpretations" "<kb_root>/wiki/variables"
```
Flag any variable where different papers assign contradictory theoretical meanings to the same operational formula.
