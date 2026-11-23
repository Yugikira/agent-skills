# External Skills

Curated third-party skills vendored from upstream Git repositories via `scripts/external_skills.py` and pinned by commit SHA in `manifest.json`.

- **Catalog & upstream provenance**: [docs/external/README.md](../../docs/external/README.md)
- **Logical domain grouping**: External skills may live under a 1-level group (`skills/external/<group>/<skill>/`) sharing a group name with `skills/custom/<group>/` so `install_skills.py install --group <group>` deploys both together.
- **Verification**: Vendored packages are checked for valid frontmatter, global name uniqueness, and `manifest.json` sync while remaining exempt from local prose style rules.

## Commands

```bash
python3 scripts/external_skills.py add https://github.com/<owner>/<repo>/tree/main/skills/<name> --group <group>
python3 scripts/external_skills.py check
python3 scripts/external_skills.py update <name>
python3 scripts/external_skills.py remove <name>
```
