#!/usr/bin/env python3
"""
Unified Wiki Collision Detector (Pre-Creation & Post-Creation).

Scans actual markdown files in wiki/{category}/*.md (zero _index.md dependency)
and compares proposed or newly created pages against existing wiki pages using
normalized name matching, token containment, and section-level definition overlap.

Supports --kb-dir / --root, .kb_root file, or $KB_ROOT environment variable.

Usage:
  # Pre-creation check from a paper summary (archival, experimental, survey, analytical):
  python3 scripts/check_collision.py --summary source/summary/barth_2012_summary.md --json

  # Post-creation check for pages created for a specific citekey:
  python3 scripts/check_collision.py --citekey barth_2012 --json

  # Post-creation check from explicit JSON list:
  python3 scripts/check_collision.py --new-pages new_pages.json --json
"""

import argparse
import json
import os
import re
import sys
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

CATEGORIES = ["concepts", "variables", "constructs", "methods", "theories"]

STOPWORDS = {
    "the", "a", "an", "is", "are", "was", "were", "of", "to", "in", "for",
    "and", "or", "by", "with", "from", "as", "that", "this", "these", "those",
    "which", "who", "what", "when", "where", "how", "why", "be", "been", "being",
    "have", "has", "had", "do", "does", "did", "will", "would", "could", "should",
    "may", "might", "must", "shall", "can", "need", "into", "over", "under",
    "between", "across", "during", "within", "without", "through", "measured",
    "defined", "variable", "concept", "paper", "study", "model", "using", "used"
}

SKIP_MARKERS = [
    "not yet in wiki", "implicit", "no wiki", "skip", "common concept",
    "[derived]", "[composite]", "[skip]", "[no wiki]"
]


def find_workspace_root(explicit_root: Optional[str] = None) -> Path:
    """Resolve KB root from --kb-dir/--root, .kb_root, $KB_ROOT, or CWD."""
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


def normalize_name(name: str) -> str:
    """Normalize wiki page or concept/variable name for comparison."""
    name = name.strip()
    md_match = re.search(r"\[([^\]]+)\]\(([^)]+)\)", name)
    if md_match:
        target = md_match.group(2).split("#")[0].strip()
        name = Path(target).stem if target.endswith(".md") else md_match.group(1)
    name = name.lower()
    name = re.sub(r"\[\[.*?/", "", name)
    name = re.sub(r"\]\]", "", name)
    name = re.sub(r"_(survey_instrument|survey|exp|experimental)$", "", name)
    name = name.replace("_", " ").replace("-", " ")
    name = re.sub(r"[^\w\s']", "", name)
    return " ".join(name.split())


def extract_keywords(text: str) -> Set[str]:
    """Extract informative tokens from definition or formula text."""
    if not text:
        return set()
    cleaned = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", text.lower())
    cleaned = re.sub(r"\[\[([^\[\]|]+)(?:\|([^\[\]]+))?\]\]", r"\1 \2", cleaned)
    cleaned = re.sub(r"[^\w\s]", " ", cleaned)
    return {w for w in cleaned.split() if len(w) > 2 and w not in STOPWORDS}


def similarity_score(
    name_a: str, def_a: str, name_b: str, title_b: str, def_b: str
) -> Tuple[float, str]:
    """Compute similarity between two entries using name tokens and definition overlap."""
    norm_a = normalize_name(name_a)
    norm_b = normalize_name(name_b)
    norm_title_b = normalize_name(title_b)

    if not norm_a or not norm_b:
        return 0.0, "none"

    name_sim = 0.0
    if norm_a == norm_b or norm_a == norm_title_b:
        return 1.0, "exact_name"
    if norm_a in norm_b or norm_b in norm_a:
        name_sim = 0.80
    elif norm_title_b and (norm_a in norm_title_b or norm_title_b in norm_a):
        name_sim = 0.75
    else:
        tokens_a = set(norm_a.split())
        tokens_b = set(norm_b.split()) | set(norm_title_b.split())
        if tokens_a and tokens_b:
            overlap = len(tokens_a & tokens_b) / min(len(tokens_a), len(tokens_b))
            if overlap >= 0.65:
                name_sim = round(0.65 * overlap, 2)

    def_sim = 0.0
    kw_a = extract_keywords(def_a)
    kw_b = extract_keywords(f"{title_b} {def_b}")
    if kw_a and kw_b:
        inter = len(kw_a & kw_b)
        union = len(kw_a | kw_b)
        min_len = min(len(kw_a), len(kw_b))
        jaccard = inter / union if union else 0.0
        containment = inter / min_len if min_len >= 3 else 0.0
        def_sim = max(jaccard, 0.75 * containment)

    if name_sim >= def_sim:
        return round(name_sim, 2), "name_match"
    return round(def_sim, 2), "definition_overlap"


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


