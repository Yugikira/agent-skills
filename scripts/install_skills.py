#!/usr/bin/env python3
"""Cross-platform skill deployment tool for the agent-skills forge.

Replaces bash symlink scripts with safe, opt-in workspace or global installation
using native directory junctions on Windows (no admin required), symlinks on Unix,
or provenance-tracked copies.

Subcommands:
  list         Show available skills grouped by bucket.
  mount-local  Link this repo's meta-skills into local .agents/skills (gitignored).
  install      Deploy selected skills to a workspace, global harness dir, or custom dest.
  uninstall    Safely remove forge-managed skills without touching unmanaged ones.
  self-test    Run an isolated temp-directory smoke test of all modes and guards.
"""

from __future__ import annotations

import argparse
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
ALL_BUCKETS = ("meta", "custom", "in-progress", "deprecated")
MANAGED_MARKER = ".forge-managed.json"
MANAGED_BY = "agent-skills-forge"

HARNESS_WORKSPACE_REL = {
    "agents": Path(".agents") / "skills",
    "claude": Path(".claude") / "skills",
    "antigravity": Path(".agents") / "skills",
    "cursor": Path(".cursor") / "skills",
}

DEFAULT_GLOBAL_HARNESSES = ("agents", "claude", "antigravity")


def harness_global_dir(harness: str, home: Path | None = None) -> Path:
    base = home or Path.home()
    mapping = {
        "agents": base / ".agents" / "skills",
        "claude": base / ".claude" / "skills",
        "antigravity": base / ".gemini" / "config" / "skills",
        "cursor": base / ".cursor" / "skills",
    }
    return mapping[harness]


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
    marker = path / MANAGED_MARKER
    if marker.is_file():
        try:
            data = json.loads(marker.read_text(encoding="utf-8"))
            return data.get("managed_by") == MANAGED_BY
        except (OSError, json.JSONDecodeError):
            return False
    return False


def discover_skills(repo_root: Path = ROOT) -> dict[str, dict[str, Path]]:
    found: dict[str, dict[str, Path]] = {b: {} for b in ALL_BUCKETS}
    for bucket in ALL_BUCKETS:
        bdir = repo_root / "skills" / bucket
        if not bdir.is_dir():
            continue
        for child in sorted(bdir.iterdir()):
            if child.is_dir() and (child / "SKILL.md").is_file():
                found[bucket][child.name] = child.resolve()
    return found


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
    all_skills: dict[str, dict[str, Path]],
    bucket: str | None,
    skill_names: list[str],
    allow_in_progress: bool,
    use_global: bool,
) -> list[tuple[str, str, Path]]:
    if not bucket and not skill_names:
        raise ValueError("Specify --bucket <meta|custom|promoted|in-progress> and/or --skills <name1,name2>.")

    if use_global and allow_in_progress:
        raise ValueError("--allow-in-progress cannot be combined with --global.")
    if use_global and bucket == "in-progress":
        raise ValueError("in-progress skills cannot be installed globally.")

    selected: list[tuple[str, str, Path]] = []
    seen: set[str] = set()

    if bucket:
        if bucket == "promoted":
            buckets_to_read = list(PROMOTED_BUCKETS)
        elif bucket == "in-progress":
            if not allow_in_progress:
                raise ValueError("Installing in-progress skills requires --allow-in-progress.")
            buckets_to_read = ["in-progress"]
        elif bucket in PROMOTED_BUCKETS:
            buckets_to_read = [bucket]
        else:
            raise ValueError(f"Unsupported bucket '{bucket}'.")

        for b in buckets_to_read:
            for name, path in all_skills[b].items():
                if name not in seen:
                    seen.add(name)
                    selected.append((b, name, path))

    for name in skill_names:
        if name in seen:
            continue
        match: tuple[str, Path] | None = None
        for b in PROMOTED_BUCKETS:
            if name in all_skills[b]:
                match = (b, all_skills[b][name])
                break
        if match is None and name in all_skills["in-progress"]:
            if use_global:
                raise ValueError(f"Skill '{name}' is in-progress and cannot be installed globally.")
            if not allow_in_progress:
                raise ValueError(
                    f"Skill '{name}' is in skills/in-progress/. Pass --allow-in-progress to test it in a workspace."
                )
            match = ("in-progress", all_skills["in-progress"][name])
        if match is None and name in all_skills["deprecated"]:
            raise ValueError(f"Skill '{name}' is deprecated and cannot be installed.")
        if match is None:
            raise ValueError(f"Skill '{name}' not found in skills/.")
        seen.add(name)
        selected.append((match[0], name, match[1]))

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

    action = f"{'[DRY-RUN] ' if dry_run else ''}{mode}: {bucket}/{name} -> {dest}"
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
            "skill": name,
            "mode": "copy",
            "installed_at": dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        }
        (dest / MANAGED_MARKER).write_text(json.dumps(marker_data, indent=2) + "\n", encoding="utf-8")
    else:
        raise ValueError(f"Unknown mode '{mode}'.")
    return action


