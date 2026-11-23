---
name: kb-ingest
description: Ingest academic papers by DOI, title, citekey, or local PDF into the Knowledge Base using libby, paddle-pdf, methodology templates, collision checks, and Obsidian wiki pages. Use for /kb-ingest.
disable-model-invocation: true
---

# kb-ingest - Paper Ingestion Pipeline

Ingest academic papers across **economics, finance, accounting, management science, and marketing** into the Knowledge Base (`source/summary/` and `wiki/`).

## Search & Discovery Rule (`rg`-First Priority)

Never read or maintain `_index.md` files. Whenever checking existing wiki pages or paper summaries, follow this strict priority order:

1. **Priority 1 (`rg` CLI)**:
   - Filename lookup: `rg --files wiki/ source/summary/ | rg -i "{keyword}"`
   - Content/definition search: `rg -i -n -C 2 "{keyword}" wiki/ source/summary/`
2. **Priority 2 (`grep` / `find` CLI fallback)**:
   - `find wiki/ source/summary/ -type f -iname "*{keyword}*.md"`
   - `grep -rnI -i -C 2 "{keyword}" wiki/ source/summary/`
3. **Priority 3 (Agent Built-in tools)**:
   - Built-in `Grep` / `Glob` tools only when shell execution is disabled.

## Execution Architecture (Inline vs. Subagent)

- **Single-Paper Mode (`/kb-ingest <doi|title|citekey|pdf>`)**:
  Execute Phases 1–4 **inline in the main agent** without spawning a subagent. Running inline for a single paper avoids subagent file-path resolution errors and eliminates duplicate reading between subagent and orchestrator.
- **Batch Mode (`/kb-ingest --batch` or 2+ papers)**:
  1. **Orchestrator Upfront Prep**: Run Phase 1 (`libby`) and Phase 2 (`paddle-pdf convert ... -o raw/papers/ --jobs 3`) across all papers first.
  2. **Per-Paper Subagent (Phase 3)**: Dispatch **one self-contained subagent per paper** in a **fresh context window** (never fork the parent conversation), passing explicit, verified file paths:
     - Paper markdown: `raw/papers/{citekey}/{citekey}.md`
     - BibTeX metadata: `raw/papers/{citekey}/{citekey}.bib`
     - Extraction rules: `<skill_dir>/references/extraction-rules.md`
     - Wiki rules: `<skill_dir>/references/wiki-rules.md`
     - Pre-selected summary template: `<skill_dir>/templates/summary/paper_summary_{type}.md`
     - Wiki templates folder: `<skill_dir>/templates/wiki/`
     The subagent must complete the summary and candidate wiki pages itself and **must never dispatch sub-sub-agents**.
  3. **Orchestrator Finalize (Phase 4)**: Run `check_related_papers.py`, `check_collision.py`, and `kb_lint.py` across the batch.

## Phase 1: Paper Acquisition (`libby` CLI)

1. **Case A (DOI provided: `/kb-ingest 10.xxxx/yyyy`)**:
   `libby fetch` extracts metadata, downloads the PDF across its built-in cascade (`crossref -> unpaywall -> s2 -> core -> arxiv -> pmc -> biorxiv -> scihub`), and writes `raw/papers/{citekey}/{citekey}.{pdf,bib}`:
   ```bash
   libby fetch "{doi}" -o raw/papers/
   ```
2. **Case B (Title provided: `/kb-ingest "Paper Title"`)**:
   ```bash
   libby extract "{title}" -f json
   # Parse DOI from JSON stdout, then fetch PDF and BibTeX into raw/papers/:
   libby fetch "{doi}" -o raw/papers/
   ```
3. **Case C (Local PDF in `raw/data/`)**:
   - **Step 0 (Well-organized folder shortcut)**: If `raw/data/{folder}/` already contains both `{citekey}.pdf` and `{citekey}.bib`, move it directly (`mv "raw/data/{folder}" raw/papers/`) and skip to Phase 2.
   - **Step 1 (Standard metadata extraction)**:
     ```bash
     libby extract "{pdf_path}" -f json
     ```
   - **Step 2 (Google Scholar SerpAPI fallback if Step 1 fails)**:
     ```bash
     libby extract "{pdf_path}" --serpapi auto -f json
     ```
   - **Step 3 (Scanned PDF fallback)**: Render page 1 (`pdftoppm -png -f 1 -l 1 "{pdf_path}" raw/data/temp_page` or `paddle-pdf convert "{pdf_path}" --pages 1 -o raw/data/`), read the paper title/DOI from page 1, and run:
     ```bash
     libby extract "{pdf_path}" --with-title "{extracted_title}" -f json
     rm -f raw/data/temp_page*.png
     ```

