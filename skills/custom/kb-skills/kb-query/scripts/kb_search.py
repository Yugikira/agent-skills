#!/usr/bin/env python3
"""
Standalone Knowledge Base Search & Deep-Link Graph Expander for kb-query.

Works from ANY external research workspace once pointed at a Knowledge Base directory
via --kb-dir, .kb_root (in current working directory), or $KB_ROOT environment variable.

Priority hierarchy for searching:
  1. `rg` (ripgrep) if installed on PATH
  2. `grep` / `find` CLI or pure-Python fallback

Usage:
  # Save KB path for the current research workspace and print KB statistics:
  python3 scripts/kb_search.py --kb-dir /path/to/my-kb --save-kb-dir --stats

  # Search filenames and content (rg-first):
  python3 scripts/kb_search.py --query "conservatism|asymmetric timeliness"

  # Search only paper summaries:
  python3 scripts/kb_search.py --query "site visit" --scope summaries

  # Deep 1-hop wikilink graph expansion around a concept or page:
  python3 scripts/kb_search.py --deep "Corporate_Site_Visit" --json
"""

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

CATEGORIES = ["concepts", "variables", "constructs", "methods", "theories"]
KB_ROOT_FILE = ".kb_root"


def resolve_kb_root(explicit_kb_dir: Optional[str] = None, save: bool = False) -> Path:
    """
    Resolve the target Knowledge Base root directory using priority order:
      1. --kb-dir CLI argument
      2. .kb_root file in current working directory (or parent directories)
      3. $KB_ROOT environment variable
      4. Current working directory (if ./wiki or ./source/summary exists)
    """
    cwd = Path.cwd().resolve()
    chosen: Optional[Path] = None

    if explicit_kb_dir:
        chosen = Path(explicit_kb_dir).expanduser().resolve()
    else:
        for d in [cwd] + list(cwd.parents):
            cfg = d / KB_ROOT_FILE
            if cfg.is_file():
                saved_text = cfg.read_text(encoding="utf-8").strip()
                if saved_text:
                    cand = Path(saved_text).expanduser().resolve()
                    if cand.is_dir():
                        chosen = cand
                        break

        if chosen is None and os.environ.get("KB_ROOT"):
            cand = Path(os.environ["KB_ROOT"]).expanduser().resolve()
            if cand.is_dir():
                chosen = cand

        if chosen is None:
            for d in [cwd] + list(cwd.parents):
                if ((d / "wiki").is_dir() or (d / "source" / "summary").is_dir()) and not (d / "SKILL.md").exists():
                    chosen = d
                    break

    if chosen is None or not ((chosen / "wiki").is_dir() or (chosen / "source").is_dir()):
        print(
            "Error: Could not locate Knowledge Base directory (missing wiki/ and source/summary/).\n"
            "Pass --kb-dir /path/to/your/kb (add --save-kb-dir to remember it in .kb_root).",
            file=sys.stderr,
        )
        sys.exit(2)

    if save:
        (cwd / KB_ROOT_FILE).write_text(str(chosen) + "\n", encoding="utf-8")

    return chosen


def parse_frontmatter(content: str) -> Dict[str, str]:
    if not content.startswith("---"):
        return {}
    end_match = re.search(r"\n---\s*\n", content[3:])
    if not end_match:
        return {}
    fm_block = content[3 : 3 + end_match.start()]
    meta: Dict[str, str] = {}
    for line in fm_block.splitlines():
        if ":" in line:
            k, v = line.split(":", 1)
            meta[k.strip()] = v.strip().strip('"').strip("'")
    return meta


