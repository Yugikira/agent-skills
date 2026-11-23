# Playbook: Authoring or Updating a Skill

1. **Read the reference**: Load `skills/meta/writing-for-agents/SKILL.md` (and `references/SKILL-MECHANICS.md` when creating a new skill).
2. **Scaffold or locate**:
   - New skill: run `python3 scripts/new_skill.py <name> --mode <user|model> --goal "<goal>"` to create it in `skills/in-progress/<name>/`.
   - Existing skill: read the full `SKILL.md` and any linked `references/` files before editing.
3. **Draft with delete-first discipline**:
   - Write the execution spine only; push checklists, schemas, and rubrics into `references/`.
   - Keep `SKILL.md` under 250 lines (hard cap: 300 lines).
   - Sync `disable-model-invocation: true` with `agents/openai.yaml` (`policy.allow_implicit_invocation: false`) for user-invoked skills.
4. **Apply the no-op pass**: Test each sentence by asking whether deleting it changes agent behavior. Delete no-ops and duplicates.
5. **Validate**: Run `python3 scripts/verify_repo.py` and fix every error.
6. **Prove improvement**: Before promoting to `skills/custom/` or merging a behavioral edit, run `playbooks/ab-eval.md`.
