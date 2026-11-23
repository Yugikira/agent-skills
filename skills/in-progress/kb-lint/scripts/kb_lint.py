#!/usr/bin/env python3
"""
Unified Knowledge Base Linter (Broken Wikilinks & True Incoming-Link Orphans).

Supports --kb-dir / --root, .kb_root file, or $KB_ROOT environment variable.
"""

import argparse
import json
import os
import re
import sys
from collections import defaultdict
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

CATEGORIES = ["concepts", "variables", "constructs", "methods", "theories"]


def find_workspace_root(explicit_root: Optional[str] = None) -> Path:
    if explicit_root:
        return Path(explicit_root).expanduser().resolve()
    cwd = Path.cwd().resolve()
    for d in [cwd] + list(cwd.parents):
        cfg = d / ".kb_root"
        if cfg.is_file():
            txt = cfg.read_text(encoding="utf-8").strip()
            if txt and Path(txt).expanduser().resolve().is_dir():
                return Path(txt).expanduser().resolve()
    if os.environ.get("KB_ROOT"):
        env_p = Path(os.environ["KB_ROOT"]).expanduser().resolve()
        if env_p.is_dir():
            return env_p
    for candidate in [cwd] + list(cwd.parents):
        if (candidate / "wiki").is_dir() or (candidate / "source").is_dir():
            if not (candidate / "SKILL.md").exists():
                return candidate
    return cwd


def extract_wikilinks(content: str) -> List[Tuple[int, str, str]]:
    links: List[Tuple[int, str, str]] = []
    in_code_block = False
    for line_num, line in enumerate(content.splitlines(), 1):
        stripped = line.strip()
        if stripped.startswith("```"):
            in_code_block = not in_code_block
            continue
        if in_code_block:
            continue
        for match in re.finditer(r"\[\[([^\[\]]+)\]\]", line):
            raw = match.group(1).strip()
            if "{" in raw or "}" in raw or raw in ("filename", "link", "source"):
                continue
            links.append((line_num, raw, stripped[:90]))
    return links


def resolve_wikilink(raw_link: str, root_dir: Path) -> Optional[Path]:
    target = raw_link.split("|")[0].split("#")[0].strip()
    if not target:
        return None

    candidates: List[Path] = []
    if target.startswith("raw/"):
        candidates.append(root_dir / target)
        if not target.endswith(".pdf") and not target.endswith(".md"):
            candidates.append(root_dir / f"{target}.md")
            candidates.append(root_dir / f"{target}.pdf")
    elif target.startswith("source/"):
        base = target[:-3] if target.endswith(".md") else target
        candidates.append(root_dir / f"{base}.md")
        candidates.append(root_dir / f"{base}_summary.md")
        candidates.append(root_dir / f"{base}_review.md")
    elif "/" in target:
        base = target[:-3] if target.endswith(".md") else target
        candidates.append(root_dir / "wiki" / f"{base}.md")
        candidates.append(root_dir / f"{base}.md")
    else:
        base = target[:-3] if target.endswith(".md") else target
        for cat in CATEGORIES:
            candidates.append(root_dir / "wiki" / cat / f"{base}.md")
        candidates.append(root_dir / "wiki" / f"{base}.md")
        candidates.append(root_dir / "source" / "summary" / f"{base}.md")
        candidates.append(root_dir / "source" / "summary" / f"{base}_summary.md")

    for cand in candidates:
        if cand.exists():
            return cand.resolve()
    return None


def run_lint(root_dir: Path) -> Dict[str, object]:
    scan_dirs = [
        root_dir / "wiki",
        root_dir / "source" / "summary",
        root_dir / "source" / "conversations",
        root_dir / "source" / "conversation",
    ]

    all_wiki_pages: Set[Path] = set()
    for cat in CATEGORIES:
        cat_dir = root_dir / "wiki" / cat
        if cat_dir.is_dir():
            for md_file in cat_dir.glob("*.md"):
                if not md_file.name.startswith("_"):
                    all_wiki_pages.add(md_file.resolve())

    incoming_links: Dict[Path, Set[Path]] = defaultdict(set)
    broken_by_file: Dict[str, List[Dict[str, object]]] = defaultdict(list)
    total_links = 0
    broken_count = 0

    seen_files: Set[Path] = set()
    for sdir in scan_dirs:
        if not sdir.is_dir():
            continue
        for md_file in sorted(sdir.rglob("*.md")):
            resolved_src = md_file.resolve()
            if resolved_src in seen_files or md_file.name.startswith("_index") or md_file.name == "log.md":
                continue
            seen_files.add(resolved_src)

            try:
                content = md_file.read_text(encoding="utf-8")
            except Exception:
                continue

            for line_num, raw_target, preview in extract_wikilinks(content):
                total_links += 1
                resolved_target = resolve_wikilink(raw_target, root_dir)
                if resolved_target is None:
                    broken_count += 1
                    rel_src = str(resolved_src.relative_to(root_dir))
                    broken_by_file[rel_src].append({
                        "line": line_num,
                        "target": raw_target,
                        "context": preview,
                    })
                elif resolved_target != resolved_src:
                    incoming_links[resolved_target].add(resolved_src)

    orphans: List[str] = []
    for page in sorted(all_wiki_pages):
        if not incoming_links.get(page):
            orphans.append(str(page.relative_to(root_dir)))

    return {
        "kb_root": str(root_dir),
        "total_wiki_pages": len(all_wiki_pages),
        "total_wikilinks_checked": total_links,
        "broken_wikilinks_count": broken_count,
        "broken_by_file": dict(broken_by_file),
        "orphan_pages_count": len(orphans),
        "orphan_pages": orphans,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Lint Knowledge Base wikilinks and true orphan pages.")
    parser.add_argument("--kb-dir", "--root", dest="root", help="Knowledge Base root directory")
    parser.add_argument("--json", action="store_true", help="Output JSON report")
    args = parser.parse_args()

    root_dir = find_workspace_root(args.root)
    report = run_lint(root_dir)

    if args.json:
        print(json.dumps(report, indent=2, ensure_ascii=False))
    else:
        print(f"# Knowledge Base Lint Report (`{report['kb_root']}`)\n")
        print(f"- Wiki pages scanned: {report['total_wiki_pages']}")
        print(f"- Total wikilinks checked: {report['total_wikilinks_checked']}")
        print(f"- Broken wikilinks: {report['broken_wikilinks_count']}")
        print(f"- True orphan wiki pages (0 incoming links): {report['orphan_pages_count']}\n")

        if report["broken_by_file"]:
            print("## Broken Wikilinks")
            for src_file, items in report["broken_by_file"].items():
                print(f"### `{src_file}`")
                for item in items:
                    print(f"- Line {item['line']}: `[[{item['target']}]]` ({item['context']})")
                print()

        if report["orphan_pages"]:
            print("## Orphan Wiki Pages (No Incoming Links)")
            for orph in report["orphan_pages"]:
                print(f"- `{orph}`")

    return 1 if report["broken_wikilinks_count"] > 0 else 0


if __name__ == "__main__":
    sys.exit(main())
