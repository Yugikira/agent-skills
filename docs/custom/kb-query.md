## What it does

`kb-query` is a standalone, directory-agnostic skill that searches an external or local academic Knowledge Base (`wiki/` and `source/summary/`) using `rg` first (via `scripts/kb_search.py` or CLI fallback) and synthesizes grounded literature answers with clickable standard Markdown file links. It supports persistent KB path resolution (`.kb_root`, `$KB_ROOT`, or `--kb-dir`), `--papers` summary comparisons, and `--deep` 1-hop link expansion.

## When to reach for it

`kb-query` is model-invoked, so an agent in any research project workspace can trigger it automatically whenever you ask a literature, concept, variable operationalization, or citation question against your Knowledge Base. You can also invoke it explicitly via `/kb-query "<question>" --kb-dir <path>`.

## Common questions

**Can I deploy `kb-query` alone into another research project?**
Yes. Run `python scripts/install_skills.py install --skills kb-query --workspace <project-dir>` (use `python3` on Unix). Pass your KB path once and `kb_search.py --save-kb-dir` remembers it in `.kb_root`.

**Does it still work on older KBs that use `[[wikilinks]]`?**
Yes. `kb_search.py --deep` parses both standard relative Markdown links and legacy `[[wikilinks]]`, while synthesized responses emit standard Markdown file links.

## It's working if

- The agent resolves and persists `.kb_root` cleanly and executes `kb_search.py` without script crashes on Windows or Unix.
- Every coefficient, formula, and theorem cited matches the files in your Knowledge Base, with explicit gap reporting when a topic or paper is missing.
- Both canonical wiki variable names and exact paper variable names are preserved alongside clickable Markdown links.
