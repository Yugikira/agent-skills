# Skill Mechanics Reference

Load this file only when authoring or updating a `SKILL.md` package.

## Frontmatter Schema

```yaml
---
name: my-skill-name
description: One-to-two sentence pointer stating what the skill does and exact trigger branches.
disable-model-invocation: true # Include only for user-invoked skills
---
```

Rules enforced by `scripts/verify_repo.py`:
- `name` must be lowercase kebab-case and match the parent directory name exactly.
- `description` must be non-empty, concise (under 300 characters), and list every trigger branch the body handles.
- Never include em-dashes in frontmatter or body prose.

## User-Invoked vs. Model-Invoked

- **User-invoked** (destructive, stateful, high-cost, or explicit workflow entry points):
  - Set `disable-model-invocation: true` in `SKILL.md`.
  - Create `agents/openai.yaml` containing:
    ```yaml
    policy:
      allow_implicit_invocation: false
    ```
- **Model-invoked** (reference guides or safe automatic checks):
  - Omit `disable-model-invocation` (or set `false`).
  - Omit `agents/openai.yaml` or set `allow_implicit_invocation: true`.

## Directive Budget

- Treat `SKILL.md` as an executive controller, not an encyclopedia.
- Target under 25 distinct procedural rules and under 250 lines (hard cap: 300 lines).
- Crossing ~40 rules causes directive degradation where models drop basic constraints at random. Split reference material into `references/<TOPIC>.md`.

## Router Skills

When adding, renaming, promoting, or removing a user-reachable skill:
1. For `skills/meta/` skills, update `skills/meta/skill-mode/SKILL.md` so the router map never lies.
2. Update `README.md`, the bucket `README.md`, and `docs/<bucket>/<name>.md` for promoted skills.
3. If updating `skills/meta/`, run `python3 scripts/install_skills.py mount-local` to refresh this repo's local `.agents/skills/` mount. Deploy `skills/custom/` skills on demand via `scripts/install_skills.py install`.