## Phase 2: PDF-to-Markdown Conversion (`paddle-pdf` CLI)

Per `Yugikira/paddle-pdf`, `paddle-pdf convert <doc.pdf> -o <out_dir>` automatically creates a subdirectory named `<out_dir>/<stem>/<stem>.md` along with `<out_dir>/<stem>/images/` and `<out_dir>/<stem>/output.json`.

1. Check if `raw/papers/{citekey}/{citekey}.md` already exists.
2. If not, convert by passing `-o raw/papers/` (never pass `-o raw/papers/{citekey}/`, which double-nests `{citekey}/{citekey}/`):
   ```bash
   # Single PDF:
   paddle-pdf convert "raw/papers/{citekey}/{citekey}.pdf" -o raw/papers/

   # Batch mode (parallel conversion with 3 workers):
   paddle-pdf convert raw/papers/*/*.pdf -o raw/papers/ --jobs 3
   ```
3. If any task fails and writes `fail_task.json`, recover via `paddle-pdf resume job <job_id>`.

## Phase 3: Methodology Classification, Summary & Wiki Creation

1. **Classify Methodology & Select Summary Template**:
   Read `<skill_dir>/references/extraction-rules.md` and inspect the paper's headings/abstract (`rg -n "^#+ " "raw/papers/{citekey}/{citekey}.md"`):

   | Methodology | Recognition Criteria | Template File |
   | :--- | :--- | :--- |
   | **Archival** | Observational/archival data, econometric regressions | `templates/summary/paper_summary_archival.md` |
   | **Experimental** | Lab/field treatment manipulation, control group, subjects | `templates/summary/paper_summary_experimental.md` |
   | **Survey** | Questionnaires, interviews, Likert scales, Cronbach's alpha | `templates/summary/paper_summary_survey.md` |
   | **Analytical** | Formal mathematical model, theorems/propositions, no sample data | `templates/summary/paper_summary_analytical.md` |
   | **Review** | Literature survey synthesizing an existing concept | `templates/summary/paper_summary_review.md` |

2. **Create Structured Summary (`source/summary/{citekey}_summary.md`)**:
   - Follow `<skill_dir>/references/extraction-rules.md`.
   - Write 3–5 **Claimed Findings** first, then 3–5 **Ground Truth Findings** where Finding $N$ directly supports Claim $N$ using exact paper variable names, coefficients, $p$-values, and sample sizes (or Theorem/Proposition statements for analytical models).
   - Run the built-in **Self-Verification Checklist** (in `references/extraction-rules.md` Section 7) to verify every Ground Truth variable has a complete computational definition or operationalization.

3. **Link Related Papers**:
   ```bash
   python3 "<skill_dir>/scripts/check_related_papers.py" --summary "source/summary/{citekey}_summary.md" --update
   ```

4. **Check Wiki Collisions (`rg` + `check_collision.py`) & Create/Update Wiki Pages**:
   - Run the disk-native collision detector before creating wiki files:
     ```bash
     python3 "<skill_dir>/scripts/check_collision.py" --summary "source/summary/{citekey}_summary.md" --json
     ```
   - Also run targeted `rg -i "{concept_or_variable}" wiki/` searches across categories.
   - Follow `<skill_dir>/references/wiki-rules.md` and `<skill_dir>/templates/wiki/*.md`:
     - **If same underlying phenomenon / transform**: Merge into the existing wiki page (update `Papers Using`, `Alternative Definitions`, or `Model Variations`).
     - **If genuinely distinct**: Create the new wiki page using the matching template in `templates/wiki/`.

## Phase 4: Post-Ingest Collision Audit & Logging

1. **Post-Ingest Collision Verification (for Batch Mode)**:
   ```bash
   python3 "<skill_dir>/scripts/check_collision.py" --citekey "{citekey}" --json
   ```
   Resolve any remaining `exact_match` or high-similarity candidates by reading both definitions at the phenomenon level (`merge_into_existing`, `create_crosslink`, `rename_new_page`, or `keep_new`).
2. **Append to `wiki/log.md`**:
   ```markdown
   ## [YYYY-MM-DD] ingest | {citekey} | {paper_type} | {title}
   - Summary: [[source/summary/{citekey}_summary]]
   - Created/Updated: [[concepts/...]], [[variables/...]]
   ```
3. **Consolidation Trigger**: When 10+ new papers have been ingested in batch mode, recommend running `/kb-consolidate`.
