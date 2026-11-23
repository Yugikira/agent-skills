## What it does

`writing-for-agents` is the core authoring reference for any document an agent reads: `SKILL.md`, `AGENTS.md`, `CLAUDE.md`, specs, and dispatch briefs. It centers on two budgets (context load and cognitive load), five levers (context pointers, progressive disclosure, completion criteria, leading words, and pruning), and the sentence-level no-op test.

## When to reach for it

Type `/writing-for-agents`, or the agent reaches for it automatically when creating or editing skills or `AGENTS.md`. Reach for it before adding new rules to prevent instruction bloat and directive degradation.

## Common questions

**Why does it emphasize deleting instead of explaining?**
Frontier models already know general software practices. Explaining why a rule exists costs context tokens on every turn without changing behavior. Delete any sentence whose removal does not change agent output.

**Where do frontmatter and cross-harness details live?**
In `skills/meta/writing-for-agents/references/SKILL-MECHANICS.md`, loaded only when the file being edited is a skill.

## It's working if

- Skills get shorter as they get more reliable.
- Nothing is stated in two places; heavy schemas and checklists live in `references/`.
- Every skill stays well under the 300-line budget enforced by `scripts/verify_repo.py`.
