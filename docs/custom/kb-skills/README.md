# Knowledge Base Skills (`kb-skills`)

Domain suite for building, querying, auditing, and consolidating an academic Markdown Knowledge Base (`wiki/` + `source/summary/`).

## Install

Install the full suite into a target workspace (flattened into `<project-dir>/.agents/skills/<skill-name>/`):

```bash
python3 scripts/install_skills.py install --group kb-skills --workspace /path/to/project
```

For an external research repo that only needs read-only literature lookup, install `kb-query` standalone:

```bash
python3 scripts/install_skills.py install --skills kb-query --workspace /path/to/project
```

## Typical Workflow

1. **Ingest**: `/kb-ingest` adds new papers and cross-linked wiki pages.
2. **Query**: `kb-query` (model-invoked) answers literature, concept, and variable questions from any workspace.
3. **Audit**: `/kb-lint` detects broken links, true orphan pages, stale summaries, and conflicting variable interpretations.
4. **Consolidate**: `/kb-consolidate` merges duplicate proxies, relocates misplaced entries, and filters large tables (typically every 10+ papers).

## Skills

### User-invoked

- [kb-ingest](kb-ingest.md) ([SKILL.md](../../../skills/custom/kb-skills/kb-ingest/SKILL.md)): Ingests academic papers by DOI, title, citekey, or local PDF into `source/summary/` and `wiki/` with methodology templates and collision checks.
- [kb-lint](kb-lint.md) ([SKILL.md](../../../skills/custom/kb-skills/kb-lint/SKILL.md)): Audits the Knowledge Base for broken Markdown/legacy links, true incoming-link orphan pages, stale summaries, and conflicting variable interpretations.
- [kb-consolidate](kb-consolidate.md) ([SKILL.md](../../../skills/custom/kb-skills/kb-consolidate/SKILL.md)): Audits and consolidates wiki concepts, constructs, and variables by merging duplicate operationalizations, moving misplaced entries, and applying top-journal caps.

### Model-invoked

- [kb-query](kb-query.md) ([SKILL.md](../../../skills/custom/kb-skills/kb-query/SKILL.md)): Standalone, directory-agnostic Knowledge Base search and literature synthesis skill using `rg`-first discovery, `.kb_root` persistence, and 1-hop link expansion.
