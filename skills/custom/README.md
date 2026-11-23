# Custom Skills

Promoted domain skills live here after passing `scripts/verify_repo.py` and verification against real examples or blinded A/B evaluation.

## User-invoked

- [kb-ingest](kb-ingest/SKILL.md): Ingest academic papers by DOI, title, citekey, or local PDF into a Markdown Knowledge Base using `libby`, `paddle-pdf`, methodology templates, and collision checks.
- [kb-lint](kb-lint/SKILL.md): Health check for a Knowledge Base finding broken Markdown/legacy links, true incoming-link orphan pages, stale summaries, and conflicting variable interpretations.
- [kb-consolidate](kb-consolidate/SKILL.md): Audit and consolidate wiki concepts, constructs, and variables by merging duplicate operationalizations, moving misplaced items, and enforcing top-journal filtering.

## Model-invoked

- [kb-query](kb-query/SKILL.md): Standalone, directory-agnostic Knowledge Base search and literature synthesis skill using `rg`-first discovery, `.kb_root` persistence, and 1-hop graph expansion.