def extract_page_definition(content: str) -> str:
    """Extract core definition, measurement, or computation text from a wiki page."""
    sections = [
        "Definition",
        "What It Measures",
        "Computation",
        "Experimental Operationalization",
        "Description",
        "Overview",
    ]
    collected: List[str] = []
    for sec in sections:
        pattern = rf"^##\s+{re.escape(sec)}\s*\n(.*?)(?=\n##\s+|\Z)"
        match = re.search(pattern, content, re.MULTILINE | re.DOTALL)
        if match:
            sec_text = re.sub(r"^>.*$", "", match.group(1), flags=re.MULTILINE).strip()
            if sec_text:
                collected.append(sec_text[:400])
    return " ".join(collected)[:800]


def load_existing_wiki_pages(wiki_dir: Path, category: str) -> List[Dict[str, str]]:
    """Scan wiki/{category}/*.md directly from disk (never relying on _index.md)."""
    cat_dir = wiki_dir / category
    if not cat_dir.is_dir():
        return []

    entries: List[Dict[str, str]] = []
    for md_file in sorted(cat_dir.glob("*.md")):
        if md_file.name.startswith("_"):
            continue
        try:
            content = md_file.read_text(encoding="utf-8")
        except Exception as exc:
            print(f"Warning: Could not read {md_file}: {exc}", file=sys.stderr)
            continue

        fm = parse_frontmatter(content)
        heading_match = re.search(r"^#\s+(.+)$", content, re.MULTILINE)
        title = fm.get("name") or fm.get("title") or (heading_match.group(1).strip() if heading_match else md_file.stem)
        definition = extract_page_definition(content)
        first_src = fm.get("first_defined") or fm.get("first_used") or fm.get("first_proposed") or ""

        entries.append({
            "name": md_file.stem,
            "title": title,
            "domain": fm.get("domain", ""),
            "first_source": first_src,
            "definition": definition,
            "path": str(md_file),
        })
    return entries


def split_md_row(line: str) -> List[str]:
    stripped = line.strip()
    if stripped.startswith("|"):
        stripped = stripped[1:]
    if stripped.endswith("|"):
        stripped = stripped[:-1]
    return [cell.strip() for cell in re.split(r"(?<!\\)\|", stripped)]


def parse_markdown_tables_by_section(content: str) -> List[Tuple[str, List[str], List[List[str]]]]:
    results: List[Tuple[str, List[str], List[List[str]]]] = []
    current_heading = ""
    lines = content.splitlines()
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        if line.startswith("#"):
            current_heading = line.lstrip("#").strip()
            i += 1
            continue
        if line.startswith("|") and not line.startswith("| >"):
            headers = [h.lower() for h in split_md_row(line)]
            if i + 1 < len(lines) and re.match(r"^\|\s*[-:]+", lines[i + 1].strip()):
                i += 2
                rows: List[List[str]] = []
                while i < len(lines) and lines[i].strip().startswith("|"):
                    row_line = lines[i].strip()
                    if not re.match(r"^\|\s*[-:]+", row_line):
                        rows.append(split_md_row(row_line))
                    i += 1
                results.append((current_heading, headers, rows))
                continue
        i += 1
    return results


