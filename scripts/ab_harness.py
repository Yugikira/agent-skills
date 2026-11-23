#!/usr/bin/env python3
"""Blinded A/B evaluation harness for agent skills.

Subcommands:
  prepare    Stage sanitized neutral workspaces for Variant A & B with randomized blind labels.
  score      Unblind judge ratings, compute medians/ranges/win-rate, emit verdict, and append TSV log.
  self-test  Run an isolated end-to-end smoke test of prepare -> score -> cleanup.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import random
import re
import shutil
import statistics
import sys
import tempfile
from pathlib import Path

BANNED_BLINDING_WORDS = (
    "eval",
    "test",
    "judge",
    "experiment",
    "rubric",
    "score",
    "compare",
    "benchmark",
    "candidate",
    "arena",
)


def check_blinding_clean(text: str, label: str) -> None:
    for word in BANNED_BLINDING_WORDS:
        if re.search(rf"\b{re.escape(word)}\b", text, re.IGNORECASE):
            raise ValueError(f"Blinding violation in {label}: contains banned word '{word}'")


def copy_skill_into_workspace(skill_src: Path, workspace_dir: Path) -> None:
    if skill_src.is_dir():
        dest = workspace_dir / ".agents" / "skills" / skill_src.name
        shutil.copytree(skill_src, dest)
    elif skill_src.is_file():
        dest = workspace_dir / ".agents" / "skills" / skill_src.parent.name / skill_src.name
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(skill_src, dest)
    else:
        raise FileNotFoundError(f"Skill path not found: {skill_src}")


def cmd_prepare(args: argparse.Namespace) -> int:
    suite_path = Path(args.suite).resolve()
    suite = json.loads(suite_path.read_text(encoding="utf-8"))
    variant_a = Path(args.variant_a).resolve()
    variant_b = Path(args.variant_b).resolve()
    out_dir = Path(args.out).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    rng = random.Random(args.seed)
    manifest: dict = {
        "suite_id": suite["suite_id"],
        "target_skill": suite["target_skill"],
        "goal": suite["goal"],
        "variant_a": str(variant_a),
        "variant_b": str(variant_b),
        "created_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        "rubric": suite["rubric"],
        "trials": [],
    }
    judge_packet: dict = {
        "goal": suite["goal"],
        "rubric": suite["rubric"],
        "instructions": "Score each trial's two outputs (alpha and beta) independently on a 1-5 scale per rubric criterion. Do not guess which label is newer.",
        "trials": [],
    }

    for idx, trial in enumerate(suite["trials"]):
        tid = trial["trial_id"]
        slug = trial["workspace_slug"]
        prompt = trial["organic_prompt"]
        check_blinding_clean(slug, f"trial {tid} workspace_slug")
        check_blinding_clean(prompt, f"trial {tid} organic_prompt")

        # Randomize which variant maps to alpha vs beta per trial
        if rng.random() < 0.5:
            mapping = {"alpha": "A", "beta": "B"}
        else:
            mapping = {"alpha": "B", "beta": "A"}
        # Alternate execution order across trials
        order = ["alpha", "beta"] if idx % 2 == 0 else ["beta", "alpha"]

        trial_record = {
            "trial_id": tid,
            "mapping": mapping,
            "execution_order": order,
            "workspaces": {},
        }

        for blind_label in ("alpha", "beta"):
            ws_name = f"{slug}-{'west' if blind_label == 'alpha' else 'east'}"
            check_blinding_clean(ws_name, f"workspace {ws_name}")
            ws_dir = out_dir / "workspaces" / tid / ws_name
            ws_dir.mkdir(parents=True, exist_ok=True)

            # Write neutral fixture files
            for rel_file, content in (trial.get("fixture_files") or {}).items():
                check_blinding_clean(rel_file, f"fixture path {rel_file}")
                f_path = ws_dir / rel_file
                f_path.parent.mkdir(parents=True, exist_ok=True)
                f_path.write_text(content, encoding="utf-8")

            # Install assigned skill variant
            assigned_variant = variant_a if mapping[blind_label] == "A" else variant_b
            copy_skill_into_workspace(assigned_variant, ws_dir)

            # Save organic prompt outside the candidate's repo root
            trial_record["workspaces"][blind_label] = str(ws_dir)

        manifest["trials"].append(trial_record)
        judge_packet["trials"].append(
            {
                "trial_id": tid,
                "organic_prompt": prompt,
                "outputs": {
                    "alpha": "<paste or link output from alpha workspace>",
                    "beta": "<paste or link output from beta workspace>",
                },
            }
        )

    # Sealed manifest is only read by score(), never shown to candidates or judge
    (out_dir / "sealed-manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    (out_dir / "judge-packet.json").write_text(json.dumps(judge_packet, indent=2) + "\n", encoding="utf-8")
    print(f"Prepared {len(manifest['trials'])} blinded trials in {out_dir}")
    print(f"Judge packet: {out_dir / 'judge-packet.json'}")
    return 0


def weighted_score(ratings: dict[str, float], weights: dict[str, float]) -> float:
    total_w = sum(weights.values()) or 1.0
    return sum(float(ratings[k]) * weights[k] for k in weights) / total_w


def cmd_score(args: argparse.Namespace) -> int:
    run_dir = Path(args.run_dir).resolve()
    manifest = json.loads((run_dir / "sealed-manifest.json").read_text(encoding="utf-8"))
    judge_data = json.loads(Path(args.scores).resolve().read_text(encoding="utf-8"))

    weights = {c["id"]: float(c.get("weight", 1.0)) for c in manifest["rubric"]}
    mapping_by_trial = {t["trial_id"]: t["mapping"] for t in manifest["trials"]}

    scores_a: list[float] = []
    scores_b: list[float] = []
    wins_b = 0
    losses_b = 0
    ties = 0
    critical_regression = False

    for entry in judge_data.get("trials", []):
        tid = entry["trial_id"]
        mapping = mapping_by_trial[tid]
        alpha_val = weighted_score(entry["scores"]["alpha"], weights)
        beta_val = weighted_score(entry["scores"]["beta"], weights)

        if mapping["alpha"] == "A":
            val_a, val_b = alpha_val, beta_val
        else:
            val_a, val_b = beta_val, alpha_val

        scores_a.append(val_a)
        scores_b.append(val_b)
        if val_b > val_a + 1e-6:
            wins_b += 1
        elif val_a > val_b + 1e-6:
            losses_b += 1
        else:
            ties += 1
        if val_b < val_a - 1.0:
            critical_regression = True

    n = len(scores_a)
    if n == 0:
        raise ValueError("No scored trials found.")

    med_a = statistics.median(scores_a)
    med_b = statistics.median(scores_b)
    range_a = max(scores_a) - min(scores_a)
    range_b = max(scores_b) - min(scores_b)
    noise_floor = max(range_a, range_b) * 0.25
    gap = med_b - med_a

    if n < 3:
        verdict = "INCONCLUSIVE"
    elif critical_regression:
        verdict = "KEEP_A"
    elif gap > max(0.15, noise_floor) and wins_b > losses_b:
        verdict = "PROMOTE_B"
    elif gap < -max(0.15, noise_floor) and losses_b > wins_b:
        verdict = "KEEP_A"
    else:
        verdict = "NO_MEASURABLE_DIFFERENCE"

    summary = {
        "suite_id": manifest["suite_id"],
        "trials": n,
        "median_a": round(med_a, 3),
        "median_b": round(med_b, 3),
        "range_a": [round(min(scores_a), 3), round(max(scores_a), 3)],
        "range_b": [round(min(scores_b), 3), round(max(scores_b), 3)],
        "wins_b": wins_b,
        "losses_b": losses_b,
        "ties": ties,
        "verdict": verdict,
    }
    print(json.dumps(summary, indent=2))

    if args.log:
        log_path = Path(args.log).resolve()
        log_path.parent.mkdir(parents=True, exist_ok=True)
        if not log_path.exists():
            log_path.write_text(
                "timestamp\tsuite_id\tvariant_a\tvariant_b\ttrials\tmedian_a\tmedian_b\twin_b\tloss_b\ttie\tverdict\tnotes\n",
                encoding="utf-8",
            )
        ts = dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        note = (args.notes or "").replace("\t", " ").replace("\n", " ")
        row = (
            f"{ts}\t{manifest['suite_id']}\t{Path(manifest['variant_a']).name}\t"
            f"{Path(manifest['variant_b']).name}\t{n}\t{med_a:.3f}\t{med_b:.3f}\t"
            f"{wins_b}\t{losses_b}\t{ties}\t{verdict}\t{note}\n"
        )
        with log_path.open("a", encoding="utf-8") as fh:
            fh.write(row)
        print(f"Appended verdict to {log_path}")

    return 0


def cmd_self_test(_args: argparse.Namespace) -> int:
    root = Path(__file__).resolve().parent.parent
    suite = root / "evals" / "suites" / "example-skill-eval.json"
    skill_dir = root / "skills" / "meta" / "writing-for-agents"
    with tempfile.TemporaryDirectory(prefix="ab_selftest_") as tmp:
        tmp_path = Path(tmp)
        run_dir = tmp_path / "run1"
        prep_args = argparse.Namespace(
            suite=str(suite),
            variant_a=str(skill_dir),
            variant_b=str(skill_dir),
            out=str(run_dir),
            seed=42,
        )
        cmd_prepare(prep_args)
        manifest = json.loads((run_dir / "sealed-manifest.json").read_text(encoding="utf-8"))
        mock_scores = {"trials": []}
        for t in manifest["trials"]:
            b_label = "alpha" if t["mapping"]["alpha"] == "B" else "beta"
            a_label = "beta" if b_label == "alpha" else "alpha"
            mock_scores["trials"].append(
                {
                    "trial_id": t["trial_id"],
                    "scores": {
                        a_label: {"noop_pruning": 3, "constraint_preservation": 4, "clarity_and_structure": 3},
                        b_label: {"noop_pruning": 5, "constraint_preservation": 5, "clarity_and_structure": 4},
                    },
                }
            )
        scores_file = run_dir / "judge-scores.json"
        scores_file.write_text(json.dumps(mock_scores, indent=2), encoding="utf-8")
        log_file = tmp_path / "test-log.tsv"
        score_args = argparse.Namespace(
            run_dir=str(run_dir),
            scores=str(scores_file),
            log=str(log_file),
            notes="harness self-test",
        )
        cmd_score(score_args)
        assert log_file.exists() and "PROMOTE_B" in log_file.read_text(encoding="utf-8")
    print("ab_harness self-test PASSED.")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Blinded A/B skill evaluation harness")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_prep = sub.add_parser("prepare", help="Stage sanitized workspaces and judge packet")
    p_prep.add_argument("--suite", required=True)
    p_prep.add_argument("--variant-a", required=True)
    p_prep.add_argument("--variant-b", required=True)
    p_prep.add_argument("--out", required=True)
    p_prep.add_argument("--seed", type=int, default=None)
    p_prep.set_defaults(func=cmd_prepare)

    p_score = sub.add_parser("score", help="Unblind judge ratings and compute verdict")
    p_score.add_argument("--run-dir", required=True)
    p_score.add_argument("--scores", required=True)
    p_score.add_argument("--log", default=None)
    p_score.add_argument("--notes", default="")
    p_score.set_defaults(func=cmd_score)

    p_self = sub.add_parser("self-test", help="Run isolated prepare -> score smoke test")
    p_self.set_defaults(func=cmd_self_test)

    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
