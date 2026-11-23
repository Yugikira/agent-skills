## What it does

`ab-eval-skill` designs and executes blinded A/B evaluations for skill modifications. Using `scripts/ab_harness.py`, it stages sanitized neutral workspaces, runs identical organic prompts in fresh context windows, has a blinded judge score both variants on a hidden rubric, audits transcripts to verify real skill usage, and logs statistical verdicts to `evals/results/eval-log.tsv`.

## When to reach for it

You invoke this by typing `/ab-eval-skill`, and the agent will not reach for it on its own. Reach for it whenever you modify a promoted skill or prepare to promote a beta skill from `skills/in-progress/`.

## Common questions

**Why ban words like `eval`, `test`, and `rubric` from candidate prompts and directories?**
Agents behave differently when they detect they are being evaluated (eval awareness). Neutral workspace names and organic user prompts measure real production behavior instead of benchmark theater.

**What if the judge verdict disagrees with my own reading?**
Treat disagreement as a signal of rubric ambiguity or judge bias. Sharpen the rubric criteria and re-run rather than blindly accepting the score.

## It's working if

- Every promoted skill modification has a blinded `PROMOTE_B` row in `evals/results/eval-log.tsv`.
- No-op edits are caught as `NO_MEASURABLE_DIFFERENCE` and rejected before bloating your skills.
