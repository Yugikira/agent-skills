#!/usr/bin/env python3
"""Cross-platform skill deployment tool for the agent-skills forge.

Replaces bash symlink scripts with safe, opt-in workspace or global installation
using native directory junctions on Windows (no admin required), symlinks on Unix,
or provenance-tracked copies.

Supports optional 1-level domain groups under skills/custom/<group>/<skill>/ and
skills/external/<group>/<skill>/ (logical grouping across buckets), while always
flattening deployed targets to <target>/<skill>/ for harness compatibility.

Subcommands:
  list         Show available skills grouped by bucket and domain group.
  mount-local  Link this repo's meta-skills into local .agents/skills (gitignored).
  install      Deploy selected skills or groups to a workspace, global dir, or custom dest.
  uninstall    Safely remove forge-managed skills without touching unmanaged ones.
  self-test    Run an isolated temp-directory smoke test of all modes and guards.
"""

from __future__ import annotations

import argparse
import dataclasses
import datetime as dt
import json
import os
import shutil
import stat
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PROMOTED_BUCKETS = ("meta", "custom")
GROUPABLE_BUCKETS = ("custom", "external")
DEPLOYABLE_BUCKETS = ("meta", "custom", "external")
ALL_BUCKETS = ("meta", "custom", "external", "in-progress", "deprecated")
MANAGED_MARKER = ".forge-managed.json"
MANAGED_BY = "agent-skills-forge"

HARNESS_WORKSPACE_REL = {
    "agents": Path(".agents") / "skills",
    "claude": Path(".claude") / "skills",
    "antigravity": Path(".agents") / "skills",
    "cursor": Path(".cursor") / "skills",
}

DEFAULT_GLOBAL_HARNESSES = ("agents", "claude", "antigravity")


@dataclasses.dataclass(frozen=True)
class SkillRecord:
    bucket: str
    group: str | None
    name: str
    path: Path
    description: str = ""

    @property
    def source_label(self) -> str:
        if self.group:
            return f"{self.bucket}/{self.group}/{self.name}"
        return f"{self.bucket}/{self.name}"


def harness_global_dir(harness: str, home: Path | None = None) -> Path:
    base = home or Path.home()
    mapping = {
        "agents": base / ".agents" / "skills",
        "claude": base / ".claude" / "skills",
        "antigravity": base / ".gemini" / "config" / "skills",
        "cursor": base / ".cursor" / "skills",
    }
    return mapping[harness]


def read_skill_description(skill_md: Path) -> str:
    try:
        text = skill_md.read_text(encoding="utf-8")
    except OSError:
        return ""
    if not text.startswith("---\n"):
        return ""
    parts = text.split("\n---\n", 1)
    if len(parts) != 2:
        return ""
    for line in parts[0][4:].splitlines():
        stripped = line.strip()
        if stripped.startswith("description:"):
            _, val = stripped.split(":", 1)
            return val.strip().strip('"').strip("'")
    return ""


def is_link_or_junction(path: Path) -> bool:
    if path.is_symlink():
        return True
    if os.name == "nt":
        try:
            st = os.lstat(path)
        except OSError:
            return False
        attrs = getattr(st, "st_file_attributes", 0)
        return bool(attrs & stat.FILE_ATTRIBUTE_REPARSE_POINT)
    return False


def read_link_target(path: Path) -> Path | None:
    if not is_link_or_junction(path):
        return None
    try:
        raw = os.readlink(path)
    except OSError:
        try:
            return path.resolve()
        except OSError:
            return None
    if os.name == "nt" and raw.startswith("\\\\?\\"):
        raw = raw[4:]
    target = Path(raw)
    if not target.is_absolute():
        target = (path.parent / target).resolve()
    return target


def create_dir_link(src: Path, dest: Path) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    if os.name == "nt":
        proc = subprocess.run(
            ["cmd", "/c", "mklink", "/J", str(dest), str(src)],
            capture_output=True,
            text=True,
        )
        if proc.returncode != 0:
            raise OSError(f"mklink /J failed: {(proc.stderr or proc.stdout).strip()}")
    else:
        os.symlink(src, dest, target_is_directory=True)


