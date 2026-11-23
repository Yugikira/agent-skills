#!/usr/bin/env python3
"""
Check Related Papers table against local summaries in source/summary/ and update Wiki Links.

Supports --kb-dir / --root, .kb_root file, or $KB_ROOT environment variable.
"""

import argparse
import os
import re
import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple


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
        if (candidate / "source").is_dir() or (candidate / "wiki").is_dir():
            if not (candidate / "SKILL.md").exists():
                return candidate
    return cwd


def normalize_title(title: str) -> str:
    title = title.lower().strip()
    title = re.sub(r"[^\w\s']", " ", title)
    return " ".join(title.split())


def parse_frontmatter(content: str) -> Dict[str, str]:
    if not content.startswith("---"):
        return {}
    end_match = re.search(r"\n---\s*\n", content[3:])
    if not end_match:
        return {}
    fm_text = content[3 : 3 + end_match.start()]
    meta: Dict[str, str] = {}
    for line in fm_text.splitlines():
        if ":" in line:
            k, v = line.split(":", 1)
            meta[k.strip()] = v.strip().strip('"').strip("'")
    return meta


def build_summary_index(summary_dir: Path) -> Dict[str, str]:
    title_index: Dict[str, str] = {}
    if not summary_dir.is_dir():
        return title_index

    for md_file in sorted(summary_dir.glob("*.md")):
        try:
            content = md_file.read_text(encoding="utf-8")
        except Exception:
            continue
        fm = parse_frontmatter(content)
        title = fm.get("title", "")
        if not title:
            h1 = re.search(r"^#\s+(.+)$", content, re.MULTILINE)
            title = h1.group(1).strip() if h1 else ""
        norm = normalize_title(title)
        if len(norm) >= 5:
            title_index[norm] = md_file.stem
    return title_index


def match_title(query_title: str, title_index: Dict[str, str], self_stem: str) -> Optional[str]:
    norm_q = normalize_title(query_title)
    if len(norm_q) < 5 or norm_q.startswith("full title") or norm_q.startswith("title"):
        return None

    if norm_q in title_index and title_index[norm_q] != self_stem:
        return title_index[norm_q]

    q_tokens = {w for w in norm_q.split() if len(w) > 2}
    best_stem = None
    best_score = 0.0
    for idx_title, stem in title_index.items():
        if stem == self_stem:
            continue
        if len(norm_q) >= 15 and len(idx_title) >= 15:
            if norm_q in idx_title or idx_title in norm_q:
                return stem
        idx_tokens = {w for w in idx_title.split() if len(w) > 2}
        if q_tokens and idx_tokens:
            overlap = len(q_tokens & idx_tokens) / max(len(q_tokens), len(idx_tokens))
            if overlap >= 0.80 and overlap > best_score:
                best_score = overlap
                best_stem = stem
    return best_stem


def process_summary_related_papers(
    summary_path: Path, title_index: Dict[str, str], update: bool = False
) -> Tuple[List[Dict[str, str]], int]:
    content = summary_path.read_text(encoding="utf-8")
    lines = content.splitlines()
    in_related = False
    header_seen = False
    results: List[Dict[str, str]] = []
    matched_count = 0
    updated_lines: List[str] = []

    for line in lines:
        stripped = line.strip()
        if re.match(r"^##\s+Related Papers", stripped):
            in_related = True
            header_seen = False
            updated_lines.append(line)
            continue

        if in_related:
            if stripped.startswith("## "):
                in_related = False
            elif stripped.startswith("|") and not stripped.startswith("| >"):
                if not header_seen:
                    header_seen = True
                    updated_lines.append(line)
                    continue
                if re.match(r"^\|\s*[-:]+", stripped):
                    updated_lines.append(line)
                    continue

                cells = [c.strip() for c in stripped.strip("|").split("|")]
                if len(cells) >= 5:
                    authors, year, title, relevance = cells[0], cells[1], cells[2], cells[3]
                    matched_stem = match_title(title, title_index, summary_path.stem)
                    new_link = f"[[source/summary/{matched_stem}]]" if matched_stem else "[not in wiki]"
                    if matched_stem:
                        matched_count += 1
                    results.append({
                        "authors": authors,
                        "year": year,
                        "title": title,
                        "relevance": relevance,
                        "wiki_link": new_link,
                        "matched": bool(matched_stem),
                    })
                    cells[4] = new_link
                    updated_lines.append("| " + " | ".join(cells[:5]) + " |")
                    continue

        updated_lines.append(line)

    if update and results:
        summary_path.write_text("\n".join(updated_lines) + "\n", encoding="utf-8")

    return results, matched_count


def main() -> int:
    parser = argparse.ArgumentParser(description="Match and update Related Papers links in a summary.")
    parser.add_argument("--kb-dir", "--root", dest="root", help="Knowledge Base root directory")
    parser.add_argument("--summary", required=True, help="Path to paper summary markdown file")
    parser.add_argument("--update", action="store_true", help="Write updated Wiki Links back to summary file")
    args = parser.parse_args()

    root_dir = find_workspace_root(args.root)
    summary_path = Path(args.summary)
    if not summary_path.exists():
        summary_path = root_dir / args.summary
    if not summary_path.exists():
        print(f"Error: Summary file not found: {args.summary}", file=sys.stderr)
        return 1

    title_index = build_summary_index(root_dir / "source" / "summary")
    results, matched_count = process_summary_related_papers(summary_path, title_index, update=args.update)

    print("| Authors | Year | Title | Wiki Link |")
    print("| :--- | :--- | :--- | :--- |")
    for r in results:
        print(f"| {r['authors']} | {r['year']} | {r['title']} | {r['wiki_link']} |")
    print(f"\nMatched: {matched_count}/{len(results)} related papers in local wiki.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
