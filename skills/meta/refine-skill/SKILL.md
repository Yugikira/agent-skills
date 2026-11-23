---
name: refine-skill
description: Run a hypothesis-driven hillclimb and no-op pruning loop to improve an existing skill against a concrete goal. Use for /refine-skill or when a skill misfires, drifts, or underperforms.
disable-model-invocation: true
---

# Refine a Skill

Improve an existing skill through small, falsifiable iterations. Each iteration tests one hypothesis, verifies structure, and proves behavioral improvement before keeping the change.

## Phase 1: Diagnose Before Editing

1. Read the target `SKILL.md`, its `references/`, and recent failure evidence (transcripts, diffs, or `evals/results/eval-log.tsv`).
2. Classify the root cause before writing a single word:
   - **Trigger miss**: pointer description omits a branch or uses weak leading words.
   - **Directive degradation**: file is bloated, repetitive, or buries constraints under filler.
   - **Structural gap**: a checkable invariant was left as prose instead of a script or lint rule.
   - **Missing completion gate**: step lacks a falsifiable done-condition.
3. Choose the highest-leverage fix level: `scripts/verify_repo.py` lint > frontmatter/metadata > `SKILL.md` edit > `references/` detail.

## Phase 2: One-Hypothesis Hillclimb

1. State the hypothesis in one sentence: "Changing X will improve metric Y on suite Z."
2. Make the smallest edit that tests that hypothesis. Load `skills/meta/writing-for-agents/SKILL.md` and run a no-op pruning pass on every touched section.
3. Run `python3 scripts/verify_repo.py`. Fix any structural error immediately.
4. Run a blinded A/B evaluation (`skills/meta/ab-eval-skill/SKILL.md`) comparing the pre-edit skill (A) against the modified skill (B) on the relevant eval suite.

## Phase 3: Keep, Revert, or Graft

- **Promote**: B beats A on the primary goal with no regressions and passes `verify_repo.py`. Keep the commit and log it in `evals/results/eval-log.tsv`.
- **Revert**: B ties or loses to A, or introduces a regression. Revert the edit; never relax the rubric to make a change pass.
- **Stalled (2+ rejects)**: Stop patching the same premise. Run an arena (2-3 distinct rewrites from first principles), judge them blind, pick the winning base, and graft only 1-2 winning ideas by hand.
