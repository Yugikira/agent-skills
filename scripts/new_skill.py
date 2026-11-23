#!/usr/bin/env python3
"""Scaffold a new skill in skills/in-progress/<name>/ plus a starter eval suite."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def main() -> int:
    parser = argparse.ArgumentParser(description="Scaffold a new skill in skills/in-progress/")
    parser.add_argument("name", help="Skill name in lowercase kebab-case")
    parser.add_argument("--mode", choices=("user", "model"), default="user", help="Invocation mode")
    parser.add_argument("--goal", required=True, help="Concrete user goal this skill improves")
    parser.add_argument("--dry-run", action="store_true", help="Print planned files without writing")
    args = parser.parse_args()

    if not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", args.name):
        print(f"Error: skill name '{args.name}' must be lowercase kebab-case.", file=sys.stderr)
        return 1

    skill_dir = ROOT / "skills" / "in-progress" / args.name
    eval_file = ROOT / "evals" / "suites" / f"{args.name}.json"

    if skill_dir.exists() and not args.dry_run:
        print(f"Error: {skill_dir.relative_to(ROOT)} already exists.", file=sys.stderr)
        return 1

    fm_extra = "disable-model-invocation: true\n" if args.mode == "user" else ""
    trigger_hint = f"Use for /{args.name}." if args.mode == "user" else f"Use when {args.goal.lower().rstrip('.')}."
    skill_md = f"""---
name: {args.name}
description: {args.goal.rstrip('.')}. {trigger_hint}
{fm_extra}---

# {args.name.replace('-', ' ').title()}

## Goal

{args.goal.rstrip('.')}.

## Workflow

1. Inspect the relevant files or state before making changes.
2. Execute the minimal step required to meet the goal.
3. Verify the real artifact before finishing.

## Done When

- The concrete check passes and evidence is reported.
"""

    starter_suite = {
        "suite_id": f"{args.name}-v1",
        "target_skill": args.name,
        "goal": args.goal,
        "trials": [
            {
                "trial_id": "t1",
                "workspace_slug": "harbor-app",
                "organic_prompt": "Replace with a realistic user request that exercises this skill.",
                "fixture_files": {"README.md": "# Harbor App\n"},
            }
        ],
        "rubric": [
            {"id": "goal_fit", "description": f"Achieves the stated goal: {args.goal}", "weight": 2},
            {"id": "verification", "description": "Verifies real output instead of self-reporting.", "weight": 2},
            {"id": "conciseness", "description": "Avoids unnecessary changes or filler.", "weight": 1},
        ],
    }

    if args.dry_run:
        print(f"[DRY-RUN] Would create {skill_dir.relative_to(ROOT)}/SKILL.md")
        if args.mode == "user":
            print(f"[DRY-RUN] Would create {skill_dir.relative_to(ROOT)}/agents/openai.yaml")
        print(f"[DRY-RUN] Would create {eval_file.relative_to(ROOT)}")
        return 0

    skill_dir.mkdir(parents=True, exist_ok=True)
    (skill_dir / "SKILL.md").write_text(skill_md, encoding="utf-8")
    if args.mode == "user":
        (skill_dir / "agents").mkdir(exist_ok=True)
        (skill_dir / "agents" / "openai.yaml").write_text(
            "policy:\n  allow_implicit_invocation: false\n", encoding="utf-8"
        )
    if not eval_file.exists():
        eval_file.parent.mkdir(parents=True, exist_ok=True)
        eval_file.write_text(json.dumps(starter_suite, indent=2) + "\n", encoding="utf-8")

    print(f"Created {skill_dir.relative_to(ROOT)}/SKILL.md and {eval_file.relative_to(ROOT)}")
    print("Next: edit the skill, populate 3+ organic trials, and run python3 scripts/verify_repo.py")
    return 0


if __name__ == "__main__":
    sys.exit(main())
