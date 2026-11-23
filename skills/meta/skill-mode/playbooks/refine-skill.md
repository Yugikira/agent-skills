# Playbook: Refine a Skill

1. **Load refine skill**: Read `skills/meta/refine-skill/SKILL.md`.
2. **Capture baseline**: Identify the concrete failure mode from transcripts, diffs, or eval results, and record the baseline score.
3. **Form one hypothesis**: State the smallest root-cause edit (prefer script/lint > metadata > skill prose).
4. **Apply and lint**: Make the single edit and run `python3 scripts/verify_repo.py`.
5. **Measure blinded**: Run `playbooks/ab-eval.md` comparing baseline (A) against the modified skill (B).
6. **Keep or revert**: Promote only if B wins on the goal without regressions; otherwise revert and test the next hypothesis.
