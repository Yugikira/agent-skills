---
name: ab-eval-skill
description: Design and execute blinded A/B evaluations to test whether a skill modification improves outcomes toward your goal. Use for /ab-eval-skill or before promoting any skill change.
disable-model-invocation: true
---

# Blinded A/B Skill Evaluation

Prove that a skill change (Variant B) improves real agent behavior over the baseline (Variant A) using blinded execution, hidden rubrics, and transcript audits. Read [references/BLINDING-CHECKLIST.md](references/BLINDING-CHECKLIST.md) before staging any run.

## Non-Negotiables

1. **Zero blinding leaks**: Never place `eval`, `test`, `judge`, `experiment`, `rubric`, `score`, `compare`, `benchmark`, `candidate`, or `arena` in any workspace path, filename, or prompt a candidate sees.
2. **Organic prompts only**: Write each prompt as a realistic user request stating the goal, never the meta-task or which skill is under test.
3. **No chain-eliciting cues**: Never ask candidates to list which skills or rules they followed. Verify skill adherence from execution transcripts and output shape.
4. **Fresh context windows**: Every candidate and judge runs in a fresh context window with no visibility into other runs.
5. **Single-pass blinded judging**: One judge (ideally from a different model family than the candidates) scores both outputs together on one hidden 3-6 criterion rubric using randomized neutral labels (`alpha`, `beta`).

## Workflow

1. **Frame**: Create or select an eval suite in `evals/suites/<name>.json` specifying the goal, organic prompts (3-5 realistic scenarios), and a hidden 3-6 criterion rubric.
2. **Stage**: Run the harness to validate blinding and build neutral workspaces:
   ```bash
   python3 scripts/ab_harness.py prepare \
     --suite evals/suites/<name>.json \
     --variant-a <path-to-baseline-skill> \
     --variant-b <path-to-candidate-skill> \
     --out eval-runs/<run-id>
   ```
3. **Execute candidates**: For each trial, run an agent in each staged workspace using the exact organic prompt. Alternate execution order (`A, B, B, A`) to avoid warmup or cache bias.
4. **Judge blind**: Give the judge only `eval-runs/<run-id>/judge-packet.json` (blinded outputs + rubric). Save its structured ratings to `eval-runs/<run-id>/judge-scores.json`.
5. **Audit & Score**:
   - Inspect candidate transcripts to verify the skill actually triggered and was read.
   - Read both outputs yourself end-to-end; flag any disagreement with the judge as rubric ambiguity or judge bias.
   - Unblind, compute medians/ranges/win-rate, and append to the decision trail:
     ```bash
     python3 scripts/ab_harness.py score \
       --run-dir eval-runs/<run-id> \
       --scores eval-runs/<run-id>/judge-scores.json \
       --log evals/results/eval-log.tsv
     ```

## Verdict Rules

- `PROMOTE_B`: B beats A on median composite score across trials, wins a majority of trials, and has zero critical regressions.
- `KEEP_A`: A beats B or B introduces a regression.
- `NO_MEASURABLE_DIFFERENCE`: Gap is smaller than run-to-run variation; prefer the shorter/simpler skill.
- `INCONCLUSIVE`: Fewer than 3 trials, a blinding leak occurred, or candidate failed to execute the task. Never promote on an inconclusive verdict.
