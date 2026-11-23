## What it does

`kb-ingest` ingests academic papers (across economics, finance, accounting, management science, and marketing) into a structured Markdown Knowledge Base. It acquires metadata and PDFs via `libby`, converts PDFs via `paddle-pdf`, classifies paper methodology (`archival`, `experimental`, `survey`, `analytical`, `review`), writes a paired Claimed vs. Ground Truth summary in `source/summary/`, links related papers, checks semantic collisions against existing wiki pages, creates or updates cross-linked Markdown wiki pages, and appends to `wiki/log.md`.

## When to reach for it

Invoke it explicitly with `/kb-ingest <doi|title|citekey|pdf>` (or `/kb-ingest --batch` for multiple papers). The agent will not invoke it automatically because it runs external CLI tools and creates files in your Knowledge Base.

## Common questions

**Does it use Obsidian wikilinks or standard Markdown links?**
Standard relative Markdown file links (`[Concept](../../wiki/concepts/Concept.md)` in body text and plain KB-root-relative paths in YAML frontmatter), while its helper scripts (`check_collision.py`, `check_related_papers.py`) remain backward-compatible with legacy `[[wikilinks]]`.

**How does single-paper vs. batch mode work?**
Single-paper ingestion runs inline in the main agent to avoid duplicate context reads. Batch mode runs `libby` and `paddle-pdf` upfront in the orchestrator and dispatches one fresh-context subagent per paper.

## It's working if

- Every Ground Truth Finding corresponds 1-to-1 to a Claimed Finding with exact paper variable names, formulas, coefficients, and sample sizes (or formal theorem statements for analytical papers).
- Routine control variables and derived composites are marked `[no wiki]` rather than cluttering `wiki/variables/`.
- Running `kb_lint.py` afterward reports zero newly broken links and zero orphan pages for the ingested paper.
