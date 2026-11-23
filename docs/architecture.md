# Repository Architecture & Improvement Loop

This repository treats agent skills like production software: every edit is scoped, structurally verified, and empirically tested against your goal before promotion.

## Design Lineage

- **From [mattpocock/skills](https://github.com/mattpocock/skills)**:
  - Bucketed lifecycle (`meta/`, `custom/`, `in-progress/`, `deprecated/`) defined in [CLAUDE.md](https://github.com/mattpocock/skills/blob/main/CLAUDE.md).
  - Context-load vs. cognitive-load discipline, five authoring levers, and the sentence-level no-op test from [writing-for-agents.md](https://github.com/mattpocock/skills/blob/main/docs/productivity/writing-for-agents.md).
  - Dual invocation metadata (`disable-model-invocation: true` in `SKILL.md` paired with `policy.allow_implicit_invocation: false` in `agents/openai.yaml`) and symlink installation via `scripts/link-skills.sh`.
  - Mirrored human documentation in `docs/<bucket>/<skill-name>.md`.
- **From poteto's [cursor/plugins/pstack](https://github.com/cursor/plugins/blob/main/pstack/README.md)**:
  - Sticky mode router (`skill-mode`) with playbooks and inline principles (`laziness-protocol`, `encode-lessons-in-structure`, `prove-it-works`, `explain-the-number`).
  - Delete-first skill authoring from [authoring-a-skill.md](https://github.com/cursor/plugins/blob/main/pstack/skills/poteto-mode/playbooks/authoring-a-skill.md).
  - Executable verification skills (`Launch`, `Doctor`, `Drive`, `Evidence`, `Cleanup`) from [create-verification-skill](https://github.com/cursor/plugins/blob/main/pstack/skills/create-verification-skill/SKILL.md) and upkeep triage (`clean` / `changed` / `blocked`) from [maintain-verification-skill](https://github.com/cursor/plugins/blob/main/pstack/skills/maintain-verification-skill/SKILL.md).
  - Strict blinding rules and transcript-based chain verification from [eval.md](https://github.com/cursor/plugins/blob/main/pstack/skills/poteto-mode/playbooks/eval.md), plus multi-run repeatability checks from [benchmark-checklist](https://github.com/cursor/plugins/blob/main/pstack/skills/benchmark-checklist/SKILL.md).

## The Four-Stage Skill Lifecycle

1. **Author (`skills/in-progress/`)**: Scaffold with `scripts/new_skill.py`, write the minimal execution spine with `writing-for-agents`, and keep reference material in `references/`.
2. **Verify (`scripts/verify_repo.py` + `verify-skills`)**: Enforce YAML frontmatter, invocation parity, resolved links, line budget, zero em-dashes, docs/index sync, and zero blinding-leak terms in eval suites.
3. **A/B Test (`scripts/ab_harness.py` + `ab-eval-skill`)**: Stage sanitized neutral workspaces for baseline (A) and candidate (B), run identical organic prompts in fresh context windows, judge both outputs blind in a single pass on a hidden 3-6 criterion rubric, audit transcripts, and log the verdict to `evals/results/eval-log.tsv`.
4. **Refine & Promote (`refine-skill`)**: Keep only edits that beat baseline on your goal without regressions, revert or prune no-ops, move the skill from `skills/in-progress/` to `skills/custom/`, update docs and router, and run `scripts/link-skills.sh`.
