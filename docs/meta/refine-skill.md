## What it does

`refine-skill` runs a structured, single-hypothesis hillclimb loop to improve an existing skill against your goal. It diagnoses the failure class first (trigger miss, directive degradation, structural gap, or weak completion gate), applies one minimal edit, validates structure, and requires a blinded A/B win before keeping the change.

## When to reach for it

You invoke this by typing `/refine-skill`, and the agent will not reach for it on its own. Reach for it when a skill misfires, produces verbose or inconsistent results, or needs tightening after a failed session. For authoring a brand-new skill from scratch, use `skill-mode` with the authoring playbook.

## Common questions

**What if two consecutive edits fail to beat baseline?**
Stop patching the same premise. Run an arena of 2-3 fresh rewrites from first principles, judge them blind, and graft only the strongest ideas into the winning base.

**Why prefer script checks over adding prose rules?**
Prose rules consume context on every run and suffer from directive degradation. Moving a check into `scripts/verify_repo.py` enforces it deterministically at zero token cost.

## It's working if

- Every accepted edit has a recorded before/after win in `evals/results/eval-log.tsv`.
- Failed hypotheses are reverted cleanly instead of accumulating as dead sediment in `SKILL.md`.
