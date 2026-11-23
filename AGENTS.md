# Agent Skills Repository Rules

This repository stores, verifies, refines, and A/B tests agent skills. `AGENTS.md` is the canonical rule file; `CLAUDE.md` points here.

## Directory Layout & Buckets

Skills live under `skills/` in four buckets:

- `skills/meta/`: promoted meta-skills that create, verify, refine, and A/B test skills.
- `skills/custom/`: your promoted domain skills.
- `skills/in-progress/`: beta skills under development or A/B evaluation. Not linked or shipped until promoted.
- `skills/deprecated/`: retired skills kept for reference. Not linked or shipped.

Every skill in a promoted bucket (`meta/`, `custom/`) must have:

1. An entry in the top-level `README.md` linking the skill name to its `SKILL.md`.
2. An entry in its bucket's `README.md` grouped under `User-invoked` or `Model-invoked`.
3. A human-facing docs page at `docs/<bucket>/<skill-name>.md` with four sections: `What it does`, `When to reach for it`, `Common questions`, and `It's working if`.
4. An entry in `skills/meta/skill-mode/SKILL.md` so the router stays accurate.

Skills in `in-progress/` and `deprecated/` must not appear in the top-level `README.md` or `docs/`.

## Invocation Parity

Every `SKILL.md` is either:

- **User-invoked**: sets `disable-model-invocation: true` in YAML frontmatter AND `policy.allow_implicit_invocation: false` in `agents/openai.yaml`.
- **Model-invoked**: omits `disable-model-invocation` (or sets it to `false`).

## Writing & Editing Rules

- Load `skills/meta/writing-for-agents/SKILL.md` before creating or editing any `SKILL.md`, `AGENTS.md`, or prompt file.
- Default fix is deletion, not explanation. Keep every `SKILL.md` under 250 lines (hard cap: 300 lines) and push heavy schemas, checklists, or rubrics into `references/`.
- No em-dashes in repo prose (`SKILL.md`, `AGENTS.md`, `README.md`, `docs/`). Use a comma, colon, period, or parentheses instead.
- Never state a rule twice. Encode repeatable checks in `scripts/verify_repo.py` rather than adding more prose.
- Every skill that dispatches a subagent must instruct it to start with a fresh context window (never fork the parent conversation).
- Preserve generator-owned marker blocks (`<!-- ...:start -->` to `<!-- ...:end -->`) byte-for-byte when pruning files.

## Verification & Promotion Gate

Run `python3 scripts/verify_repo.py` after any edit to skills, docs, or eval suites. A change is not done until `verify_repo.py` exits 0.

Before promoting a skill from `skills/in-progress/` or merging a behavioral edit to a promoted skill, run a blinded A/B evaluation with `skills/meta/ab-eval-skill/SKILL.md` and `scripts/ab_harness.py`, and record the verdict in `evals/results/eval-log.tsv`.

## Local Linking

Run `bash scripts/link-skills.sh` after adding, removing, renaming, or promoting a skill to refresh symlinks in `~/.claude/skills`, `~/.cursor/skills`, and `~/.agents/skills`.
