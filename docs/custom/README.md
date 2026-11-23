# Custom Skills Documentation

Promoted domain skills for deployment into target project workspaces via `scripts/install_skills.py`. Related domain skills are organized into 1-level groups; standalone cross-cutting skills live directly under `docs/custom/`.

## Domain Groups

- [kb-skills](kb-skills/README.md): Academic Markdown Knowledge Base suite (`kb-ingest`, `kb-query`, `kb-lint`, `kb-consolidate`) for ingesting papers, querying literature, auditing links/orphans, and consolidating wiki pages. Install all: `python3 scripts/install_skills.py install --group kb-skills --workspace <project-dir>`.

## Standalone Skills

None yet. Standalone skills that do not belong to a multi-skill domain group are listed here.
