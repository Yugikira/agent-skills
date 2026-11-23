---
name: writing-for-agents
description: Reference for writing and pruning any document an agent consumes (SKILL.md, AGENTS.md, CLAUDE.md, specs, rule files, issue bodies, or dispatch briefs). Use when creating or editing skills, modifying AGENTS.md, or tightening agent instructions.
---

# Writing for Agents

Write for a reader that already knows general engineering. Explanation is context cost; precision is the job. When editing a skill, also read [references/SKILL-MECHANICS.md](references/SKILL-MECHANICS.md).

## The Two Loads

- **Context load**: Always-loaded tokens (`AGENTS.md`, skill descriptions) paid on every turn whether or not they fire. Keep these minimal.
- **Cognitive load**: Your mental index of which skills exist and when to invoke them. Do not dump everything into always-loaded files just to avoid remembering a slash command.

## Five Levers

1. **Context pointers**: A skill `description` or `AGENTS.md` pointer does two jobs: name what the material is, and list the exact branches that trigger reading it. Pointer wording determines trigger reliability.
2. **Information hierarchy (progressive disclosure)**: Keep the execution spine in `SKILL.md` (under 250 lines, hard cap 300). Move rubrics, schemas, long examples, and checklists into `references/` behind clear pointers.
3. **Completion criteria**: Give every step a concrete, falsifiable done-condition (command exit code, file diff, observed output) to prevent premature completion.
4. **Leading words**: Use compact pretraining concepts (`red-green`, `tracer bullet`, `no-op test`, `delete-first`, `root cause`) that steer behavior in a few tokens.
5. **Pruning and the no-op test**: Inspect sentence by sentence. Ask: "If I delete this sentence, does the agent's behavior change?" If not, delete the entire sentence.

## Editing Rules

- **Single source of truth**: Never state a rule in two places. Link by path instead of restating.
- **Encode lessons in structure**: If a rule is checkable by script or lint, add it to `scripts/verify_repo.py` instead of writing a warning paragraph.
- **Preserve generator markers**: Before rewriting an existing instruction file, locate `<!-- ...:start -->` / `<!-- ...:end -->` blocks and preserve them byte-for-byte.
- **Generalize from evidence**: When turning a past session into a skill, strip repo-specific filenames and one-off glitches; write for the class of task.
- **Fresh subagent contexts**: Any instruction that spawns a subagent must require a fresh context window.

## Done When

- Every sentence passes the no-op test.
- No rule is duplicated across `AGENTS.md`, `SKILL.md`, and `references/`.
- `python3 scripts/verify_repo.py` passes with exit code 0.