def extract_proposed_from_summary(summary_path: Path) -> Dict[str, List[Dict[str, str]]]:
    """Extract proposed wiki pages across all 5 categories and all 4 methodology templates."""
    proposed: Dict[str, List[Dict[str, str]]] = {c: [] for c in CATEGORIES}
    content = summary_path.read_text(encoding="utf-8")

    for heading, headers, rows in parse_markdown_tables_by_section(content):
        if not headers:
            continue
        for row in rows:
            if len(row) < len(headers):
                row = row + [""] * (len(headers) - len(row))
            row_map = dict(zip(headers, row))
            wiki_col = row_map.get("wiki page", row[-1] if row else "")
            if any(skip in wiki_col.lower() for skip in SKIP_MARKERS):
                continue

            md_link_match = re.search(
                r"\[[^\]]+\]\((?:[^)]*/)?(concepts|variables|constructs|methods|theories)/([^)/#]+?)(?:\.md)?(?:#[^)]*)?\)",
                wiki_col,
            )
            wiki_link_match = re.search(r"\[\[(?:(concepts|variables|constructs|methods|theories)/)?([^\[\]|#]+)", wiki_col)
            if md_link_match:
                explicit_cat = md_link_match.group(1)
                linked_name = md_link_match.group(2).strip()
            elif wiki_link_match:
                explicit_cat = wiki_link_match.group(1)
                linked_name = wiki_link_match.group(2).strip()
            else:
                explicit_cat = None
                linked_name = ""

            if "concept" in headers and "definition" in headers:
                cname = linked_name or row_map.get("concept", "").replace(" ", "_")
                if cname and not cname.startswith("{"):
                    proposed["concepts"].append({
                        "proposed": cname,
                        "definition": row_map.get("definition", ""),
                    })
            elif "paper variable" in headers or "dimension" in headers:
                vname = linked_name or row_map.get("wiki name") or row_map.get("dimension", "")
                if any(skip in vname.lower() for skip in SKIP_MARKERS):
                    continue
                defn = (
                    row_map.get("computational definition")
                    or row_map.get("questions grouped")
                    or row_map.get("concept", "")
                )
                if vname and not vname.startswith("{"):
                    proposed["variables"].append({
                        "proposed": vname.replace(" ", "_"),
                        "definition": defn,
                    })
            elif "construct" in headers and ("symbol" in headers or "definition" in headers):
                kname = linked_name or row_map.get("construct", "").replace(" ", "_")
                if kname and not kname.startswith("{"):
                    proposed["constructs"].append({
                        "proposed": kname,
                        "definition": row_map.get("definition", ""),
                    })
            elif "theory" in headers and ("key propositions" in headers or "original source" in headers):
                tname = linked_name or row_map.get("theory", "").replace(" ", "_")
                if tname and not tname.startswith("{"):
                    proposed["theories"].append({
                        "proposed": tname,
                        "definition": row_map.get("key propositions", ""),
                    })
            elif explicit_cat in CATEGORIES and linked_name and not linked_name.startswith("{"):
                proposed[explicit_cat].append({
                    "proposed": linked_name,
                    "definition": " ".join(row),
                })

    for m_match in re.finditer(
        r"(?:Create\s+wiki/methods/|Create\s+\[\[methods/|\[\[methods/|wiki/methods/|\.\./methods/)([A-Za-z0-9_-]+)",
        content,
    ):
        m_name = m_match.group(1).replace(".md", "")
        if m_name and not any(p["proposed"] == m_name for p in proposed["methods"]):
            proposed["methods"].append({"proposed": m_name, "definition": ""})

    return proposed


def discover_pages_by_citekey(wiki_dir: Path, citekey: str) -> Dict[str, List[str]]:
    found: Dict[str, List[str]] = {c: [] for c in CATEGORIES}
    for cat in CATEGORIES:
        cat_dir = wiki_dir / cat
        if not cat_dir.is_dir():
            continue
        for md_file in sorted(cat_dir.glob("*.md")):
            if md_file.name.startswith("_"):
                continue
            try:
                text = md_file.read_text(encoding="utf-8")
            except Exception:
                continue
            fm = parse_frontmatter(text)
            first_ref = f"{fm.get('first_defined', '')} {fm.get('first_used', '')} {fm.get('first_proposed', '')}"
            if citekey in first_ref:
                found[cat].append(md_file.stem)
    return found


