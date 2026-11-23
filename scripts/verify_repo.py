#!/usr/bin/env python3
"""Structural and policy verifier for the agent-skills repository.

Enforces:
- Valid YAML frontmatter in every SKILL.md (name matches dir, description non-empty)
- Dual-harness invocation parity (disable-model-invocation: true <-> agents/openai.yaml)
- Line budget (warn > 250 lines, fail > 300 lines)
- Zero em-dashes in repo prose
- All relative Markdown links resolve to existing files
- Promoted skills (meta/, custom/) synced across README.md, bucket README.md,
  and docs/<bucket>/<name>.md (4 required H2 headings); meta/ skills synced in skill-mode router
- Non-promoted skills (in-progress/, deprecated/) excluded from top-level README.md and docs/
- Zero blinding-leak terms in evals/suites/*.json candidate-visible fields
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PROMOTED_BUCKETS = ("meta", "custom")
NON_PROMOTED_BUCKETS = ("in-progress", "deprecated")
ALL_BUCKETS = PROMOTED_BUCKETS + NON_PROMOTED_BUCKETS
MAX_LINES_WARN = 250
MAX_LINES_FAIL = 300
REQUIRED_DOC_HEADINGS = (
    "## What it does",
    "## When to reach for it",
    "## Common questions",
    "## It's working if",
)
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

errors: list[str] = []
warnings: list[str] = []


def parse_frontmatter(text: str, path: Path) -> tuple[dict[str, str], str]:
    if not text.startswith("---\n"):
        errors.append(f"{path.relative_to(ROOT)}: missing YAML frontmatter")
        return {}, text
    parts = text.split("\n---\n", 1)
    if len(parts) != 2:
        errors.append(f"{path.relative_to(ROOT)}: unclosed YAML frontmatter")
        return {}, text
    raw_fm, body = parts[0][4:], parts[1]
    meta: dict[str, str] = {}
    for line in raw_fm.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if ":" in stripped:
            key, val = stripped.split(":", 1)
            meta[key.strip()] = val.strip().strip('"').strip("'")
    return meta, body


def check_em_dashes(path: Path, text: str) -> None:
    for idx, line in enumerate(text.splitlines(), 1):
        if "\u2014" in line:
            errors.append(f"{path.relative_to(ROOT)}:{idx}: em-dash found; rewrite with comma, colon, period, or parentheses")


def check_relative_links(path: Path, text: str) -> None:
    link_re = re.compile(r"\[[^\]]+\]\(([^)]+)\)")
    in_code_block = False
    for idx, line in enumerate(text.splitlines(), 1):
        if line.strip().startswith("```"):
            in_code_block = not in_code_block
            continue
        if in_code_block:
            continue
        cleaned_line = re.sub(r"`[^`]*`", "", line)
        for match in link_re.finditer(cleaned_line):
            target = match.group(1).strip()
            if target.startswith(("http://", "https://", "mailto:", "#")):
                continue
            if any(ch in target for ch in ("{", "}", "<", ">")):
                continue
            target_path = target.split("#", 1)[0]
            if not target_path:
                continue
            resolved = (path.parent / target_path).resolve()
            if not resolved.exists():
                errors.append(f"{path.relative_to(ROOT)}:{idx}: broken relative link -> {target}")


def check_skills() -> None:
    top_readme = (ROOT / "README.md").read_text(encoding="utf-8")
    router_path = ROOT / "skills/meta/skill-mode/SKILL.md"
    router_text = router_path.read_text(encoding="utf-8") if router_path.exists() else ""

    for bucket in ALL_BUCKETS:
        bucket_dir = ROOT / "skills" / bucket
        if not bucket_dir.exists():
            errors.append(f"Missing bucket directory: skills/{bucket}")
            continue
        bucket_readme_path = bucket_dir / "README.md"
        if not bucket_readme_path.exists():
            errors.append(f"Missing bucket README: skills/{bucket}/README.md")
            bucket_readme = ""
        else:
            bucket_readme = bucket_readme_path.read_text(encoding="utf-8")

        for skill_dir in sorted(p for p in bucket_dir.iterdir() if p.is_dir()):
            skill_md = skill_dir / "SKILL.md"
            if not skill_md.exists():
                errors.append(f"{skill_dir.relative_to(ROOT)}: missing SKILL.md")
                continue
            text = skill_md.read_text(encoding="utf-8")
            lines = text.splitlines()
            if len(lines) > MAX_LINES_FAIL:
                errors.append(f"{skill_md.relative_to(ROOT)}: {len(lines)} lines exceeds hard cap ({MAX_LINES_FAIL})")
            elif len(lines) > MAX_LINES_WARN:
                warnings.append(f"{skill_md.relative_to(ROOT)}: {len(lines)} lines exceeds soft target ({MAX_LINES_WARN})")

            meta, _ = parse_frontmatter(text, skill_md)
            name = meta.get("name", "")
            desc = meta.get("description", "")
            if name != skill_dir.name:
                errors.append(f"{skill_md.relative_to(ROOT)}: frontmatter name '{name}' != directory '{skill_dir.name}'")
            if not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", name):
                errors.append(f"{skill_md.relative_to(ROOT)}: name '{name}' must be lowercase kebab-case")
            if not desc:
                errors.append(f"{skill_md.relative_to(ROOT)}: empty description")
            elif len(desc) > 300:
                warnings.append(f"{skill_md.relative_to(ROOT)}: description is {len(desc)} chars (aim for <= 300)")

            # Dual-harness invocation parity
            user_invoked = meta.get("disable-model-invocation", "").lower() == "true"
            openai_yaml = skill_dir / "agents" / "openai.yaml"
            if user_invoked:
                if not openai_yaml.exists():
                    errors.append(f"{skill_dir.relative_to(ROOT)}: user-invoked skill missing agents/openai.yaml")
                else:
                    yaml_text = openai_yaml.read_text(encoding="utf-8")
                    if "allow_implicit_invocation: false" not in yaml_text:
                        errors.append(
                            f"{openai_yaml.relative_to(ROOT)}: must set 'allow_implicit_invocation: false' for user-invoked skill"
                        )
            else:
                if openai_yaml.exists() and "allow_implicit_invocation: false" in openai_yaml.read_text(encoding="utf-8"):
                    errors.append(
                        f"{openai_yaml.relative_to(ROOT)}: sets allow_implicit_invocation: false but SKILL.md omits disable-model-invocation: true"
                    )

            # Promoted vs non-promoted sync checks
            rel_link = f"skills/{bucket}/{skill_dir.name}/SKILL.md"
            doc_path = ROOT / "docs" / bucket / f"{skill_dir.name}.md"
            if bucket in PROMOTED_BUCKETS:
                if rel_link not in top_readme:
                    errors.append(f"README.md: missing link to promoted skill '{rel_link}'")
                if f"{skill_dir.name}/SKILL.md" not in bucket_readme:
                    errors.append(f"skills/{bucket}/README.md: missing link to '{skill_dir.name}/SKILL.md'")
                if not doc_path.exists():
                    errors.append(f"Missing docs page for promoted skill: {doc_path.relative_to(ROOT)}")
                else:
                    doc_text = doc_path.read_text(encoding="utf-8")
                    for heading in REQUIRED_DOC_HEADINGS:
                        if heading not in doc_text:
                            errors.append(f"{doc_path.relative_to(ROOT)}: missing required section '{heading}'")
                if bucket == "meta" and skill_dir.name != "skill-mode" and skill_dir.name not in router_text:
                    errors.append(f"skills/meta/skill-mode/SKILL.md: router does not mention meta skill '{skill_dir.name}'")
            else:
                if rel_link in top_readme:
                    errors.append(f"README.md: non-promoted skill '{rel_link}' must not appear in top-level README.md")
                if doc_path.exists():
                    errors.append(f"Non-promoted skill should not have docs page: {doc_path.relative_to(ROOT)}")


def check_markdown_files() -> None:
    for md_path in sorted(ROOT.rglob("*.md")):
        rel = md_path.relative_to(ROOT)
        if any(part.startswith(".") for part in rel.parts):
            continue
        if rel.parts[:2] == ("evals", "fixtures"):
            continue
        text = md_path.read_text(encoding="utf-8")
        check_em_dashes(md_path, text)
        check_relative_links(md_path, text)


def check_eval_suites() -> None:
    suites_dir = ROOT / "evals" / "suites"
    if not suites_dir.exists():
        return
    word_patterns = [(w, re.compile(rf"\b{re.escape(w)}\b", re.IGNORECASE)) for w in BANNED_BLINDING_WORDS]
    for suite_path in sorted(suites_dir.glob("*.json")):
        try:
            data = json.loads(suite_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            errors.append(f"{suite_path.relative_to(ROOT)}: invalid JSON ({exc})")
            continue
        for key in ("suite_id", "target_skill", "goal", "trials", "rubric"):
            if key not in data:
                errors.append(f"{suite_path.relative_to(ROOT)}: missing required key '{key}'")
        rubric = data.get("rubric", [])
        if not (3 <= len(rubric) <= 6):
            warnings.append(f"{suite_path.relative_to(ROOT)}: rubric has {len(rubric)} criteria (recommended 3-6)")
        for trial in data.get("trials", []):
            tid = trial.get("trial_id", "?")
            fields_to_check = [
                ("workspace_slug", str(trial.get("workspace_slug", ""))),
                ("organic_prompt", str(trial.get("organic_prompt", ""))),
                ("fixture_target", str(trial.get("fixture_target", ""))),
            ]
            for fname in (trial.get("fixture_files") or {}).keys():
                fields_to_check.append((f"fixture_files[{fname}]", str(fname)))
            if trial.get("fixture_dir"):
                raw_dir = Path(str(trial["fixture_dir"])).expanduser()
                fix_path = raw_dir if raw_dir.is_absolute() else (suite_path.parent / raw_dir)
                if not fix_path.is_dir():
                    fix_path = ROOT / raw_dir
                if not fix_path.is_dir():
                    errors.append(f"{suite_path.relative_to(ROOT)} (trial {tid}): fixture_dir not found -> {trial['fixture_dir']}")
                else:
                    for fp in sorted(fix_path.rglob("*")):
                        rel_fp = fp.relative_to(fix_path)
                        if any(part in (".git", "__pycache__", ".DS_Store") for part in rel_fp.parts):
                            continue
                        fields_to_check.append((f"fixture_dir[{rel_fp}]", str(rel_fp)))
            for field_name, val in fields_to_check:
                for word, pat in word_patterns:
                    if pat.search(val):
                        errors.append(
                            f"{suite_path.relative_to(ROOT)} (trial {tid}, {field_name}): blinding leak word '{word}'"
                        )


def main() -> int:
    check_skills()
    check_markdown_files()
    check_eval_suites()

    for w in warnings:
        print(f"[WARN] {w}")
    for e in errors:
        print(f"[FAIL] {e}")

    if errors:
        print(f"\nVerification FAILED: {len(errors)} error(s), {len(warnings)} warning(s).")
        return 1
    print(f"Verification PASSED: 0 errors, {len(warnings)} warning(s).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
