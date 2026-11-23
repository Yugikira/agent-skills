#!/usr/bin/env python3
"""Structural and policy verifier for the agent-skills repository.

Enforces:
- Valid YAML frontmatter in every SKILL.md (name matches dir, description non-empty)
- Global skill-name uniqueness across all buckets (meta, custom, external, in-progress, deprecated)
- Optional 1-level domain grouping inside skills/custom/ and skills/external/ (no depth > 2, no empty or mixed dirs)
- Dual-harness invocation parity (disable-model-invocation: true <-> agents/openai.yaml) for owned skills
- Line budget (warn > 250 lines, fail > 300 lines) for owned skills
- Zero em-dashes and resolved relative Markdown links in owned repo prose
- Progressive disclosure docs sync across README.md, bucket README.md, docs/README.md,
  docs/<bucket>/README.md, docs/custom/<group>/README.md, and docs/<bucket>/[<group>/]<name>.md
- Two-way sync between skills/external/ on disk, skills/external/manifest.json, and docs/external/README.md
  (vendored upstream skill packages are exempt from local style rules)
- Zero orphaned doc pages under docs/meta/, docs/custom/, and docs/external/
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
EXTERNAL_BUCKET = "external"
NON_PROMOTED_BUCKETS = ("in-progress", "deprecated")
ALL_BUCKETS = PROMOTED_BUCKETS + (EXTERNAL_BUCKET,) + NON_PROMOTED_BUCKETS
MAX_LINES_WARN = 250
MAX_LINES_FAIL = 300
KEBAB_RE = re.compile(r"[a-z0-9]+(?:-[a-z0-9]+)*")
DOCS_EXTERNAL_START = "<!-- external-skills:start -->"
DOCS_EXTERNAL_END = "<!-- external-skills:end -->"
REQUIRED_DOC_HEADINGS = (
    "## What it does",
    "## When to reach for it",
    "## Common questions",
    "## It's working if",
)
REQUIRED_MANIFEST_FIELDS = ("name", "repo", "subpath", "ref", "commit", "fetched_at")
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


def validate_skill_package(
    bucket: str,
    group: str | None,
    skill_dir: Path,
    seen_names: dict[str, Path],
    strict: bool = True,
) -> tuple[str, bool] | None:
    skill_md = skill_dir / "SKILL.md"
    if not skill_md.exists():
        errors.append(f"{skill_dir.relative_to(ROOT)}: missing SKILL.md")
        return None

    # Disallow nested skills inside a skill directory
    for nested in sorted(skill_dir.iterdir()):
        if nested.is_dir() and (nested / "SKILL.md").is_file():
            errors.append(
                f"{nested.relative_to(ROOT)}: nested skill directory inside skill '{skill_dir.relative_to(ROOT)}' is not allowed"
            )

    text = skill_md.read_text(encoding="utf-8")
    if strict:
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
    if not KEBAB_RE.fullmatch(name):
        errors.append(f"{skill_md.relative_to(ROOT)}: name '{name}' must be lowercase kebab-case")
    if not desc:
        errors.append(f"{skill_md.relative_to(ROOT)}: empty description")
    elif strict and len(desc) > 300:
        warnings.append(f"{skill_md.relative_to(ROOT)}: description is {len(desc)} chars (aim for <= 300)")

    if name:
        if name in seen_names:
            errors.append(
                f"{skill_dir.relative_to(ROOT)}: duplicate skill name '{name}' (already defined at {seen_names[name].relative_to(ROOT)})"
            )
        else:
            seen_names[name] = skill_dir

    user_invoked = meta.get("disable-model-invocation", "").lower() == "true"
    if strict:
        # Dual-harness invocation parity (owned skills only)
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

    return name or skill_dir.name, user_invoked


def validate_doc_page(doc_path: Path) -> None:
    if not doc_path.exists():
        errors.append(f"Missing docs page for promoted skill: {doc_path.relative_to(ROOT)}")
        return
    doc_text = doc_path.read_text(encoding="utf-8")
    for heading in REQUIRED_DOC_HEADINGS:
        if heading not in doc_text:
            errors.append(f"{doc_path.relative_to(ROOT)}: missing required section '{heading}'")


def check_external_bucket(seen_names: dict[str, Path], external_docs_text: str) -> None:
    ext_dir = ROOT / "skills" / EXTERNAL_BUCKET
    if not ext_dir.exists():
        errors.append("Missing bucket directory: skills/external")
        return
    if not (ext_dir / "README.md").exists():
        errors.append("Missing bucket README: skills/external/README.md")

    # Validate manifest.json
    mpath = ext_dir / "manifest.json"
    manifest_by_name: dict[str, dict] = {}
    if not mpath.exists():
        errors.append("Missing external manifest: skills/external/manifest.json")
    else:
        try:
            data = json.loads(mpath.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            errors.append(f"skills/external/manifest.json: invalid JSON ({exc})")
            data = None
        if isinstance(data, dict):
            if "schema_version" not in data or not isinstance(data.get("skills"), list):
                errors.append("skills/external/manifest.json: must contain 'schema_version' and 'skills' list")
            else:
                for idx, entry in enumerate(data["skills"]):
                    if not isinstance(entry, dict):
                        errors.append(f"skills/external/manifest.json: skills[{idx}] must be an object")
                        continue
                    for field in REQUIRED_MANIFEST_FIELDS:
                        if not entry.get(field):
                            errors.append(
                                f"skills/external/manifest.json: entry '{entry.get('name', idx)}' missing required field '{field}'"
                            )
                    ename = str(entry.get("name", ""))
                    if ename:
                        if ename in manifest_by_name:
                            errors.append(f"skills/external/manifest.json: duplicate entry '{ename}'")
                        else:
                            manifest_by_name[ename] = entry
                    egroup = entry.get("group")
                    if egroup is not None and not KEBAB_RE.fullmatch(str(egroup)):
                        errors.append(
                            f"skills/external/manifest.json: entry '{ename}' group '{egroup}' must be lowercase kebab-case"
                        )
        elif data is not None:
            errors.append("skills/external/manifest.json: top-level JSON value must be an object")

    # Scan skills/external/ on disk (optional 1-level grouping, relaxed style checks)
    on_disk: dict[str, str | None] = {}
    child_dirs = sorted(p for p in ext_dir.iterdir() if p.is_dir() and not p.name.startswith("."))
    for child in child_dirs:
        if (child / "SKILL.md").is_file():
            res = validate_skill_package(EXTERNAL_BUCKET, None, child, seen_names, strict=False)
            if res is not None:
                on_disk[child.name] = None
            continue

        # 1-level domain group under skills/external/
        group = child.name
        if not KEBAB_RE.fullmatch(group):
            errors.append(f"{child.relative_to(ROOT)}: group directory name '{group}' must be lowercase kebab-case")
        dup_readme = child / "README.md"
        if dup_readme.exists():
            errors.append(
                f"{dup_readme.relative_to(ROOT)}: duplicate group README not allowed; use docs/external/README.md"
            )
        sub_dirs = sorted(
            p for p in child.iterdir() if p.is_dir() and not p.name.startswith(".") and p.name != "__pycache__"
        )
        if not sub_dirs:
            errors.append(f"{child.relative_to(ROOT)}: empty domain group directory (missing child skills)")
            continue
        for skill_dir in sub_dirs:
            res = validate_skill_package(EXTERNAL_BUCKET, group, skill_dir, seen_names, strict=False)
            if res is not None:
                on_disk[skill_dir.name] = group

    # Two-way sync between on-disk external skills and manifest.json
    for sname, sgroup in sorted(on_disk.items()):
        if sname not in manifest_by_name:
            errors.append(f"skills/external: skill '{sname}' on disk is missing from skills/external/manifest.json")
        else:
            mgroup = manifest_by_name[sname].get("group")
            if mgroup != sgroup:
                errors.append(
                    f"skills/external/manifest.json: skill '{sname}' group '{mgroup}' != on-disk group '{sgroup}'"
                )

    for ename, entry in sorted(manifest_by_name.items()):
        egroup = entry.get("group")
        if ename not in on_disk:
            expected_rel = f"skills/external/{egroup}/{ename}" if egroup else f"skills/external/{ename}"
            errors.append(f"skills/external/manifest.json: entry '{ename}' missing on disk at {expected_rel}")
        if external_docs_text:
            expected_link = f"skills/external/{egroup}/{ename}/SKILL.md" if egroup else f"skills/external/{ename}/SKILL.md"
            if expected_link not in external_docs_text:
                errors.append(f"docs/external/README.md: missing link to vendored skill '{expected_link}'")


def check_skills() -> None:
    top_readme = (ROOT / "README.md").read_text(encoding="utf-8")
    router_path = ROOT / "skills/meta/skill-mode/SKILL.md"
    router_text = router_path.read_text(encoding="utf-8") if router_path.exists() else ""

    # Level-1 and Level-2 progressive disclosure docs indexes
    docs_root_readme = ROOT / "docs" / "README.md"
    if not docs_root_readme.exists():
        errors.append("Missing Level-1 docs index: docs/README.md")
        docs_root_text = ""
    else:
        docs_root_text = docs_root_readme.read_text(encoding="utf-8")
        for bucket in PROMOTED_BUCKETS + (EXTERNAL_BUCKET,):
            if f"{bucket}/README.md" not in docs_root_text:
                errors.append(f"docs/README.md: missing link to '{bucket}/README.md'")

    bucket_docs_text: dict[str, str] = {}
    for bucket in PROMOTED_BUCKETS + (EXTERNAL_BUCKET,):
        b_doc_readme = ROOT / "docs" / bucket / "README.md"
        if not b_doc_readme.exists():
            errors.append(f"Missing Level-2 docs index: docs/{bucket}/README.md")
            bucket_docs_text[bucket] = ""
        else:
            bucket_docs_text[bucket] = b_doc_readme.read_text(encoding="utf-8")

    ext_docs_text = bucket_docs_text.get(EXTERNAL_BUCKET, "")
    if ext_docs_text and (DOCS_EXTERNAL_START not in ext_docs_text or DOCS_EXTERNAL_END not in ext_docs_text):
        errors.append(
            f"docs/external/README.md: missing generator markers '{DOCS_EXTERNAL_START}' / '{DOCS_EXTERNAL_END}'"
        )

    seen_names: dict[str, Path] = {}
    expected_docs: set[Path] = set()

    for bucket in PROMOTED_BUCKETS + NON_PROMOTED_BUCKETS:
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

        child_dirs = sorted(p for p in bucket_dir.iterdir() if p.is_dir() and not p.name.startswith("."))

        for child in child_dirs:
            has_skill_md = (child / "SKILL.md").is_file()

            if bucket != "custom" or has_skill_md:
                # Standalone skill (or non-custom bucket skill)
                if validate_skill_package(bucket, None, child, seen_names, strict=True) is None:
                    continue

                rel_link = f"skills/{bucket}/{child.name}/SKILL.md"
                doc_path = ROOT / "docs" / bucket / f"{child.name}.md"
                if bucket in PROMOTED_BUCKETS:
                    expected_docs.add(doc_path.resolve())
                    if rel_link not in top_readme:
                        errors.append(f"README.md: missing link to promoted skill '{rel_link}'")
                    if f"{child.name}/SKILL.md" not in bucket_readme:
                        errors.append(f"skills/{bucket}/README.md: missing link to '{child.name}/SKILL.md'")
                    if f"{child.name}.md" not in bucket_docs_text[bucket]:
                        errors.append(f"docs/{bucket}/README.md: missing link to '{child.name}.md'")
                    if f"skills/{bucket}/{child.name}/SKILL.md" not in bucket_docs_text[bucket]:
                        errors.append(
                            f"docs/{bucket}/README.md: missing link to 'skills/{bucket}/{child.name}/SKILL.md'"
                        )
                    validate_doc_page(doc_path)
                    if bucket == "meta" and child.name != "skill-mode" and child.name not in router_text:
                        errors.append(f"skills/meta/skill-mode/SKILL.md: router does not mention meta skill '{child.name}'")
                else:
                    if rel_link in top_readme:
                        errors.append(f"README.md: non-promoted skill '{rel_link}' must not appear in top-level README.md")
                    if doc_path.exists():
                        errors.append(f"Non-promoted skill should not have docs page: {doc_path.relative_to(ROOT)}")
                continue

            # Custom domain group directory (1-level grouping inside skills/custom/)
            group = child.name
            if not KEBAB_RE.fullmatch(group):
                errors.append(f"{child.relative_to(ROOT)}: group directory name '{group}' must be lowercase kebab-case")

            dup_group_readme = child / "README.md"
            if dup_group_readme.exists():
                errors.append(
                    f"{dup_group_readme.relative_to(ROOT)}: duplicate group README not allowed; use docs/custom/{group}/README.md"
                )

            sub_dirs = sorted(
                p for p in child.iterdir() if p.is_dir() and not p.name.startswith(".") and p.name != "__pycache__"
            )
            if not sub_dirs:
                errors.append(f"{child.relative_to(ROOT)}: empty domain group directory (missing child skills)")
                continue

            group_doc_readme = ROOT / "docs" / "custom" / group / "README.md"
            expected_docs.add(group_doc_readme.resolve())
            if not group_doc_readme.exists():
                errors.append(f"Missing domain group overview: {group_doc_readme.relative_to(ROOT)}")
                group_doc_text = ""
            else:
                group_doc_text = group_doc_readme.read_text(encoding="utf-8")

            group_doc_rel = f"docs/custom/{group}/README.md"
            if group_doc_rel not in top_readme:
                errors.append(f"README.md: missing link to custom domain group '{group_doc_rel}'")
            if group_doc_rel not in bucket_readme:
                errors.append(f"skills/custom/README.md: missing link to custom domain group '{group_doc_rel}'")
            if f"{group}/README.md" not in bucket_docs_text["custom"]:
                errors.append(f"docs/custom/README.md: missing link to '{group}/README.md'")

            for skill_dir in sub_dirs:
                if validate_skill_package("custom", group, skill_dir, seen_names, strict=True) is None:
                    continue

                doc_path = ROOT / "docs" / "custom" / group / f"{skill_dir.name}.md"
                expected_docs.add(doc_path.resolve())
                validate_doc_page(doc_path)

                if group_doc_text:
                    if f"{skill_dir.name}.md" not in group_doc_text:
                        errors.append(f"{group_doc_readme.relative_to(ROOT)}: missing link to '{skill_dir.name}.md'")
                    skill_rel = f"skills/custom/{group}/{skill_dir.name}/SKILL.md"
                    if skill_rel not in group_doc_text:
                        errors.append(f"{group_doc_readme.relative_to(ROOT)}: missing link to '{skill_rel}'")

    # Validate external vendored bucket (shares global seen_names uniqueness check)
    check_external_bucket(seen_names, ext_docs_text)

    # Orphan doc check under docs/meta/, docs/custom/, and docs/external/
    for bucket in PROMOTED_BUCKETS + (EXTERNAL_BUCKET,):
        docs_bdir = ROOT / "docs" / bucket
        if not docs_bdir.is_dir():
            continue
        bucket_index = (docs_bdir / "README.md").resolve()
        for md_file in sorted(docs_bdir.rglob("*.md")):
            resolved = md_file.resolve()
            if resolved == bucket_index:
                continue
            if resolved not in expected_docs:
                errors.append(f"Orphaned doc page (no matching promoted skill/group): {md_file.relative_to(ROOT)}")


def check_markdown_files() -> None:
    for md_path in sorted(ROOT.rglob("*.md")):
        rel = md_path.relative_to(ROOT)
        if any(part.startswith(".") for part in rel.parts):
            continue
        if rel.parts[:2] == ("evals", "fixtures"):
            continue
        # Vendored upstream skill packages are exempt from local style/link rules,
        # while skills/external/README.md and docs/external/README.md remain enforced.
        if rel.parts[:2] == ("skills", EXTERNAL_BUCKET) and rel != Path("skills/external/README.md"):
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
