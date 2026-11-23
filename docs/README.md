# Documentation Index

Progressive-disclosure entry point for human readers and agents discovering skills in this repository. Start here, drill into a bucket or domain group overview, and open individual skill docs only when needed.

For fast CLI discovery without reading Markdown files:

```bash
python3 scripts/install_skills.py list --describe
```

## Sections

- [Repository Architecture & Improvement Loop](architecture.md): Lifecycle from `skills/in-progress/` through blinded A/B evaluation to promotion.
- [Meta Skills](meta/README.md): Skills that author, verify, refine, and A/B test skills inside this repository.
- [Custom Skills](custom/README.md): Promoted domain skill groups (such as `kb-skills`) and standalone custom skills for target workspaces.
- [External Skills](external/README.md): Curated third-party skills vendored from upstream Git repos via `scripts/external_skills.py` and pinned in `skills/external/manifest.json`.
