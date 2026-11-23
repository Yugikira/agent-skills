---
name: skill-mode
description: Sticky router for creating, updating, verifying, refining, and A/B testing agent skills in this repository. Use for /skill-mode or any non-trivial skill authoring, audit, or evaluation task.
disable-model-invocation: true
---

# Skill Mode

Route every non-trivial skill task through one explicit playbook, enforce the principles below, and never declare done without verification evidence.

## Core Principles

- **Laziness Protocol**: Bias toward deletion and the smallest edit that solves the root cause.
- **Encode Lessons in Structure**: When you write the same rule twice, move it into `scripts/verify_repo.py` or frontmatter instead of adding prose.
- **Prove It Works**: Verify against the real artifact (script exit code, live run, or transcript), never self-report.
- **Explain the Number**: Before trusting an A/B eval result, check whether every run did the task, whether the win holds across trials, and whether the scenario matches the real goal.
- **Fresh Context Windows**: Every dispatched subagent starts with a fresh context window, never a fork of the parent chat.

## Playbooks

Match the user's request to one playbook, read it in full, and execute its steps in order:

- **Create or update a skill**: [playbooks/authoring-a-skill.md](playbooks/authoring-a-skill.md)
- **Verify repo or skills**: [playbooks/verify-skill.md](playbooks/verify-skill.md)
- **Refine an underperforming skill**: [playbooks/refine-skill.md](playbooks/refine-skill.md)
- **A/B test a skill modification**: [playbooks/ab-eval.md](playbooks/ab-eval.md)

## Skill Map

- [writing-for-agents](../writing-for-agents/SKILL.md): Authoring and pruning reference for any agent-facing file.
- [verify-skills](../verify-skills/SKILL.md): Structural linter and live verification harness.
- [refine-skill](../refine-skill/SKILL.md): Single-hypothesis hillclimb and no-op pruning loop.
- [ab-eval-skill](../ab-eval-skill/SKILL.md): Blinded A/B testing, judge scoring, and arena grafting.

## Finish Condition

Every task ends with:
1. `python3 scripts/verify_repo.py` passing with exit code 0.
2. Concrete evidence (command output, diff summary, or `evals/results/eval-log.tsv` row) proving the goal improved or held.
