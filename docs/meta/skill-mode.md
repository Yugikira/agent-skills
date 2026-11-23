## What it does

`skill-mode` is the sticky entry-point router for this repository. Give it a goal (creating a skill, verifying the repo, refining an underperforming skill, or running a blinded A/B test) and it loads the matching playbook, enforces core principles, and requires verification evidence before finishing.

## When to reach for it

You invoke this by typing `/skill-mode`, and the agent will not reach for it on its own. Reach for it at the start of any non-trivial skill authoring, cleanup, or evaluation task. For a quick single-file prose check without a full playbook, reach for `writing-for-agents` directly.

## Common questions

**Why route through a mode skill instead of calling scripts directly?**
Running scripts by hand checks syntax, not rigor. `skill-mode` sequences authoring, static verification, blinded A/B testing, and logging so modifications cannot bypass the evidence gate.

**When should I update `skill-mode`?**
Whenever you add, rename, promote, or remove a user-reachable skill so the router map stays accurate.

## It's working if

- Every skill task starts by naming the matched playbook and ends with a passing `verify_repo.py` run.
- Subagents are always dispatched with fresh context windows instead of inheriting noisy parent chats.
- You rarely have to remind the agent to verify or A/B test before declaring a skill change done.