def run_collision_check(
    wiki_dir: Path,
    proposed_by_cat: Dict[str, List[Dict[str, str]]],
    exclude_self: bool = False,
    threshold: float = 0.30,
) -> Dict[str, object]:
    report: Dict[str, object] = {}
    total_checked = 0
    exact_matches = 0
    needs_review = 0

    for cat in CATEGORIES:
        items = proposed_by_cat.get(cat, [])
        total_checked += len(items)
        if not items:
            report[cat] = []
            continue

        existing_pool = load_existing_wiki_pages(wiki_dir, cat)
        if exclude_self:
            new_norms = {normalize_name(item["proposed"]) for item in items}
            existing_pool = [
                e for e in existing_pool if normalize_name(e["name"]) not in new_norms
            ]

        cat_results = []
        for item in items:
            prop_name = item["proposed"]
            prop_def = item.get("definition", "")
            if not prop_def and exclude_self:
                page_path = wiki_dir / cat / f"{prop_name}.md"
                if page_path.exists():
                    prop_def = extract_page_definition(page_path.read_text(encoding="utf-8"))

            exact_hit = None
            candidates = []
            for entry in existing_pool:
                score, reason = similarity_score(
                    prop_name, prop_def, entry["name"], entry["title"], entry["definition"]
                )
                if reason == "exact_name":
                    exact_hit = entry["name"]
                    break
                if score >= threshold:
                    candidates.append({
                        "name": entry["name"],
                        "title": entry["title"],
                        "similarity": score,
                        "reason": reason,
                        "definition_preview": entry["definition"][:160],
                    })

            candidates.sort(key=lambda c: c["similarity"], reverse=True)
            if exact_hit:
                exact_matches += 1
                cat_results.append({
                    "proposed": prop_name,
                    "exact_match": exact_hit,
                    "candidates": [],
                })
            elif candidates:
                needs_review += 1
                cat_results.append({
                    "proposed": prop_name,
                    "exact_match": None,
                    "candidates": candidates[:5],
                })

        report[cat] = cat_results

    report["_summary"] = {
        "total_checked": total_checked,
        "exact_matches": exact_matches,
        "needs_semantic_review": needs_review,
        "no_collision": total_checked - exact_matches - needs_review,
    }
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description="Unified Wiki Collision Detector (disk-native, no _index.md)")
    parser.add_argument("--kb-dir", "--root", dest="root", help="Knowledge Base root directory (auto-detected if omitted)")
    parser.add_argument("--summary", help="Pre-creation mode: path to summary markdown file")
    parser.add_argument("--new-pages", help="Post-creation mode: path to JSON file of newly created page names")
    parser.add_argument("--citekey", help="Post-creation mode: auto-discover pages created by citekey")
    parser.add_argument("--threshold", type=float, default=0.30, help="Similarity threshold (default: 0.30)")
    parser.add_argument("--json", action="store_true", help="Output JSON report")
    args = parser.parse_args()

    if not (args.summary or args.new_pages or args.citekey):
        parser.error("Provide one of --summary, --new-pages, or --citekey")

    root_dir = find_workspace_root(args.root)
    wiki_dir = root_dir / "wiki"

    exclude_self = False
    proposed_by_cat: Dict[str, List[Dict[str, str]]] = {c: [] for c in CATEGORIES}

    if args.summary:
        summary_path = Path(args.summary)
        if not summary_path.exists():
            summary_path = root_dir / args.summary
        if not summary_path.exists():
            print(f"Error: Summary file not found: {args.summary}", file=sys.stderr)
            return 1
        proposed_by_cat = extract_proposed_from_summary(summary_path)
    elif args.new_pages:
        exclude_self = True
        np_path = Path(args.new_pages)
        if not np_path.exists():
            np_path = root_dir / args.new_pages
        raw = json.loads(np_path.read_text(encoding="utf-8"))
        for cat in CATEGORIES:
            proposed_by_cat[cat] = [{"proposed": n, "definition": ""} for n in raw.get(cat, [])]
    elif args.citekey:
        exclude_self = True
        discovered = discover_pages_by_citekey(wiki_dir, args.citekey)
        for cat in CATEGORIES:
            proposed_by_cat[cat] = [{"proposed": n, "definition": ""} for n in discovered.get(cat, [])]

    report = run_collision_check(
        wiki_dir=wiki_dir,
        proposed_by_cat=proposed_by_cat,
        exclude_self=exclude_self,
        threshold=args.threshold,
    )

    if args.json:
        print(json.dumps(report, indent=2, ensure_ascii=False))
    else:
        print("# Wiki Collision Report")
        for cat in CATEGORIES:
            items = report.get(cat, [])
            if not items:
                continue
            print(f"\n## {cat}")
            print("| Proposed Page | Exact Match | Candidates |")
            print("| :--- | :--- | :--- |")
            for item in items:
                exact = item["exact_match"] or "-"
                cands = ", ".join(f"{c['name']} ({c['similarity']})" for c in item["candidates"]) or "-"
                print(f"| {item['proposed']} | {exact} | {cands} |")
        s = report["_summary"]
        print(
            f"\nSummary: {s['total_checked']} checked | {s['exact_matches']} exact | "
            f"{s['needs_semantic_review']} review | {s['no_collision']} clean"
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
