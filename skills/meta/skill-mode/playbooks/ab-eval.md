# Playbook: Blinded A/B Evaluation

1. **Load eval skill**: Read `skills/meta/ab-eval-skill/SKILL.md` and `skills/meta/ab-eval-skill/references/BLINDING-CHECKLIST.md`.
2. **Frame**: Define the baseline (A), candidate (B), target goal, and a hidden 3-6 criterion rubric.
3. **Stage sanitized workspaces**: Run `python3 scripts/ab_harness.py prepare --suite <suite.json> --variant-a <path> --variant-b <path> --out <tmp-dir>`.
4. **Run candidates**: Dispatch fresh-context-window agents on identical organic prompts in each sanitized workspace. Never reveal A/B labels, rubrics, or other runs.
5. **Judge blind**: Have one judge (ideally a different model family) score all outputs in a single pass using only randomized blind labels.
6. **Audit transcripts & score**: Inspect which files candidates actually read, run `python3 scripts/ab_harness.py score`, and log the verdict to `evals/results/eval-log.tsv`.
