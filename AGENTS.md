# Agent Skills Repository Rules

This repository stores, verifies, refines, and A/B tests agent skills. `AGENTS.md` is the canonical rule file; `CLAUDE.md` points here.

## Directory Layout & Buckets

Skills live under `skills/` in five buckets:

- `skills/meta/`: promoted meta-skills that create, verify, refine, and A/B test skills.
- `skills/custom/`: promoted domain skills. Related skills may be grouped 1 level deep (`skills/custom/<group>/<skill-name>/`); standalone skills live directly at `skills/custom/<skill-name>/`.
- `skills/external/`: curated third-party skills vendored from upstream Git repositories via `scripts/external_skills.py` and pinned in `skills/external/manifest.json`. Supports optional 1-level grouping (`skills/external/<group>/<skill-name>/`) sharing logical `--group` names with `skills/custom/`, auto-synced to `docs/external/README.md`. Checked for frontmatter, global name uniqueness, and manifest sync; exempt from local prose style caps.
- `skills/in-progress/`: beta skills under development or A/B evaluation. Not linked or shipped until promoted.
- `skills/deprecated/`: retired skills kept for reference. Not linked or shipped.

Skill names must be globally unique across all five buckets and groups.

Progressive-disclosure docs live under `docs/` (`docs/README.md` -> `docs/<bucket>/README.md` -> `docs/custom/<group>/README.md` -> per-skill doc). Every promoted skill (`meta/`, `custom/`) must satisfy:

1. **Standalone promoted skills** (`meta/<name>`, `custom/<name>`): linked in top-level `README.md`, `skills/<bucket>/README.md`, and `docs/<bucket>/README.md`, with a docs page at `docs/<bucket>/<skill-name>.md`.
2. **Grouped custom skills** (`custom/<group>/<name>`): group overview at `docs/custom/<group>/README.md` (single source of truth; no duplicate `skills/custom/<group>/README.md`) linked from top-level `README.md`, `skills/custom/README.md`, and `docs/custom/README.md`; each skill linked in `docs/custom/<group>/README.md` with its docs page at `docs/custom/<group>/<skill-name>.md`.
3. Every promoted skill docs page has four sections: `What it does`, `When to reach for it`, `Common questions`, and `It's working if`.
4. For `skills/meta/` skills, an entry in `skills/meta/skill-mode/SKILL.md` so the meta-skill router stays accurate.

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

Run `python3 scripts/verify_repo.py` after any edit to skills, docs, or eval suites (on Windows where `python3` is not mapped, use `python`). A change is not done until `verify_repo.py` exits 0.

Before promoting a skill from `skills/in-progress/` or merging a behavioral edit to a promoted skill, run a blinded A/B evaluation with `skills/meta/ab-eval-skill/SKILL.md` and `scripts/ab_harness.py`, and record the verdict in `evals/results/eval-log.tsv`.

## Skill Deployment (Opt-In)

Do not automatically link or copy skills into global directories after edits or promotions.

- Inside this repo, mount `skills/meta/` locally (gitignored `.agents/skills/`) with `python3 scripts/install_skills.py mount-local`.
- Deploy skills on demand (by `--skills`, `--group`, or `--bucket`) to a target project workspace (defaults to copy) or explicitly to `--global` (opt-in) with `python3 scripts/install_skills.py install`. Grouped skills are always flattened to `<target>/<skill-name>/` on install. `--bucket promoted` installs `meta/` and `custom/` only; external skills deploy via `--group`, `--skills`, or `--bucket external` (combine `--bucket custom --group <g>` or `--bucket external --group <g>` to scope a group to one bucket).
- Skills in `skills/in-progress/` are blocked by default and can only be installed into a workspace with `--allow-in-progress` (never globally).
