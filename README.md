# Agent Skills Forge

A self-verifying repository for authoring, maintaining, refining, and blinded A/B testing agent skills across Claude Code, Cursor, and Codex.

The architecture synthesizes patterns from [mattpocock/skills](https://github.com/mattpocock/skills) (bucketed layout, `writing-for-agents` levers, dual-harness invocation metadata, symlink installation) and poteto's [cursor/plugins/pstack](https://github.com/cursor/plugins/blob/main/pstack/README.md) (sticky mode router, executable verification skills, blinded A/B evaluation, hillclimb refinement, and TSV decision trails).

## Quickstart

1. **Validate the repository**:
   ```bash
   python3 scripts/verify_repo.py
   ```
2. **Link promoted skills into your local agent harnesses** (`~/.claude/skills`, `~/.cursor/skills`, `~/.agents/skills`):
   ```bash
   bash scripts/link-skills.sh
   ```
3. **Scaffold a new skill in `skills/in-progress/`**:
   ```bash
   python3 scripts/new_skill.py my-skill --mode user --goal "Short statement of the user goal this skill improves"
   ```
4. **Run the improvement loop**:
   - Use `/skill-mode` as the entry point for creating, verifying, refining, or A/B testing any skill.
   - Run `scripts/ab_harness.py` to stage blinded A/B workspaces and score judge results into `evals/results/eval-log.tsv`.

## Promoted Skills

### User-invoked

- [skill-mode](skills/meta/skill-mode/SKILL.md): Sticky router that matches any skill-repo task to a playbook (`authoring-a-skill`, `verify-skill`, `refine-skill`, `ab-eval`) and applies core principles.
- [verify-skills](skills/meta/verify-skills/SKILL.md): Runs static linting, link checks, invocation parity, and live end-to-end harness verification with preserved evidence.
- [refine-skill](skills/meta/refine-skill/SKILL.md): Runs a disciplined hillclimb and no-op pruning loop so every edit targets one root cause and proves improvement.
- [ab-eval-skill](skills/meta/ab-eval-skill/SKILL.md): Designs and runs blinded A/B evaluations across variants using organic prompts, hidden rubrics, and transcript audits.

### Model-invoked

- [writing-for-agents](skills/meta/writing-for-agents/SKILL.md): Reference for authoring and pruning any agent-facing file (`SKILL.md`, `AGENTS.md`, specs, prompts) using context pointers, progressive disclosure, leading words, and the no-op test.

## Architecture & Workflow

See [docs/architecture.md](docs/architecture.md) for the full lifecycle from `skills/in-progress/` through blinded A/B evaluation to promotion.
