## What it does

`kb-lint` performs a 5-check health audit on an academic Knowledge Base: broken Markdown/legacy file links (`scripts/kb_lint.py`), true incoming-link orphan wiki pages (zero dependency on `_index.md`), missing targets referenced from paper summaries, stale summaries older than 6 months (`processed:`), and conflicting theoretical interpretations across `wiki/variables/*.md`.

## When to reach for it

Invoke it explicitly with `/kb-lint` (or `/kb-lint --quick` / `/kb-lint --contradictions`) after batch ingestions, after running `/kb-consolidate`, or during periodic KB maintenance. The agent will not invoke it automatically.

## Common questions

**How are orphan pages detected without `_index.md` files?**
`kb_lint.py` builds a full incoming-link graph across `wiki/`, `source/summary/`, and `source/conversations/` (supporting both standard Markdown links and legacy `[[wikilinks]]`) and flags any wiki page with zero incoming links from other files.

**Does `kb-lint` modify or delete files automatically?**
No. It reports exact file paths, line numbers, root causes, and recommended fixes so you can review or apply repairs safely.

## It's working if

- Broken links (including category mismatches like `constructs/` vs. `concepts/`) and unlinked method or variable pages are caught with exact line numbers.
- Conflicting theoretical interpretations of the same operational proxy across papers are surfaced cleanly instead of silently coexisting.
- Re-running `kb_lint.py` after fixes exits 0 with zero broken links and zero orphan pages.