def cmd_list(_args: argparse.Namespace) -> int:
    all_skills = discover_skills()
    for bucket in ALL_BUCKETS:
        names = sorted(all_skills[bucket].keys())
        label = ", ".join(names) if names else "(none)"
        print(f"{bucket}: {label}")
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
    selected = [( "meta", name, path) for name, path in all_skills["meta"].items()]
    for target_dir in target_dirs:
        if target_dir.is_dir():
            for child in sorted(target_dir.iterdir()):
                if is_managed_entry(child) and child.name not in all_skills["meta"]:
                    print(f"{'[DRY-RUN] ' if args.dry_run else ''}prune stale: {child}")
                    if not args.dry_run:
                        remove_entry(child)
        for bucket, name, src in selected:
            msg = install_one(
                bucket=bucket,
                name=name,
                src=src,
                target_dir=target_dir,
                mode=args.mode,
                force=args.force,
                dry_run=args.dry_run,
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
    selected = select_skills(
        all_skills=all_skills,
        bucket=args.bucket,
        skill_names=skill_names,
        allow_in_progress=args.allow_in_progress,
        use_global=args.use_global,
    )
    if not selected:
        print("No skills matched the requested bucket/filter.")
        return 0

    mode = args.mode or ("link" if args.use_global else "copy")
    for target_dir in target_dirs:
        for bucket, name, src in selected:
            msg = install_one(
                bucket=bucket,
                name=name,
                src=src,
                target_dir=target_dir,
                mode=mode,
                force=args.force,
                dry_run=args.dry_run,
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
    if not args.all_managed and not skill_names:
        raise ValueError("Specify --skills <name1,name2> or --all to uninstall.")

    removed = 0
    for target_dir in target_dirs:
        if not target_dir.is_dir():
            continue
        for child in sorted(target_dir.iterdir()):
            if skill_names and child.name not in skill_names:
                continue
            if not is_managed_entry(child):
                if skill_names and args.force:
                    pass
                else:
                    if skill_names:
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

        # Build an isolated fake repo with 1 meta skill and 1 in-progress skill
        fake_repo = tmp_path / "forge"
        for b in ALL_BUCKETS:
            (fake_repo / "skills" / b).mkdir(parents=True)
        meta_skill = fake_repo / "skills" / "meta" / "alpha-meta"
        meta_skill.mkdir()
        (meta_skill / "SKILL.md").write_text("---\nname: alpha-meta\ndescription: Meta test.\n---\n", encoding="utf-8")
        beta_skill = fake_repo / "skills" / "in-progress" / "beta-draft"
        beta_skill.mkdir()
        (beta_skill / "SKILL.md").write_text("---\nname: beta-draft\ndescription: Draft test.\n---\n", encoding="utf-8")

        all_skills = discover_skills(fake_repo)
        assert "alpha-meta" in all_skills["meta"]
        assert "beta-draft" in all_skills["in-progress"]

        # 1. Deduplication for agents + antigravity on same workspace
        ws_dirs = resolve_target_dirs(str(fake_ws), False, None, ["agents", "antigravity"])
        assert len(ws_dirs) == 1 and ws_dirs[0] == (fake_ws / ".agents" / "skills").resolve()

        # 2. Global target resolution
        g_dirs = resolve_target_dirs(None, True, None, list(DEFAULT_GLOBAL_HARNESSES), home=fake_home)
        assert len(g_dirs) == 3

        # 3. Copy mode + unmanaged protection
        target_dir = ws_dirs[0]
        unmanaged = target_dir / "find-skills"
        unmanaged.mkdir(parents=True)
        (unmanaged / "SKILL.md").write_text("unmanaged\n", encoding="utf-8")

        install_one("meta", "alpha-meta", meta_skill, target_dir, "copy", False, False, repo_root=fake_repo)
        assert (target_dir / "alpha-meta" / "SKILL.md").is_file()
        assert is_managed_entry(target_dir / "alpha-meta", repo_root=fake_repo)
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

        # 4. Link mode (NTFS junction on Windows, symlink on Unix) & safe removal
        link_target_dir = fake_ws / ".claude" / "skills"
        install_one("meta", "alpha-meta", meta_skill, link_target_dir, "link", False, False, repo_root=fake_repo)
        linked = link_target_dir / "alpha-meta"
        assert is_link_or_junction(linked)
        assert (linked / "SKILL.md").is_file()
        assert is_managed_entry(linked, repo_root=fake_repo)
        remove_entry(linked)
        assert not linked.exists()
        assert (meta_skill / "SKILL.md").is_file(), "Removing link must never delete source skill"

        # 5. in-progress guard checks
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
        assert len(allowed) == 1 and allowed[0][1] == "beta-draft"

    print("install_skills self-test PASSED.")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Cross-platform skill installer for agent-skills forge")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_list = sub.add_parser("list", help="List available skills by bucket")
    p_list.set_defaults(func=cmd_list)

    p_mount = sub.add_parser("mount-local", help="Mount this repo's meta-skills into local .agents/skills")
    p_mount.add_argument("--harness", default="agents", help="Comma-separated harnesses (default: agents)")
    p_mount.add_argument("--mode", choices=("link", "copy"), default="link", help="link (default) or copy")
    p_mount.add_argument("--force", action="store_true", help="Overwrite unmanaged skill directories")
    p_mount.add_argument("--dry-run", action="store_true", help="Print planned actions without writing")
    p_mount.set_defaults(func=cmd_mount_local)

    p_inst = sub.add_parser("install", help="Install skills into a workspace, global harness dir, or custom dest")
    p_inst.add_argument("--bucket", choices=("meta", "custom", "promoted", "in-progress"), default=None)
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
    p_uninst.add_argument("--skills", default=None, help="Comma-separated skill names to remove")
    p_uninst.add_argument("--all", dest="all_managed", action="store_true", help="Remove all forge-managed skills")
    p_uninst.add_argument("--force", action="store_true", help="Also allow removing named unmanaged directories")
    p_uninst.add_argument("--dry-run", action="store_true", help="Print planned removals without deleting")
    p_uninst.set_defaults(func=cmd_uninstall)

    p_self = sub.add_parser("self-test", help="Run isolated smoke tests for link, copy, guards, and uninstall")
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
