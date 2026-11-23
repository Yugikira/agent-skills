---
name: verify-skills
description: Run static linting, link checks, invocation parity, blinding-leak checks, and live harness smoke tests for this skills repo. Use for /verify-skills or before committing any skill edit.
disable-model-invocation: true
---

# Verify Skills

Prove that every skill, doc, script, and eval suite in this repository is structurally valid and executable. Never declare done on a static read alone.

## Outcomes

End every run by stating exactly one verdict:
- `clean`: all static checks and live smoke checks passed with no drift.
- `changed`: proven fixes applied within verification scope and re-verified green.
- `blocked`: a check failed due to an external dependency or unresolvable defect; name the exact blocker.

## Launch & Doctor

Run the repository verifier from the repo root:

```bash
python3 scripts/verify_repo.py
```

`verify_repo.py` checks:
1. Valid YAML frontmatter (`name` matches directory, non-empty `description`).
2. Dual-harness invocation parity (`disable-model-invocation: true` matches `agents/openai.yaml`).
3. Line-count budget (warns above 250 lines, fails above 300 lines).
4. Zero em-dashes in skill and repo prose.
5. Every relative markdown link resolves to an existing file.
6. Promoted skills (`meta/`, `custom/`) are synced across top-level `README.md`, bucket `README.md`, `docs/<bucket>/<name>.md` (with all 4 required headings), and `skills/meta/skill-mode/SKILL.md`.
7. Eval suites under `evals/suites/*.json` contain zero blinding-leak terms in organic prompts.

## Live Drive

Whenever `scripts/ab_harness.py`, `scripts/new_skill.py`, or `scripts/install_skills.py` changes, exercise them live in an isolated temp directory:

```bash
python3 scripts/new_skill.py smoke-check --mode user --goal "Smoke test" --dry-run
python3 scripts/ab_harness.py self-test
python3 scripts/install_skills.py self-test
```

## Evidence & Cleanup

- Record the exact command and exit code in your reply.
- Clean up any temporary workspaces created during live drives, and confirm permanent logs (`evals/results/eval-log.tsv`) are untouched unless intentionally updated.
- Never weaken a check or skip a failing assertion to turn a red run green.
