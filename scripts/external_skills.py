#!/usr/bin/env python3
"""Vendored external/GitHub skill manager for the agent-skills forge.

Uses pure Python stdlib + git partial sparse-checkout (zero Node/npx dependency)
to fetch specific skill folders from GitHub or local git repos into
skills/external/[<group>/]<skill-name>/, pinned by commit SHA in
skills/external/manifest.json, with auto-synced docs/external/README.md.

Subcommands:
  add        Fetch and vendor a specific skill folder from GitHub (or git repo).
  list       Show all vendored external skills from skills/external/manifest.json.
  check      Check upstream refs via git ls-remote without cloning.
  update     Re-fetch one or all vendored skills from their tracked upstream ref.
  remove     Delete a vendored skill, update manifest.json, and refresh docs.
  self-test  Run an isolated offline smoke test against a local temp git repo.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import re
import shutil
import stat
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ALL_BUCKETS = ("meta", "custom", "external", "in-progress", "deprecated")
KEBAB_RE = re.compile(r"[a-z0-9]+(?:-[a-z0-9]+)*")
SHA_RE = re.compile(r"[0-9a-fA-F]{40}")
SCRIPT_EXTS = {".py", ".sh", ".bash", ".ps1", ".js", ".ts", ".mjs", ".cjs", ".rb", ".bat", ".cmd"}

DOCS_START_MARKER = "<!-- external-skills:start -->"
DOCS_END_MARKER = "<!-- external-skills:end -->"


def manifest_path(repo_root: Path = ROOT) -> Path:
    return repo_root / "skills" / "external" / "manifest.json"


def external_docs_path(repo_root: Path = ROOT) -> Path:
    return repo_root / "docs" / "external" / "README.md"


def rmtree_force(path: Path) -> None:
    if not path.exists():
        return

    def _handle_readonly(func, p, _exc_info):
        try:
            os.chmod(p, stat.S_IWRITE | stat.S_IREAD)
            func(p)
        except OSError:
            pass

    if sys.version_info >= (3, 12):
        shutil.rmtree(path, onexc=_handle_readonly)
    else:
        shutil.rmtree(path, onerror=_handle_readonly)


def run_git(args: list[str], cwd: Path | None = None, check: bool = True) -> subprocess.CompletedProcess[str]:
    proc = subprocess.run(
        ["git", *args],
        cwd=str(cwd) if cwd else None,
        capture_output=True,
        text=True,
    )
    if check and proc.returncode != 0:
        detail = (proc.stderr or proc.stdout).strip()
        raise RuntimeError(f"git {' '.join(args)} failed (exit {proc.returncode}): {detail}")
    return proc


def normalize_subpath(raw: str | None) -> str:
    if not raw:
        return "."
    cleaned = raw.replace("\\", "/").strip().strip("/")
    if not cleaned or cleaned == ".":
        return "."
    parts = [p for p in cleaned.split("/") if p]
    if any(p == ".." for p in parts):
        raise ValueError(f"Unsafe subpath '{raw}': parent traversal is not allowed.")
    return "/".join(parts)


def parse_source_spec(
    spec: str,
    ref_override: str | None = None,
    subpath_override: str | None = None,
) -> tuple[str, str | None, str]:
    """Parse a GitHub URL, shorthand, or local git repo path into (repo_url, ref, subpath)."""
    raw = spec.strip()
    repo_url: str
    ref: str | None = None
    subpath = "."

    # 1. Local directory or file:// URL (checked first to avoid Windows drive ':' confusion)
    is_win_drive = len(raw) >= 2 and raw[1] == ":" and raw[0].isalpha()
    if raw.startswith("file://") or is_win_drive or Path(raw).expanduser().exists():
        repo_url = raw if raw.startswith("file://") else str(Path(raw).expanduser().resolve())
    # 2. Full GitHub web URL
    elif re.match(r"^https?://github\.com/", raw, re.IGNORECASE):
        m_tree = re.match(
            r"^https?://github\.com/([^/]+)/([^/]+?)(?:\.git)?/(?:tree|blob)/([^/]+)(?:/(.*))?$",
            raw,
            re.IGNORECASE,
        )
        m_root = re.match(
            r"^https?://github\.com/([^/]+)/([^/]+?)(?:\.git)?/?$",
            raw,
            re.IGNORECASE,
        )
        if m_tree:
            owner, repo, parsed_ref, parsed_sub = m_tree.groups()
            repo_url = f"https://github.com/{owner}/{repo}.git"
            ref = parsed_ref
            subpath = normalize_subpath(parsed_sub)
        elif m_root:
            owner, repo = m_root.groups()
            repo_url = f"https://github.com/{owner}/{repo}.git"
        else:
            raise ValueError(f"Unrecognized GitHub URL format: '{raw}'")
    # 3. Any other git URL (https://, ssh://, git@)
    elif raw.startswith(("https://", "http://", "ssh://", "git@")):
        repo_url = raw
    # 4. Compact GitHub shorthand: owner/repo[:subpath][@ref]
    else:
        body = raw
        if "@" in body:
            body, ref = body.rsplit("@", 1)
        if ":" in body:
            repo_part, parsed_sub = body.split(":", 1)
            subpath = normalize_subpath(parsed_sub)
        else:
            repo_part = body
        m_short = re.fullmatch(r"([A-Za-z0-9_.-]+)/([A-Za-z0-9_.-]+?)(?:\.git)?", repo_part)
        if not m_short:
            raise ValueError(
                f"Cannot parse source spec '{raw}'. Use a GitHub URL, 'owner/repo:subpath@ref', or a local git repo path."
            )
        owner, repo = m_short.groups()
        repo_url = f"https://github.com/{owner}/{repo}.git"

    if ref_override is not None:
        ref = ref_override.strip() or None
    if subpath_override is not None:
        subpath = normalize_subpath(subpath_override)

    return repo_url, ref, subpath


def detect_default_branch(repo_url: str) -> str:
    proc = run_git(["ls-remote", "--symref", repo_url, "HEAD"], check=False)
    if proc.returncode == 0:
        for line in proc.stdout.splitlines():
            m = re.match(r"^ref:\s+refs/heads/(\S+)\s+HEAD$", line.strip())
            if m:
                return m.group(1)
    return "HEAD"


def resolve_remote_ref(repo_url: str, ref: str) -> str | None:
    if SHA_RE.fullmatch(ref):
        return ref.lower()
    if ref == "HEAD":
        candidates = ["HEAD"]
    elif ref.startswith("refs/"):
        candidates = [ref]
    else:
        candidates = [f"refs/heads/{ref}", f"refs/tags/{ref}"]
    proc = run_git(["ls-remote", repo_url, *candidates], check=False)
    if proc.returncode != 0:
        return None
    by_ref: dict[str, str] = {}
    for line in proc.stdout.splitlines():
        parts = line.strip().split()
        if len(parts) >= 2 and SHA_RE.fullmatch(parts[0]):
            by_ref[parts[1]] = parts[0].lower()
    for cand in candidates:
        if cand.startswith("refs/tags/") and f"{cand}^{{}}" in by_ref:
            return by_ref[f"{cand}^{{}}"]
        if cand in by_ref:
            return by_ref[cand]
    return None


def parse_frontmatter(skill_md: Path) -> tuple[dict[str, str], str]:
    text = skill_md.read_text(encoding="utf-8")
    if not text.startswith("---\n"):
        raise ValueError(f"{skill_md}: missing YAML frontmatter")
    parts = text.split("\n---\n", 1)
    if len(parts) != 2:
        raise ValueError(f"{skill_md}: unclosed YAML frontmatter")
    meta: dict[str, str] = {}
    for line in parts[0][4:].splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if ":" in stripped:
            key, val = stripped.split(":", 1)
            meta[key.strip()] = val.strip().strip('"').strip("'")
    return meta, parts[1]


def collect_existing_skill_names(repo_root: Path = ROOT) -> dict[str, tuple[str, str | None, Path]]:
    existing: dict[str, tuple[str, str | None, Path]] = {}
    for bucket in ALL_BUCKETS:
        bdir = repo_root / "skills" / bucket
        if not bdir.is_dir():
            continue
        for child in sorted(bdir.iterdir()):
            if not child.is_dir() or child.name.startswith("."):
                continue
            if (child / "SKILL.md").is_file():
                existing[child.name] = (bucket, None, child)
            elif bucket in ("custom", "external"):
                for sub in sorted(child.iterdir()):
                    if sub.is_dir() and not sub.name.startswith(".") and (sub / "SKILL.md").is_file():
                        existing[sub.name] = (bucket, child.name, sub)
    return existing


def load_manifest(repo_root: Path = ROOT) -> dict:
    mpath = manifest_path(repo_root)
    if not mpath.exists():
        return {"schema_version": 1, "skills": []}
    data = json.loads(mpath.read_text(encoding="utf-8"))
    if not isinstance(data, dict) or not isinstance(data.get("skills"), list):
        raise ValueError(f"Invalid manifest format in {mpath}")
    return data


def save_manifest(data: dict, repo_root: Path = ROOT) -> None:
    data["skills"] = sorted(data.get("skills", []), key=lambda e: (e.get("group") or "", e.get("name", "")))
    mpath = manifest_path(repo_root)
    mpath.parent.mkdir(parents=True, exist_ok=True)
    mpath.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")


def sanitize_doc_text(text: str) -> str:
    cleaned = text.replace("\u2014", " - ").replace("\r\n", " ").replace("\n", " ")
    return re.sub(r"\s+", " ", cleaned).strip()


def format_upstream_link(repo_url: str, commit: str, subpath: str) -> str:
    short_sha = commit[:10]
    m_gh = re.match(r"^https?://github\.com/([^/]+/[^/]+?)(?:\.git)?/?$", repo_url, re.IGNORECASE)
    if m_gh:
        base = f"https://github.com/{m_gh.group(1)}"
        url = f"{base}/tree/{commit}" if subpath == "." else f"{base}/tree/{commit}/{subpath}"
        return f"[upstream]({url}), `{short_sha}`"
    loc = repo_url if subpath == "." else f"{repo_url}:{subpath}"
    return f"`{loc}` @ `{short_sha}`"


def render_external_index(manifest: dict) -> str:
    entries = manifest.get("skills", [])
    if not entries:
        return (
            "No external skills vendored yet. Add one with "
            "`python3 scripts/external_skills.py add <github-url> [--group <group>]`."
        )

    grouped: dict[str, list[dict]] = {}
    standalone: list[dict] = []
    for entry in entries:
        grp = entry.get("group")
        if grp:
            grouped.setdefault(grp, []).append(entry)
        else:
            standalone.append(entry)

    lines: list[str] = []
    if grouped:
        lines.append("## Domain Groups")
        lines.append("")
        for grp in sorted(grouped.keys()):
            lines.append(f"### {grp}")
            lines.append("")
            for e in sorted(grouped[grp], key=lambda item: item["name"]):
                name = e["name"]
                skill_rel = f"../../skills/external/{grp}/{name}/SKILL.md"
                upstream = format_upstream_link(e["repo"], e["commit"], e["subpath"])
                summary = sanitize_doc_text(e.get("summary") or "(no summary)")
                lines.append(f"- [{name}]({skill_rel}) ({upstream}): {summary}")
            lines.append("")

    if standalone:
        lines.append("## Standalone External Skills")
        lines.append("")
        for e in sorted(standalone, key=lambda item: item["name"]):
            name = e["name"]
            skill_rel = f"../../skills/external/{name}/SKILL.md"
            upstream = format_upstream_link(e["repo"], e["commit"], e["subpath"])
            summary = sanitize_doc_text(e.get("summary") or "(no summary)")
            lines.append(f"- [{name}]({skill_rel}) ({upstream}): {summary}")
        lines.append("")

    return "\n".join(lines).rstrip()


def sync_external_docs(manifest: dict, repo_root: Path = ROOT) -> None:
    dpath = external_docs_path(repo_root)
    generated = render_external_index(manifest)
    block = f"{DOCS_START_MARKER}\n{generated}\n{DOCS_END_MARKER}"

    if dpath.exists():
        text = dpath.read_text(encoding="utf-8")
        if DOCS_START_MARKER in text and DOCS_END_MARKER in text:
            pre, rest = text.split(DOCS_START_MARKER, 1)
            _, post = rest.split(DOCS_END_MARKER, 1)
            dpath.write_text(f"{pre}{block}{post}", encoding="utf-8")
            return

    default_doc = (
        "# External Skills Documentation\n\n"
        "Curated third-party skills vendored from upstream Git repositories via `scripts/external_skills.py` "
        "and pinned in `skills/external/manifest.json`. External skills can share a logical `--group` name "
        "with `skills/custom/` for unified workspace deployment.\n\n"
        "```bash\n"
        "python3 scripts/install_skills.py install --bucket external --workspace /path/to/project\n"
        "python3 scripts/install_skills.py install --group <group> --workspace /path/to/project\n"
        "python3 scripts/external_skills.py check\n"
        "```\n\n"
        f"{block}\n"
    )
    dpath.parent.mkdir(parents=True, exist_ok=True)
    dpath.write_text(default_doc, encoding="utf-8")


def audit_skill_dir(skill_dir: Path, meta: dict[str, str]) -> dict:
    skill_md = skill_dir / "SKILL.md"
    line_count = len(skill_md.read_text(encoding="utf-8").splitlines())
    user_invoked = meta.get("disable-model-invocation", "").lower() == "true"
    scripts = sorted(
        str(p.relative_to(skill_dir)).replace("\\", "/")
        for p in skill_dir.rglob("*")
        if p.is_file() and p.suffix.lower() in SCRIPT_EXTS
    )
    return {
        "invocation": "user-invoked" if user_invoked else "model-invoked",
        "lines": line_count,
        "scripts": scripts,
    }


def print_audit(name: str, group: str | None, repo_url: str, subpath: str, ref: str, commit: str, audit: dict) -> None:
    loc = f"external/{group}/{name}" if group else f"external/{name}"
    print(f"Audit [{loc}]:")
    print(f"  source:     {repo_url} ({subpath} @ {ref} -> {commit[:12]})")
    inv = audit["invocation"]
    inv_note = " (adds description to always-on context load)" if inv == "model-invoked" else ""
    print(f"  invocation: {inv}{inv_note}")
    line_note = " (above 300-line local cap; allowed in external/)" if audit["lines"] > 300 else ""
    print(f"  SKILL.md:   {audit['lines']} lines{line_note}")
    if audit["scripts"]:
        print(f"  scripts:    {', '.join(audit['scripts'])}")
    else:
        print("  scripts:    (none)")


def fetch_skill_from_git(
    repo_url: str,
    ref: str | None,
    subpath: str,
    staging_dir: Path,
) -> tuple[Path, str, str]:
    """Sparse-checkout only the requested skill folder into staging_dir.

    Returns (fetched_skill_dir, resolved_ref, resolved_commit_sha).
    """
    resolved_ref = ref or detect_default_branch(repo_url)
    run_git(["init", "-q"], cwd=staging_dir)
    run_git(["remote", "add", "origin", repo_url], cwd=staging_dir)

    if subpath != ".":
        run_git(["sparse-checkout", "init", "--cone"], cwd=staging_dir)
        run_git(["sparse-checkout", "set", "--", subpath], cwd=staging_dir)

    # Prefer partial shallow fetch; gracefully fall back for local or older remotes
    fetched = run_git(["fetch", "--depth", "1", "--filter=blob:none", "origin", resolved_ref], cwd=staging_dir, check=False)
    if fetched.returncode != 0:
        fetched = run_git(["fetch", "--depth", "1", "origin", resolved_ref], cwd=staging_dir, check=False)
    if fetched.returncode != 0:
        run_git(["fetch", "origin", resolved_ref], cwd=staging_dir, check=True)

    run_git(["checkout", "-q", "FETCH_HEAD"], cwd=staging_dir)
    commit = run_git(["rev-parse", "HEAD"], cwd=staging_dir).stdout.strip().lower()

    src_dir = staging_dir if subpath == "." else (staging_dir / subpath)
    if not src_dir.is_dir():
        raise FileNotFoundError(f"Subpath '{subpath}' not found in {repo_url} @ {resolved_ref}")
    if not (src_dir / "SKILL.md").is_file():
        raise FileNotFoundError(f"No SKILL.md found inside '{subpath}' of {repo_url} @ {resolved_ref}")

    return src_dir, resolved_ref, commit


def copy_vendored_skill(src_dir: Path, dest_dir: Path) -> None:
    if dest_dir.exists():
        rmtree_force(dest_dir)
    dest_dir.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(
        src_dir,
        dest_dir,
        ignore=shutil.ignore_patterns(".git", "__pycache__", "*.pyc", ".DS_Store"),
    )


def add_external_skill(
    spec: str,
    group: str | None = None,
    ref_override: str | None = None,
    subpath_override: str | None = None,
    summary_override: str | None = None,
    force: bool = False,
    dry_run: bool = False,
    repo_root: Path = ROOT,
) -> dict:
    if group and not KEBAB_RE.fullmatch(group):
        raise ValueError(f"Group name '{group}' must be lowercase kebab-case.")

    repo_url, parsed_ref, subpath = parse_source_spec(spec, ref_override=ref_override, subpath_override=subpath_override)

    tmp_dir = Path(tempfile.mkdtemp(prefix="ext_skill_fetch_"))
    try:
        src_dir, resolved_ref, commit = fetch_skill_from_git(repo_url, parsed_ref, subpath, tmp_dir)
        meta, _ = parse_frontmatter(src_dir / "SKILL.md")
        name = meta.get("name", "").strip()
        desc = meta.get("description", "").strip()
        if not name:
            raise ValueError("Fetched SKILL.md is missing 'name' in YAML frontmatter.")
        if not KEBAB_RE.fullmatch(name):
            raise ValueError(f"Fetched skill name '{name}' must be lowercase kebab-case.")
        if not desc:
            raise ValueError(f"Fetched skill '{name}' has an empty description in YAML frontmatter.")

        existing = collect_existing_skill_names(repo_root)
        if name in existing:
            ex_bucket, ex_group, ex_path = existing[name]
            if ex_bucket != "external":
                raise ValueError(
                    f"Skill name '{name}' already exists in skills/{ex_bucket}/ ({ex_path.relative_to(repo_root)})."
                )
            if not force:
                raise FileExistsError(
                    f"External skill '{name}' already exists at {ex_path.relative_to(repo_root)} (pass --force or use 'update')."
                )
            # If moving between groups with --force, clean up old path
            target_dir = (
                repo_root / "skills" / "external" / group / name
                if group
                else repo_root / "skills" / "external" / name
            )
            if not dry_run and ex_path.resolve() != target_dir.resolve():
                rmtree_force(ex_path)
                if ex_group:
                    old_grp_dir = repo_root / "skills" / "external" / ex_group
                    if old_grp_dir.is_dir() and not any(old_grp_dir.iterdir()):
                        old_grp_dir.rmdir()

        target_dir = (
            repo_root / "skills" / "external" / group / name
            if group
            else repo_root / "skills" / "external" / name
        )
        audit = audit_skill_dir(src_dir, meta)
        print_audit(name, group, repo_url, subpath, resolved_ref, commit, audit)

        entry = {
            "name": name,
            "group": group,
            "repo": repo_url,
            "subpath": subpath,
            "ref": resolved_ref,
            "commit": commit,
            "fetched_at": dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "summary": sanitize_doc_text(summary_override or desc),
        }

        if dry_run:
            print(f"[DRY-RUN] Would vendor '{name}' to {target_dir.relative_to(repo_root)}")
            return entry

        copy_vendored_skill(src_dir, target_dir)

        manifest = load_manifest(repo_root)
        manifest["skills"] = [e for e in manifest["skills"] if e.get("name") != name]
        manifest["skills"].append(entry)
        save_manifest(manifest, repo_root)
        sync_external_docs(manifest, repo_root)

        print(f"Vendored '{name}' -> {target_dir.relative_to(repo_root)}")
        return entry
    finally:
        rmtree_force(tmp_dir)


def remove_external_skill(name: str, dry_run: bool = False, repo_root: Path = ROOT) -> None:
    manifest = load_manifest(repo_root)
    matches = [e for e in manifest["skills"] if e.get("name") == name]
    if not matches:
        raise ValueError(f"External skill '{name}' not found in skills/external/manifest.json.")

    entry = matches[0]
    grp = entry.get("group")
    target_dir = (
        repo_root / "skills" / "external" / grp / name
        if grp
        else repo_root / "skills" / "external" / name
    )
    if dry_run:
        print(f"[DRY-RUN] Would remove {target_dir.relative_to(repo_root)} and update manifest/docs.")
        return

    if target_dir.exists():
        rmtree_force(target_dir)
    if grp:
        grp_dir = repo_root / "skills" / "external" / grp
        if grp_dir.is_dir() and not any(grp_dir.iterdir()):
            grp_dir.rmdir()

    manifest["skills"] = [e for e in manifest["skills"] if e.get("name") != name]
    save_manifest(manifest, repo_root)
    sync_external_docs(manifest, repo_root)
    print(f"Removed external skill '{name}'.")


def check_external_skills(name: str | None = None, repo_root: Path = ROOT) -> list[dict]:
    manifest = load_manifest(repo_root)
    entries = manifest["skills"]
    if name:
        entries = [e for e in entries if e.get("name") == name]
        if not entries:
            raise ValueError(f"External skill '{name}' not found in manifest.")

    results: list[dict] = []
    for entry in entries:
        skill_name = entry["name"]
        pinned = entry["commit"].lower()
        ref = entry["ref"]
        if SHA_RE.fullmatch(ref):
            status = "pinned-sha"
            upstream = pinned
        else:
            upstream = resolve_remote_ref(entry["repo"], ref)
            if upstream is None:
                status = "unreachable"
            elif upstream == pinned:
                status = "up-to-date"
            else:
                status = "update-available"
        results.append(
            {
                "name": skill_name,
                "group": entry.get("group"),
                "ref": ref,
                "pinned": pinned,
                "upstream": upstream,
                "status": status,
            }
        )
    return results


def update_external_skills(
    name: str | None = None,
    update_all: bool = False,
    dry_run: bool = False,
    repo_root: Path = ROOT,
) -> int:
    if not name and not update_all:
        raise ValueError("Specify a skill name or --all.")
    manifest = load_manifest(repo_root)
    entries = manifest["skills"] if update_all else [e for e in manifest["skills"] if e.get("name") == name]
    if not entries:
        if name:
            raise ValueError(f"External skill '{name}' not found in manifest.")
        print("No external skills in manifest to update.")
        return 0

    updated = 0
    for entry in list(entries):
        old_commit = entry["commit"]
        new_entry = add_external_skill(
            spec=entry["repo"],
            group=entry.get("group"),
            ref_override=entry["ref"],
            subpath_override=entry["subpath"],
            summary_override=entry.get("summary"),
            force=True,
            dry_run=dry_run,
            repo_root=repo_root,
        )
        if new_entry["commit"] != old_commit:
            print(f"Updated '{entry['name']}': {old_commit[:12]} -> {new_entry['commit'][:12]}")
            updated += 1
        else:
            print(f"'{entry['name']}' is already at latest ({old_commit[:12]}).")

    if updated > 0 and not dry_run:
        print("Review changes with 'git diff skills/external/' before committing.")
    return updated


def cmd_add(args: argparse.Namespace) -> int:
    add_external_skill(
        spec=args.spec,
        group=args.group,
        ref_override=args.ref,
        subpath_override=args.subpath,
        summary_override=args.summary,
        force=args.force,
        dry_run=args.dry_run,
    )
    return 0


def cmd_list(_args: argparse.Namespace) -> int:
    manifest = load_manifest()
    entries = manifest.get("skills", [])
    if not entries:
        print("No external skills vendored in skills/external/manifest.json.")
        return 0
    for e in entries:
        loc = f"external/{e['group']}/{e['name']}" if e.get("group") else f"external/{e['name']}"
        print(f"{loc}  [{e['ref']} @ {e['commit'][:10]}]  {e['repo']} ({e['subpath']})")
    return 0


def cmd_check(args: argparse.Namespace) -> int:
    results = check_external_skills(name=args.name)
    if not results:
        print("No external skills vendored in skills/external/manifest.json.")
        return 0
    for r in results:
        if r["status"] == "update-available":
            print(f"{r['name']}: update-available ({r['pinned'][:10]} -> {r['upstream'][:10]} on {r['ref']})")
        elif r["status"] == "up-to-date":
            print(f"{r['name']}: up-to-date ({r['pinned'][:10]} on {r['ref']})")
        elif r["status"] == "pinned-sha":
            print(f"{r['name']}: pinned-sha ({r['pinned'][:10]})")
        else:
            print(f"{r['name']}: unreachable ({r['ref']})")
    return 0


def cmd_update(args: argparse.Namespace) -> int:
    update_external_skills(name=args.name, update_all=args.update_all, dry_run=args.dry_run)
    return 0


def cmd_remove(args: argparse.Namespace) -> int:
    remove_external_skill(name=args.name, dry_run=args.dry_run)
    return 0


def cmd_self_test(_args: argparse.Namespace) -> int:
    tmp_root = Path(tempfile.mkdtemp(prefix="external_skills_selftest_"))
    try:
        # 1. URL / spec parsing checks
        assert parse_source_spec("https://github.com/acme/skills/tree/main/skills/pdf") == (
            "https://github.com/acme/skills.git",
            "main",
            "skills/pdf",
        )
        assert parse_source_spec("acme/skills:skills/pdf@v2") == (
            "https://github.com/acme/skills.git",
            "v2",
            "skills/pdf",
        )
        assert parse_source_spec("https://github.com/acme/solo-skill") == (
            "https://github.com/acme/solo-skill.git",
            None,
            ".",
        )

        # 2. Build an isolated local upstream multi-skill git repo
        upstream = tmp_root / "upstream-repo"
        upstream.mkdir()
        run_git(["init", "-q", "-b", "main"], cwd=upstream)
        run_git(["config", "user.email", "smoke@example.com"], cwd=upstream)
        run_git(["config", "user.name", "Smoke"], cwd=upstream)

        s1 = upstream / "skills" / "ext-pdf"
        (s1 / "scripts").mkdir(parents=True)
        (s1 / "SKILL.md").write_text(
            "---\nname: ext-pdf\ndescription: Parse PDFs \u2014 upstream v1.\n---\n# Ext PDF\n",
            encoding="utf-8",
        )
        (s1 / "scripts" / "parse.py").write_text("print('v1')\n", encoding="utf-8")

        s2 = upstream / "skills" / "ext-solo"
        s2.mkdir(parents=True)
        (s2 / "SKILL.md").write_text(
            "---\nname: ext-solo\ndescription: Solo external helper.\ndisable-model-invocation: true\n---\n# Ext Solo\n",
            encoding="utf-8",
        )

        # Unrelated file that sparse-checkout should NOT copy into the vendored folder
        (upstream / "README.md").write_text("# Giant Monorepo\n", encoding="utf-8")
        run_git(["add", "."], cwd=upstream)
        run_git(["commit", "-q", "-m", "v1"], cwd=upstream)
        commit_v1 = run_git(["rev-parse", "HEAD"], cwd=upstream).stdout.strip().lower()

        # 3. Build an isolated fake forge repo
        fake_repo = tmp_root / "forge"
        for b in ALL_BUCKETS:
            (fake_repo / "skills" / b).mkdir(parents=True)
        # Seed one custom skill to test duplicate-name protection
        custom_clash = fake_repo / "skills" / "custom" / "kb-skills" / "kb-query"
        custom_clash.mkdir(parents=True)
        (custom_clash / "SKILL.md").write_text("---\nname: kb-query\ndescription: Own KB query.\n---\n", encoding="utf-8")

        # 4. Add grouped + standalone skills via sparse checkout
        e1 = add_external_skill(
            spec=str(upstream),
            group="kb-skills",
            ref_override="main",
            subpath_override="skills/ext-pdf",
            repo_root=fake_repo,
        )
        assert e1["commit"] == commit_v1
        assert (fake_repo / "skills" / "external" / "kb-skills" / "ext-pdf" / "SKILL.md").is_file()
        assert not (fake_repo / "skills" / "external" / "kb-skills" / "ext-pdf" / ".git").exists()

        e2 = add_external_skill(
            spec=str(upstream),
            group=None,
            ref_override="main",
            subpath_override="skills/ext-solo",
            repo_root=fake_repo,
        )
        assert (fake_repo / "skills" / "external" / "ext-solo" / "SKILL.md").is_file()

        # Verify auto-synced docs have zero em-dashes even when upstream description had one
        docs_text = external_docs_path(fake_repo).read_text(encoding="utf-8")
        assert "\u2014" not in docs_text, "Generated docs/external/README.md must sanitize upstream em-dashes"
        assert "ext-pdf" in docs_text and "ext-solo" in docs_text

        # 5. Add a distractor branch ending in '/main' (e.g. changeset-release/main) at a different commit
        #    to ensure resolve_remote_ref matches refs/heads/main exactly.
        run_git(["checkout", "-q", "-b", "changeset-release/main"], cwd=upstream)
        (upstream / "RELEASE.md").write_text("release branch\n", encoding="utf-8")
        run_git(["add", "RELEASE.md"], cwd=upstream)
        run_git(["commit", "-q", "-m", "distractor branch"], cwd=upstream)
        run_git(["checkout", "-q", "main"], cwd=upstream)

        # Check reports up-to-date before upstream main commit
        chk1 = {r["name"]: r for r in check_external_skills(repo_root=fake_repo)}
        assert chk1["ext-pdf"]["status"] == "up-to-date"

        # 6. Push a v2 commit upstream -> check detects update-available -> update pulls v2
        (s1 / "scripts" / "parse.py").write_text("print('v2')\n", encoding="utf-8")
        run_git(["add", "."], cwd=upstream)
        run_git(["commit", "-q", "-m", "v2"], cwd=upstream)
        commit_v2 = run_git(["rev-parse", "HEAD"], cwd=upstream).stdout.strip().lower()
        assert commit_v2 != commit_v1

        chk2 = {r["name"]: r for r in check_external_skills(name="ext-pdf", repo_root=fake_repo)}
        assert chk2["ext-pdf"]["status"] == "update-available"
        assert chk2["ext-pdf"]["upstream"] == commit_v2

        updated_count = update_external_skills(name="ext-pdf", repo_root=fake_repo)
        assert updated_count == 1
        assert "v2" in (fake_repo / "skills" / "external" / "kb-skills" / "ext-pdf" / "scripts" / "parse.py").read_text(
            encoding="utf-8"
        )

        # 7. Duplicate name collision against skills/custom/ must fail even with --force
        clash_dir = upstream / "skills" / "kb-query"
        clash_dir.mkdir(parents=True)
        (clash_dir / "SKILL.md").write_text("---\nname: kb-query\ndescription: Upstream clash.\n---\n", encoding="utf-8")
        run_git(["add", "."], cwd=upstream)
        run_git(["commit", "-q", "-m", "add clash"], cwd=upstream)
        try:
            add_external_skill(
                spec=str(upstream),
                group="kb-skills",
                ref_override="main",
                subpath_override="skills/kb-query",
                force=True,
                repo_root=fake_repo,
            )
            raise AssertionError("Expected ValueError for skill colliding with skills/custom/")
        except ValueError:
            pass

        # 8. Remove grouped skill cleans up folder, empty group dir, manifest, and docs
        remove_external_skill("ext-pdf", repo_root=fake_repo)
        assert not (fake_repo / "skills" / "external" / "kb-skills").exists()
        assert "ext-pdf" not in external_docs_path(fake_repo).read_text(encoding="utf-8")
        assert "ext-solo" in external_docs_path(fake_repo).read_text(encoding="utf-8")

        print("external_skills self-test PASSED.")
        return 0
    finally:
        rmtree_force(tmp_root)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Vendored external/GitHub skill manager for agent-skills forge")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_add = sub.add_parser("add", help="Fetch and vendor a specific skill folder from GitHub or git")
    p_add.add_argument("spec", help="GitHub URL, 'owner/repo:subpath@ref', or local git repo path")
    p_add.add_argument("--group", default=None, help="Optional 1-level domain group (can match a skills/custom/ group)")
    p_add.add_argument("--ref", default=None, help="Branch, tag, or commit SHA override")
    p_add.add_argument("--subpath", default=None, help="Subdirectory inside upstream repo containing SKILL.md")
    p_add.add_argument("--summary", default=None, help="Optional 1-line summary override for docs/external/README.md")
    p_add.add_argument("--force", action="store_true", help="Overwrite an existing vendored external skill")
    p_add.add_argument("--dry-run", action="store_true", help="Fetch and audit without modifying this repo")
    p_add.set_defaults(func=cmd_add)

    p_list = sub.add_parser("list", help="List all vendored external skills")
    p_list.set_defaults(func=cmd_list)

    p_check = sub.add_parser("check", help="Check upstream refs via git ls-remote without cloning")
    p_check.add_argument("name", nargs="?", default=None, help="Optional skill name to check")
    p_check.set_defaults(func=cmd_check)

    p_upd = sub.add_parser("update", help="Re-fetch one or all vendored skills from upstream")
    p_upd.add_argument("name", nargs="?", default=None, help="External skill name to update")
    p_upd.add_argument("--all", dest="update_all", action="store_true", help="Update all vendored external skills")
    p_upd.add_argument("--dry-run", action="store_true", help="Check and audit updates without writing")
    p_upd.set_defaults(func=cmd_update)

    p_rm = sub.add_parser("remove", help="Remove a vendored external skill and update manifest/docs")
    p_rm.add_argument("name", help="External skill name to remove")
    p_rm.add_argument("--dry-run", action="store_true", help="Print planned removal without deleting")
    p_rm.set_defaults(func=cmd_remove)

    p_self = sub.add_parser("self-test", help="Run isolated offline smoke test against a temp local git repo")
    p_self.set_defaults(func=cmd_self_test)

    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    try:
        return args.func(args)
    except (ValueError, FileExistsError, FileNotFoundError, RuntimeError, OSError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