def get_kb_stats(kb_root: Path) -> Dict[str, object]:
    stats: Dict[str, int] = {}
    for cat in CATEGORIES:
        cat_dir = kb_root / "wiki" / cat
        stats[cat] = len([p for p in cat_dir.glob("*.md") if not p.name.startswith("_")]) if cat_dir.is_dir() else 0
    sum_dir = kb_root / "source" / "summary"
    stats["summaries"] = len(list(sum_dir.glob("*.md"))) if sum_dir.is_dir() else 0
    conv_dir = kb_root / "source" / "conversations"
    if not conv_dir.is_dir():
        conv_dir = kb_root / "source" / "conversation"
    stats["conversations"] = len(list(conv_dir.glob("*.md"))) if conv_dir.is_dir() else 0
    return {"kb_root": str(kb_root), "counts": stats}


def run_rg_or_fallback_search(
    kb_root: Path, query: str, scope: str = "all", context_lines: int = 2
) -> Dict[str, object]:
    """
    Priority 1: rg (ripgrep)
    Priority 2: grep / find
    Priority 3: Pure Python scan
    """
    target_dirs: List[Path] = []
    if scope in ("all", "wiki") and (kb_root / "wiki").is_dir():
        target_dirs.append(kb_root / "wiki")
    if scope in ("all", "summaries") and (kb_root / "source" / "summary").is_dir():
        target_dirs.append(kb_root / "source" / "summary")
    if scope == "all" and (kb_root / "source" / "conversations").is_dir():
        target_dirs.append(kb_root / "source" / "conversations")

    if not target_dirs:
        return {"engine": "none", "file_matches": [], "content_matches": ""}

    dir_strs = [str(d) for d in target_dirs]
    rg_bin = shutil.which("rg")

    # Priority 1: ripgrep (rg)
    if rg_bin:
        file_list_proc = subprocess.run(
            [rg_bin, "--files", "--glob", "*.md", "--glob", "!_index.md"] + dir_strs,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
        all_files = [line.strip() for line in file_list_proc.stdout.splitlines() if line.strip()]
        file_pat = re.sub(r"\s+", lambda _m: r"[_\s-]", query.strip())
        try:
            rx_file = re.compile(file_pat, re.IGNORECASE)
        except re.error:
            rx_file = re.compile(re.escape(query), re.IGNORECASE)
        file_matches = [
            str(Path(f).resolve().relative_to(kb_root))
            for f in all_files
            if rx_file.search(Path(f).name) or rx_file.search(Path(f).name.replace("_", " "))
        ]

        content_proc = subprocess.run(
            [
                rg_bin,
                "-i",
                "-n",
                "-C",
                str(context_lines),
                "--glob",
                "*.md",
                "--glob",
                "!_index.md",
                query,
            ]
            + dir_strs,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
        return {
            "engine": "rg",
            "kb_root": str(kb_root),
            "file_matches": file_matches,
            "content_matches": content_proc.stdout.strip(),
        }

    # Priority 2: POSIX grep
    grep_bin = shutil.which("grep")
    if grep_bin:
        file_pat = re.sub(r"\s+", lambda _m: r"[_\s-]", query.strip())
        try:
            rx_file = re.compile(file_pat, re.IGNORECASE)
        except re.error:
            rx_file = re.compile(re.escape(query), re.IGNORECASE)
        file_matches = []
        for d in target_dirs:
            for md in sorted(d.rglob("*.md")):
                if not md.name.startswith("_index") and (rx_file.search(md.name) or rx_file.search(md.name.replace("_", " "))):
                    file_matches.append(str(md.resolve().relative_to(kb_root)))

        grep_proc = subprocess.run(
            [grep_bin, "-rnI", "-E", "-i", f"-C{context_lines}", query] + dir_strs,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
        return {
            "engine": "grep",
            "kb_root": str(kb_root),
            "file_matches": file_matches,
            "content_matches": grep_proc.stdout.strip(),
        }

    # Priority 3: Pure Python fallback
    try:
        rx = re.compile(query, re.IGNORECASE)
    except re.error:
        rx = re.compile(re.escape(query), re.IGNORECASE)

    file_matches = []
    snippets = []
    for d in target_dirs:
        for md in sorted(d.rglob("*.md")):
            if md.name.startswith("_index"):
                continue
            rel = str(md.resolve().relative_to(kb_root))
            if rx.search(md.name):
                file_matches.append(rel)
            lines = md.read_text(encoding="utf-8", errors="replace").splitlines()
            for idx, line in enumerate(lines, 1):
                if rx.search(line):
                    snippets.append(f"{rel}:{idx}:{line}")

    return {
        "engine": "python-fallback",
        "kb_root": str(kb_root),
        "file_matches": file_matches,
        "content_matches": "\n".join(snippets[:100]),
    }


def resolve_md_link(raw_target: str, src_file: Path, kb_root: Path) -> Optional[Path]:
    target = raw_target.split("#")[0].split(" ")[0].strip().strip("<>")
    if not target or target.startswith(("http://", "https://", "mailto:", "#")):
        return None
    for cand in (src_file.parent / target, kb_root / target):
        if cand.is_file():
            return cand.resolve()
    return None


def resolve_wikilink(raw_link: str, kb_root: Path) -> Optional[Path]:
    target = raw_link.split("|")[0].split("#")[0].strip()
    if not target:
        return None
    base = target[:-3] if target.endswith(".md") else target
    candidates: List[Path] = []
    if target.startswith("source/"):
        candidates.extend([
            kb_root / f"{base}.md",
            kb_root / f"{base}_summary.md",
            kb_root / f"{base}_review.md",
        ])
    elif "/" in target:
        candidates.extend([kb_root / "wiki" / f"{base}.md", kb_root / f"{base}.md"])
    else:
        for cat in CATEGORIES:
            candidates.append(kb_root / "wiki" / cat / f"{base}.md")
        candidates.extend([
            kb_root / "source" / "summary" / f"{base}.md",
            kb_root / "source" / "summary" / f"{base}_summary.md",
        ])
    for c in candidates:
        if c.is_file():
            return c.resolve()
    return None


def expand_deep_graph(kb_root: Path, page_query: str) -> Dict[str, object]:
    """Locate a focal wiki page and resolve all 1-hop outgoing and incoming Markdown/legacy links."""
    norm_q = page_query.lower().strip().replace(" ", "_")
    focal_path: Optional[Path] = None

    for cat in CATEGORIES:
        cand = kb_root / "wiki" / cat / f"{page_query}.md"
        if cand.is_file():
            focal_path = cand.resolve()
            break
        if (kb_root / "wiki" / cat).is_dir():
            for md in (kb_root / "wiki" / cat).glob("*.md"):
                if md.stem.lower() == norm_q or norm_q in md.stem.lower():
                    focal_path = md.resolve()
                    break
        if focal_path:
            break

    if not focal_path:
        return {"error": f"Could not find wiki page matching '{page_query}' in {kb_root / 'wiki'}"}

    content = focal_path.read_text(encoding="utf-8")
    outgoing_md = re.findall(r"(?<!!)\[[^\[\]]+\]\(([^)]+)\)", content)
    outgoing_wiki = re.findall(r"\[\[([^\[\]]+)\]\]", content)
    outgoing_resolved: List[str] = []
    outgoing_missing: List[str] = []

    for raw in outgoing_md:
        if raw.startswith(("http://", "https://", "mailto:", "#")):
            continue
        resolved = resolve_md_link(raw, focal_path, kb_root)
        if resolved and resolved != focal_path:
            rel = str(resolved.relative_to(kb_root))
            if rel not in outgoing_resolved:
                outgoing_resolved.append(rel)
        elif not resolved and not any(ch in raw for ch in ("{", "}", "<", ">")):
            clean = raw.split("#")[0].strip()
            if clean and clean not in outgoing_missing:
                outgoing_missing.append(clean)

    for raw in outgoing_wiki:
        resolved = resolve_wikilink(raw, kb_root)
        if resolved and resolved != focal_path:
            rel = str(resolved.relative_to(kb_root))
            if rel not in outgoing_resolved:
                outgoing_resolved.append(rel)
        elif not resolved:
            clean = raw.split("|")[0].strip()
            if clean not in outgoing_missing:
                outgoing_missing.append(clean)

    # Also find incoming backlinks (standard markdown links and legacy wikilinks) across wiki/ and source/summary/
    focal_stem = focal_path.stem
    backlinks: List[str] = []
    md_backlink_re = re.compile(rf"\((?:[^)]*/)?{re.escape(focal_stem)}\.md(?:#[^)]*)?\)")
    for scan_dir in [kb_root / "wiki", kb_root / "source" / "summary"]:
        if not scan_dir.is_dir():
            continue
        for md in sorted(scan_dir.rglob("*.md")):
            if md.resolve() == focal_path or md.name.startswith("_index"):
                continue
            txt = md.read_text(encoding="utf-8", errors="replace")
            if (
                md_backlink_re.search(txt)
                or f"[[{focal_stem}" in txt
                or f"/{focal_stem}]]" in txt
                or f"/{focal_stem}|" in txt
            ):
                backlinks.append(str(md.resolve().relative_to(kb_root)))

    return {
        "kb_root": str(kb_root),
        "focal_page": str(focal_path.relative_to(kb_root)),
        "outgoing_linked_files": outgoing_resolved,
        "incoming_backlink_files": backlinks,
        "unresolved_links": outgoing_missing,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Standalone rg-first Knowledge Base search & graph expander.")
    parser.add_argument("--kb-dir", "--root", dest="kb_dir", help="Path to Knowledge Base root directory")
    parser.add_argument("--save-kb-dir", action="store_true", help="Persist --kb-dir to .kb_root in current workspace")
    parser.add_argument("--stats", action="store_true", help="Print Knowledge Base page counts")
    parser.add_argument("--query", "-q", help="Search keyword or regex pattern (uses rg first)")
    parser.add_argument("--scope", choices=["all", "wiki", "summaries"], default="all", help="Search scope")
    parser.add_argument("--context", "-C", type=int, default=2, help="Context lines for content matches")
    parser.add_argument("--deep", help="Expand 1-hop wikilink graph around a concept or wiki page name")
    parser.add_argument("--json", action="store_true", help="Output JSON format")
    args = parser.parse_args()

    kb_root = resolve_kb_root(args.kb_dir, save=args.save_kb_dir)

    if args.stats and not (args.query or args.deep):
        st = get_kb_stats(kb_root)
        if args.json:
            print(json.dumps(st, indent=2))
        else:
            print(f"Knowledge Base Root: {st['kb_root']}")
            for k, v in st["counts"].items():
                print(f"  {k}: {v}")
        return 0

    if args.deep:
        graph = expand_deep_graph(kb_root, args.deep)
        if args.json:
            print(json.dumps(graph, indent=2, ensure_ascii=False))
        else:
            if "error" in graph:
                print(graph["error"], file=sys.stderr)
                return 1
            print(f"# Deep Graph for `{graph['focal_page']}` (KB: `{graph['kb_root']}`)")
            print("\n## Outgoing Linked Pages")
            for p in graph["outgoing_linked_files"]:
                print(f"- `{p}`")
            print("\n## Incoming Backlinks (Summaries & Wiki Pages)")
            for p in graph["incoming_backlink_files"]:
                print(f"- `{p}`")
        return 0

    if args.query:
        res = run_rg_or_fallback_search(kb_root, args.query, scope=args.scope, context_lines=args.context)
        if args.json:
            print(json.dumps(res, indent=2, ensure_ascii=False))
        else:
            print(f"# Search Results (engine: {res['engine']}, kb_root: {res['kb_root']})")
            print("\n## Matching Filenames")
            if res["file_matches"]:
                for fm in res["file_matches"]:
                    print(f"- `{fm}`")
            else:
                print("- (none)")
            print("\n## Matching Content Snippets")
            print(res["content_matches"] or "(none)")
        return 0

    parser.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
