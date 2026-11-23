# External Skills Documentation

Curated third-party skills vendored from upstream Git repositories via `scripts/external_skills.py` and pinned in `skills/external/manifest.json`. External skills can share a logical `--group` name with `skills/custom/` for unified workspace deployment.

```bash
python3 scripts/install_skills.py install --bucket external --workspace /path/to/project
python3 scripts/install_skills.py install --group <group> --workspace /path/to/project
python3 scripts/external_skills.py check
```

<!-- external-skills:start -->
## Domain Groups

### productivity

- [grill-me](../../skills/external/productivity/grill-me/SKILL.md) ([upstream](https://github.com/mattpocock/skills/tree/abeeaf95660ba9e8b7c753eb38f441ca707a8823/skills/productivity/grill-me), `abeeaf9566`): A relentless interview to sharpen a plan or design.
- [grilling](../../skills/external/productivity/grilling/SKILL.md) ([upstream](https://github.com/mattpocock/skills/tree/abeeaf95660ba9e8b7c753eb38f441ca707a8823/skills/productivity/grilling), `abeeaf9566`): Grill the user relentlessly about a plan, decision, or idea. Use when the user wants to stress-test their thinking, or uses any 'grill' trigger phrases.
- [handoff](../../skills/external/productivity/handoff/SKILL.md) ([upstream](https://github.com/mattpocock/skills/tree/abeeaf95660ba9e8b7c753eb38f441ca707a8823/skills/productivity/handoff), `abeeaf9566`): Compact the current conversation into a handoff document for another agent to pick up.
- [teach](../../skills/external/productivity/teach/SKILL.md) ([upstream](https://github.com/mattpocock/skills/tree/abeeaf95660ba9e8b7c753eb38f441ca707a8823/skills/productivity/teach), `abeeaf9566`): Teach the user a new skill or concept, within this workspace.
<!-- external-skills:end -->
