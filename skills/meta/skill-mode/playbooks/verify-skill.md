# Playbook: Verify Skills & Repository

1. **Load verification skill**: Read `skills/meta/verify-skills/SKILL.md`.
2. **Run Doctor (static checks)**: Execute `python3 scripts/verify_repo.py`. Inspect every failure or warning.
3. **Run live smoke checks**: Exercise any modified script or skill end-to-end in an isolated temp workspace.
4. **Triage outcome**: Classify the run as `clean`, `changed`, or `blocked`. Never weaken a check to make it pass.
5. **Cleanup and preserve evidence**: Remove scratch workspaces while confirming verification output or logs remain intact.