def remove_entry(path: Path) -> None:
    if is_link_or_junction(path):
        if os.name == "nt":
            os.rmdir(path)
        else:
            path.unlink()
    elif path.is_dir():
        shutil.rmtree(path)
    elif path.exists():
        path.unlink()


def read_managed_marker(path: Path) -> dict | None:
    marker = path / MANAGED_MARKER
    if not marker.is_file():
        return None
    try:
        data = json.loads(marker.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else None
    except (OSError, json.JSONDecodeError):
        return None


def is_managed_entry(path: Path, repo_root: Path = ROOT) -> bool:
    if not (path.exists() or is_link_or_junction(path)):
        return False
    if is_link_or_junction(path):
        target = read_link_target(path)
        if target is None:
            return False
        skills_root = (repo_root / "skills").resolve()
        try:
            target.resolve().relative_to(skills_root)
            return True
        except ValueError:
            return False
    data = read_managed_marker(path)
    return bool(data and data.get("managed_by") == MANAGED_BY)


def installed_entry_group(path: Path, repo_root: Path = ROOT) -> str | None:
    if is_link_or_junction(path):
        target = read_link_target(path)
        if target is None:
            return None
        skills_root = (repo_root / "skills").resolve()
        try:
            rel = target.resolve().relative_to(skills_root)
        except ValueError:
            return None
        if len(rel.parts) == 3 and rel.parts[0] in GROUPABLE_BUCKETS:
            return rel.parts[1]
        return None
    data = read_managed_marker(path)
    if data and data.get("managed_by") == MANAGED_BY:
        grp = data.get("group")
        return str(grp) if grp else None
    return None


def discover_skills(repo_root: Path = ROOT) -> dict[str, dict[str, SkillRecord]]:
    found: dict[str, dict[str, SkillRecord]] = {b: {} for b in ALL_BUCKETS}
    seen_global: dict[str, str] = {}

    def register(rec: SkillRecord) -> None:
        if rec.name in seen_global:
            raise ValueError(
                f"Duplicate skill name '{rec.name}' found in '{rec.source_label}' and '{seen_global[rec.name]}'."
            )
        seen_global[rec.name] = rec.source_label
        found[rec.bucket][rec.name] = rec

    for bucket in ALL_BUCKETS:
        bdir = repo_root / "skills" / bucket
        if not bdir.is_dir():
            continue
        for child in sorted(bdir.iterdir()):
            if not child.is_dir() or child.name.startswith("."):
                continue
            skill_md = child / "SKILL.md"
            if skill_md.is_file():
                register(
                    SkillRecord(
                        bucket=bucket,
                        group=None,
                        name=child.name,
                        path=child.resolve(),
                        description=read_skill_description(skill_md),
                    )
                )
            elif bucket in GROUPABLE_BUCKETS:
                for sub in sorted(child.iterdir()):
                    if not sub.is_dir() or sub.name.startswith("."):
                        continue
                    sub_md = sub / "SKILL.md"
                    if sub_md.is_file():
                        register(
                            SkillRecord(
                                bucket=bucket,
                                group=child.name,
                                name=sub.name,
                                path=sub.resolve(),
                                description=read_skill_description(sub_md),
                            )
                        )
    return found


def available_groups(
    all_skills: dict[str, dict[str, SkillRecord]],
    buckets: tuple[str, ...] = GROUPABLE_BUCKETS,
) -> dict[str, list[SkillRecord]]:
    grouped: dict[str, list[SkillRecord]] = {}
    for bucket in buckets:
        for rec in all_skills.get(bucket, {}).values():
            if rec.group:
                grouped.setdefault(rec.group, []).append(rec)
    for grp in grouped:
        grouped[grp].sort(key=lambda r: (r.bucket, r.name))
    return dict(sorted(grouped.items()))


def parse_csv(raw: str | None) -> list[str]:
    if not raw:
        return []
    return [item.strip() for item in raw.split(",") if item.strip()]


def resolve_harnesses(raw: str | None, default_harnesses: tuple[str, ...]) -> list[str]:
    names = parse_csv(raw) if raw else list(default_harnesses)
    valid = set(HARNESS_WORKSPACE_REL.keys())
    for name in names:
        if name not in valid:
            raise ValueError(f"Unknown harness '{name}'. Valid choices: {', '.join(sorted(valid))}")
    return names


def resolve_target_dirs(
    workspace: str | None,
    use_global: bool,
    dest: str | None,
    harnesses: list[str],
    home: Path | None = None,
) -> list[Path]:
    selected = sum(bool(x) for x in (workspace, use_global, dest))
    if selected != 1:
        raise ValueError("Specify exactly one target: --workspace <dir>, --global, or --dest <dir>.")

    dirs: list[Path] = []
    if dest:
        dirs.append(Path(dest).expanduser().resolve())
    elif workspace:
        ws = Path(workspace).expanduser().resolve()
        for h in harnesses:
            dirs.append((ws / HARNESS_WORKSPACE_REL[h]).resolve())
    else:
        for h in harnesses:
            dirs.append(harness_global_dir(h, home=home).resolve())

    deduped: list[Path] = []
    seen: set[Path] = set()
    for d in dirs:
        if d not in seen:
            seen.add(d)
            deduped.append(d)
    return deduped


def select_skills(
    all_skills: dict[str, dict[str, SkillRecord]],
    bucket: str | None,
    skill_names: list[str],
    allow_in_progress: bool,
    use_global: bool,
    groups: list[str] | None = None,
) -> list[SkillRecord]:
    group_names = groups or []
    if not bucket and not skill_names and not group_names:
        raise ValueError(
            "Specify --bucket <meta|custom|external|promoted|in-progress>, --group <g1,g2>, and/or --skills <s1,s2>."
        )

    if use_global and allow_in_progress:
        raise ValueError("--allow-in-progress cannot be combined with --global.")
    if use_global and bucket == "in-progress":
        raise ValueError("in-progress skills cannot be installed globally.")

    selected: list[SkillRecord] = []
    seen: set[str] = set()

    if group_names:
        if bucket:
            if bucket not in GROUPABLE_BUCKETS:
                raise ValueError(
                    f"--group can only be combined with --bucket custom or --bucket external (got '--bucket {bucket}')."
                )
            scope_buckets = (bucket,)
        else:
            scope_buckets = GROUPABLE_BUCKETS

        by_group = available_groups(all_skills, buckets=scope_buckets)
        for grp in group_names:
            if grp not in by_group:
                known = ", ".join(by_group.keys()) if by_group else "(none)"
                scope_label = "/".join(scope_buckets)
                raise ValueError(f"Group '{grp}' not found in skills/{scope_label}/. Available groups: {known}")
            for rec in by_group[grp]:
                if rec.name not in seen:
                    seen.add(rec.name)
                    selected.append(rec)
    elif bucket:
        if bucket == "promoted":
            buckets_to_read = list(PROMOTED_BUCKETS)
        elif bucket == "in-progress":
            if not allow_in_progress:
                raise ValueError("Installing in-progress skills requires --allow-in-progress.")
            buckets_to_read = ["in-progress"]
        elif bucket in DEPLOYABLE_BUCKETS:
            buckets_to_read = [bucket]
        else:
            raise ValueError(f"Unsupported bucket '{bucket}'.")

        for b in buckets_to_read:
            for name in sorted(all_skills[b].keys()):
                if name not in seen:
                    seen.add(name)
                    selected.append(all_skills[b][name])

    for name in skill_names:
        if name in seen:
            continue
        match: SkillRecord | None = None
        for b in DEPLOYABLE_BUCKETS:
            if name in all_skills[b]:
                match = all_skills[b][name]
                break
        if match is None and name in all_skills["in-progress"]:
            if use_global:
                raise ValueError(f"Skill '{name}' is in-progress and cannot be installed globally.")
            if not allow_in_progress:
                raise ValueError(
                    f"Skill '{name}' is in skills/in-progress/. Pass --allow-in-progress to test it in a workspace."
                )
            match = all_skills["in-progress"][name]
        if match is None and name in all_skills["deprecated"]:
            raise ValueError(f"Skill '{name}' is deprecated and cannot be installed.")
        if match is None:
            raise ValueError(f"Skill '{name}' not found in skills/.")
        seen.add(name)
        selected.append(match)

    return selected


def install_one(
    bucket: str,
    name: str,
    src: Path,
    target_dir: Path,
    mode: str,
    force: bool,
    dry_run: bool,
    repo_root: Path = ROOT,
    group: str | None = None,
) -> str:
    dest = target_dir / name
    exists = dest.exists() or is_link_or_junction(dest)
    if exists:
        if not is_managed_entry(dest, repo_root=repo_root) and not force:
            raise FileExistsError(
                f"Refusing to overwrite unmanaged skill directory: {dest} (pass --force to override)"
            )
        if not dry_run:
            remove_entry(dest)

    source_label = f"{bucket}/{group}/{name}" if group else f"{bucket}/{name}"
    action = f"{'[DRY-RUN] ' if dry_run else ''}{mode}: {source_label} -> {dest}"
    if dry_run:
        return action

    target_dir.mkdir(parents=True, exist_ok=True)
    if mode == "link":
        create_dir_link(src, dest)
    elif mode == "copy":
        shutil.copytree(src, dest, ignore=shutil.ignore_patterns("__pycache__", "*.pyc", ".DS_Store"))
        marker_data = {
            "managed_by": MANAGED_BY,
            "source_repo": str(repo_root.resolve()),
            "bucket": bucket,
            "group": group,
            "skill": name,
            "mode": "copy",
            "installed_at": dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        }
        (dest / MANAGED_MARKER).write_text(json.dumps(marker_data, indent=2) + "\n", encoding="utf-8")
    else:
        raise ValueError(f"Unknown mode '{mode}'.")
    return action


def cmd_list(args: argparse.Namespace) -> int:
    all_skills = discover_skills()
    describe = bool(getattr(args, "describe", False))

    def emit_section(header: str, records: list[SkillRecord]) -> None:
        if not records:
            print(f"{header}: (none)")
            return
        if not describe:
            names = ", ".join(r.name for r in records)
            print(f"{header}: {names}")
        else:
            print(f"{header}:")
            for rec in records:
                desc = rec.description or "(no description)"
                print(f"  - {rec.name}: {desc}")

    for bucket in ALL_BUCKETS:
        records = sorted(all_skills[bucket].values(), key=lambda r: r.name)
        if bucket not in GROUPABLE_BUCKETS:
            emit_section(bucket, records)
            continue

        standalone = [r for r in records if r.group is None]
        grouped = available_groups(all_skills, buckets=(bucket,))
        if not standalone and not grouped:
            print(f"{bucket}: (none)")
            continue
        if standalone:
            emit_section(f"{bucket} (standalone)", standalone)
        for grp, grp_records in grouped.items():
            emit_section(f"{bucket}/{grp}", grp_records)
    return 0


def cmd_mount_local(args: argparse.Namespace) -> int:
    all_skills = discover_skills()
    harnesses = resolve_harnesses(args.harness, ("agents",))
    target_dirs = resolve_target_dirs(
        workspace=str(ROOT),
        use_global=False,
        dest=None,
        harnesses=harnesses,
    )
    selected = sorted(all_skills["meta"].values(), key=lambda r: r.name)
    for target_dir in target_dirs:
        if target_dir.is_dir():
            for child in sorted(target_dir.iterdir()):
                if is_managed_entry(child) and child.name not in all_skills["meta"]:
                    print(f"{'[DRY-RUN] ' if args.dry_run else ''}prune stale: {child}")
                    if not args.dry_run:
                        remove_entry(child)
        for rec in selected:
            msg = install_one(
                bucket=rec.bucket,
                name=rec.name,
                src=rec.path,
                target_dir=target_dir,
                mode=args.mode,
                force=args.force,
                dry_run=args.dry_run,
                group=rec.group,
            )
            print(msg)
    return 0


def cmd_install(args: argparse.Namespace) -> int:
    all_skills = discover_skills()
    default_harnesses = DEFAULT_GLOBAL_HARNESSES if args.use_global else ("agents",)
    harnesses = resolve_harnesses(args.harness, default_harnesses)
    target_dirs = resolve_target_dirs(
        workspace=args.workspace,
        use_global=args.use_global,
        dest=args.dest,
        harnesses=harnesses,
    )
    skill_names = parse_csv(args.skills)
    group_names = parse_csv(args.group)
    selected = select_skills(
        all_skills=all_skills,
        bucket=args.bucket,
        groups=group_names,
        skill_names=skill_names,
        allow_in_progress=args.allow_in_progress,
        use_global=args.use_global,
    )
    if not selected:
        print("No skills matched the requested bucket/group/filter.")
        return 0

    mode = args.mode or ("link" if args.use_global else "copy")
    for target_dir in target_dirs:
        for rec in selected:
            msg = install_one(
                bucket=rec.bucket,
                name=rec.name,
                src=rec.path,
                target_dir=target_dir,
                mode=mode,
                force=args.force,
                dry_run=args.dry_run,
                group=rec.group,
            )
            print(msg)
    return 0


def cmd_uninstall(args: argparse.Namespace) -> int:
    workspace = str(ROOT) if args.local else args.workspace
    default_harnesses = DEFAULT_GLOBAL_HARNESSES if args.use_global else ("agents",)
    harnesses = resolve_harnesses(args.harness, default_harnesses)
    target_dirs = resolve_target_dirs(
        workspace=workspace,
        use_global=args.use_global,
        dest=args.dest,
        harnesses=harnesses,
    )
    skill_names = set(parse_csv(args.skills))
    group_names = set(parse_csv(args.group))
    if not args.all_managed and not skill_names and not group_names:
        raise ValueError("Specify --skills <name1,name2>, --group <g1,g2>, or --all to uninstall.")

    if group_names:
        all_skills = discover_skills()
        by_group = available_groups(all_skills)
        for grp in group_names:
            for rec in by_group.get(grp, []):
                skill_names.add(rec.name)

    removed = 0
    for target_dir in target_dirs:
        if not target_dir.is_dir():
            continue
        for child in sorted(target_dir.iterdir()):
            if not args.all_managed:
                matches_name = child.name in skill_names
                matches_group = bool(group_names) and (installed_entry_group(child) in group_names)
                if not (matches_name or matches_group):
                    continue
            if not is_managed_entry(child):
                if (skill_names or group_names) and args.force:
                    pass
                else:
                    if skill_names or group_names:
                        print(f"skip unmanaged (use --force to remove): {child}")
                    continue
            print(f"{'[DRY-RUN] ' if args.dry_run else ''}remove: {child}")
            if not args.dry_run:
                remove_entry(child)
            removed += 1
    if removed == 0:
        print("No matching managed skills found to remove.")
    return 0


def cmd_self_test(_args: argparse.Namespace) -> int:
    with tempfile.TemporaryDirectory(prefix="install_skills_selftest_") as tmp:
        tmp_path = Path(tmp)
        fake_ws = tmp_path / "sample-project"
        fake_ws.mkdir()
        fake_home = tmp_path / "fake-home"
        fake_home.mkdir()

        # Build an isolated fake repo with meta, custom (standalone + grouped), external (standalone + grouped), and in-progress
        fake_repo = tmp_path / "forge"
        for b in ALL_BUCKETS:
            (fake_repo / "skills" / b).mkdir(parents=True)
        meta_skill = fake_repo / "skills" / "meta" / "alpha-meta"
        meta_skill.mkdir()
        (meta_skill / "SKILL.md").write_text("---\nname: alpha-meta\ndescription: Meta test.\n---\n", encoding="utf-8")

        solo_custom = fake_repo / "skills" / "custom" / "solo-custom"
        solo_custom.mkdir()
        (solo_custom / "SKILL.md").write_text(
            "---\nname: solo-custom\ndescription: Standalone custom test.\n---\n", encoding="utf-8"
        )

        kb_a = fake_repo / "skills" / "custom" / "kb-skills" / "gamma-kb"
        kb_a.mkdir(parents=True)
        (kb_a / "SKILL.md").write_text("---\nname: gamma-kb\ndescription: KB skill A.\n---\n", encoding="utf-8")

        kb_b = fake_repo / "skills" / "custom" / "kb-skills" / "delta-kb"
        kb_b.mkdir(parents=True)
        (kb_b / "SKILL.md").write_text("---\nname: delta-kb\ndescription: KB skill B.\n---\n", encoding="utf-8")

        ext_kb = fake_repo / "skills" / "external" / "kb-skills" / "ext-pdf"
        ext_kb.mkdir(parents=True)
        (ext_kb / "SKILL.md").write_text("---\nname: ext-pdf\ndescription: External KB companion.\n---\n", encoding="utf-8")

        ext_solo = fake_repo / "skills" / "external" / "ext-solo"
        ext_solo.mkdir(parents=True)
        (ext_solo / "SKILL.md").write_text("---\nname: ext-solo\ndescription: External solo.\n---\n", encoding="utf-8")

        beta_skill = fake_repo / "skills" / "in-progress" / "beta-draft"
        beta_skill.mkdir()
        (beta_skill / "SKILL.md").write_text("---\nname: beta-draft\ndescription: Draft test.\n---\n", encoding="utf-8")

        all_skills = discover_skills(fake_repo)
        assert "alpha-meta" in all_skills["meta"]
        assert "solo-custom" in all_skills["custom"] and all_skills["custom"]["solo-custom"].group is None
        assert "gamma-kb" in all_skills["custom"] and all_skills["custom"]["gamma-kb"].group == "kb-skills"
        assert "ext-pdf" in all_skills["external"] and all_skills["external"]["ext-pdf"].group == "kb-skills"
        assert "ext-solo" in all_skills["external"] and all_skills["external"]["ext-solo"].group is None

        # 1. Deduplication for agents + antigravity on same workspace
        ws_dirs = resolve_target_dirs(str(fake_ws), False, None, ["agents", "antigravity"])
        assert len(ws_dirs) == 1 and ws_dirs[0] == (fake_ws / ".agents" / "skills").resolve()

        # 2. Global target resolution
        g_dirs = resolve_target_dirs(None, True, None, list(DEFAULT_GLOBAL_HARNESSES), home=fake_home)
        assert len(g_dirs) == 3

        # 3. Logical group union across custom + external, plus bucket-scoped group filters
        grp_all = select_skills(
            all_skills, bucket=None, groups=["kb-skills"], skill_names=[], allow_in_progress=False, use_global=False
        )
        assert [r.name for r in grp_all] == ["delta-kb", "gamma-kb", "ext-pdf"]

        grp_custom = select_skills(
            all_skills, bucket="custom", groups=["kb-skills"], skill_names=[], allow_in_progress=False, use_global=False
        )
        assert [r.name for r in grp_custom] == ["delta-kb", "gamma-kb"]

        grp_external = select_skills(
            all_skills, bucket="external", groups=["kb-skills"], skill_names=[], allow_in_progress=False, use_global=False
        )
        assert [r.name for r in grp_external] == ["ext-pdf"]

        # --bucket promoted must exclude external skills
        promoted = select_skills(
            all_skills, bucket="promoted", groups=[], skill_names=[], allow_in_progress=False, use_global=False
        )
        assert "ext-pdf" not in {r.name for r in promoted}
        assert "ext-solo" not in {r.name for r in promoted}

        # Reject unknown group or invalid bucket+group combination
        for bad_kwargs in (
            {"bucket": None, "groups": ["missing-group"], "skill_names": [], "allow_in_progress": False, "use_global": False},
            {"bucket": "meta", "groups": ["kb-skills"], "skill_names": [], "allow_in_progress": False, "use_global": False},
        ):
            try:
                select_skills(all_skills, **bad_kwargs)
                raise AssertionError(f"Expected ValueError for {bad_kwargs}")
            except ValueError:
                pass

        # 4. Flattened copy install + unmanaged protection
        target_dir = ws_dirs[0]
        unmanaged = target_dir / "find-skills"
        unmanaged.mkdir(parents=True)
        (unmanaged / "SKILL.md").write_text("unmanaged\n", encoding="utf-8")

        for rec in grp_all:
            install_one(
                rec.bucket, rec.name, rec.path, target_dir, "copy", False, False, repo_root=fake_repo, group=rec.group
            )
        assert (target_dir / "gamma-kb" / "SKILL.md").is_file()
        assert (target_dir / "ext-pdf" / "SKILL.md").is_file()
        assert not (target_dir / "kb-skills").exists(), "Grouped skills must be flattened at install target"
        assert is_managed_entry(target_dir / "ext-pdf", repo_root=fake_repo)
        assert installed_entry_group(target_dir / "ext-pdf", repo_root=fake_repo) == "kb-skills"
        assert not is_managed_entry(unmanaged, repo_root=fake_repo)

        # Dry-run should not write
        install_one("in-progress", "beta-draft", beta_skill, target_dir, "copy", False, True, repo_root=fake_repo)
        assert not (target_dir / "beta-draft").exists()

        # Refuse to overwrite unmanaged skill
        try:
            install_one("meta", "find-skills", meta_skill, target_dir, "copy", False, False, repo_root=fake_repo)
            raise AssertionError("Expected FileExistsError for unmanaged directory")
        except FileExistsError:
            pass

        # 5. Link mode (NTFS junction on Windows, symlink on Unix) for external grouped skill & safe removal
        link_target_dir = fake_ws / ".claude" / "skills"
        install_one(
            "external", "ext-pdf", ext_kb, link_target_dir, "link", False, False, repo_root=fake_repo, group="kb-skills"
        )
        linked = link_target_dir / "ext-pdf"
        assert is_link_or_junction(linked)
        assert (linked / "SKILL.md").is_file()
        assert is_managed_entry(linked, repo_root=fake_repo)
        assert installed_entry_group(linked, repo_root=fake_repo) == "kb-skills"
        remove_entry(linked)
        assert not linked.exists()
        assert (ext_kb / "SKILL.md").is_file(), "Removing link must never delete source skill"

        # 6. in-progress guard checks
        for kwargs in (
            {"bucket": "in-progress", "skill_names": [], "allow_in_progress": False, "use_global": False},
            {"bucket": None, "skill_names": ["beta-draft"], "allow_in_progress": False, "use_global": False},
            {"bucket": None, "skill_names": ["beta-draft"], "allow_in_progress": True, "use_global": True},
        ):
            try:
                select_skills(all_skills, **kwargs)
                raise AssertionError(f"Expected ValueError for {kwargs}")
            except ValueError:
                pass

        allowed = select_skills(all_skills, None, ["beta-draft"], allow_in_progress=True, use_global=False)
        assert len(allowed) == 1 and allowed[0].name == "beta-draft"

        # 7. Duplicate skill name across custom and external must fail discovery
        dup_skill = fake_repo / "skills" / "external" / "other-group" / "gamma-kb"
        dup_skill.mkdir(parents=True)
        (dup_skill / "SKILL.md").write_text("---\nname: gamma-kb\ndescription: Dup.\n---\n", encoding="utf-8")
        try:
            discover_skills(fake_repo)
            raise AssertionError("Expected ValueError for duplicate skill name across custom and external")
        except ValueError:
            pass

    print("install_skills self-test PASSED.")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Cross-platform skill installer for agent-skills forge")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_list = sub.add_parser("list", help="List available skills by bucket and domain group")
    p_list.add_argument("--describe", action="store_true", help="Include 1-line frontmatter descriptions")
    p_list.set_defaults(func=cmd_list)

    p_mount = sub.add_parser("mount-local", help="Mount this repo's meta-skills into local .agents/skills")
    p_mount.add_argument("--harness", default="agents", help="Comma-separated harnesses (default: agents)")
    p_mount.add_argument("--mode", choices=("link", "copy"), default="link", help="link (default) or copy")
    p_mount.add_argument("--force", action="store_true", help="Overwrite unmanaged skill directories")
    p_mount.add_argument("--dry-run", action="store_true", help="Print planned actions without writing")
    p_mount.set_defaults(func=cmd_mount_local)

    p_inst = sub.add_parser("install", help="Install skills or groups into a workspace, global dir, or custom dest")
    p_inst.add_argument(
        "--bucket",
        choices=("meta", "custom", "external", "promoted", "in-progress"),
        default=None,
        help="Install a bucket (combine custom/external with --group to scope that group to one bucket)",
    )
    p_inst.add_argument(
        "--group",
        default=None,
        help="Comma-separated domain group names (spans custom + external unless scoped by --bucket)",
    )
    p_inst.add_argument("--skills", default=None, help="Comma-separated skill names to install")
    p_inst.add_argument("--workspace", default=None, help="Target project workspace root")
    p_inst.add_argument("--global", dest="use_global", action="store_true", help="Install to global harness dirs")
    p_inst.add_argument("--dest", default=None, help="Exact destination skills directory")
    p_inst.add_argument("--harness", default=None, help="Comma-separated harnesses: agents,claude,antigravity,cursor")
    p_inst.add_argument(
        "--mode",
        choices=("link", "copy"),
        default=None,
        help="Default: copy for --workspace/--dest, link for --global",
    )
    p_inst.add_argument(
        "--allow-in-progress",
        action="store_true",
        help="Allow installing skills/in-progress/ into a workspace (never allowed with --global)",
    )
    p_inst.add_argument("--force", action="store_true", help="Overwrite unmanaged skill directories")
    p_inst.add_argument("--dry-run", action="store_true", help="Print planned actions without writing")
    p_inst.set_defaults(func=cmd_install)

    p_uninst = sub.add_parser("uninstall", help="Remove forge-managed skills from a target")
    p_uninst.add_argument("--local", action="store_true", help="Target this repo's local harness directory")
    p_uninst.add_argument("--workspace", default=None, help="Target project workspace root")
    p_uninst.add_argument("--global", dest="use_global", action="store_true", help="Target global harness dirs")
    p_uninst.add_argument("--dest", default=None, help="Exact destination skills directory")
    p_uninst.add_argument("--harness", default=None, help="Comma-separated harnesses")
    p_uninst.add_argument("--group", default=None, help="Comma-separated domain group names to remove")
    p_uninst.add_argument("--skills", default=None, help="Comma-separated skill names to remove")
    p_uninst.add_argument("--all", dest="all_managed", action="store_true", help="Remove all forge-managed skills")
    p_uninst.add_argument("--force", action="store_true", help="Also allow removing named unmanaged directories")
    p_uninst.add_argument("--dry-run", action="store_true", help="Print planned removals without deleting")
    p_uninst.set_defaults(func=cmd_uninstall)

    p_self = sub.add_parser("self-test", help="Run isolated smoke tests for link, copy, groups, guards, and uninstall")
    p_self.set_defaults(func=cmd_self_test)

    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    try:
        return args.func(args)
    except (ValueError, FileExistsError, OSError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
