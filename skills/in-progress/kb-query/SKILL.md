---
name: kb-query
description: Standalone, directory-agnostic skill to query an academic Knowledge Base (wiki concepts, variables, constructs, methods, theories, and paper summaries) using an rg-first search workflow. Works inside the KB root or from any external research project workspace once given the KB directory path.
---

# kb-query - Standalone Knowledge Base Query & Synthesis

Query your academic Knowledge Base from **any research workspace** to synthesize literature answers, compare variable operationalizations, inspect empirical/theoretical ground truths, and trace citations using Obsidian `[[wikilinks]]`.

This skill is **100% standalone**: you can drop `kb-query/` into any research repository's skill folder and point it at your Knowledge Base directory anywhere on disk.

## Usage Patterns

- `/kb-query "{question}"` - Synthesize an answer from the knowledge base with `[[wikilink]]` citations
- `/kb-query "{question}" --kb-dir /path/to/kb` - Query a knowledge base located in a specific external directory
- `/kb-query "{topic}" --papers` - Find and compare all paper summaries related to a topic or methodology
- `/kb-query "{concept}" --deep` - Deep dive into a concept and all its 1-hop linked variables, constructs, theories, and source papers

## Step 0: Resolve Target Knowledge Base Directory (`KB_ROOT`)

Because `kb-query` often runs inside an external empirical or theoretical research workspace rather than inside the Knowledge Base folder itself, **always resolve `KB_ROOT` first** using this priority order:

1. **Explicit path in user prompt or `--kb-dir <path>`**:
   - If the user provides a directory path in their message (e.g., *"Search my KB at `~/research/accounting-kb` for..."* or `--kb-dir /path/to/kb`), verify that `<path>/wiki` or `<path>/source/summary` exists.
   - Persist this path to `.kb_root` in the current working directory so subsequent queries in this workspace remember it automatically:
     ```bash
     python3 "<skill_dir>/scripts/kb_search.py" --kb-dir "/path/to/kb" --save-kb-dir --stats
     ```
2. **Saved `.kb_root` file or `$KB_ROOT` environment variable**:
   - Check if `.kb_root` exists in the current working directory (`cat .kb_root`) or if `$KB_ROOT` is set in the environment.
   - Also check `docs/agents/research-context.md` if present in the repo for a configured `KB_ROOT` or `knowledge_base_dir` path.
3. **Current Working Directory (`./`)**:
   - Check if `./wiki/` and `./source/summary/` exist directly in the current working directory. If so, `KB_ROOT="."`.
4. **Ask the User Once (If Unconfigured)**:
   - If none of the above resolve to a valid directory containing `wiki/` or `source/summary/`, ask the user:
     *"Which directory holds your Knowledge Base (the folder containing `wiki/` and `source/summary/`)? Once you share the path, I'll save it to `.kb_root` for this workspace."*

## Knowledge Base Directory Schema (Self-Contained Reference)

Once `KB_ROOT` is resolved, all files live under `$KB_ROOT` (there are **no `_index.md` files**; the filesystem is the single source of truth):

| Path under `$KB_ROOT` | Content & Structure |
| :--- | :--- |
| `wiki/concepts/{Concept}.md` | Abstract theoretical definitions, `## Alternative Definitions`, `## Constructs & Variables` table, `## Related Theories`, `## Determinants`, `## Economic Consequences`, `## Identification Strategy`, and `## Future Works`. |
| `wiki/variables/{Variable}.md` | Observable/computational measures (`variable.md`), experimental manipulations/DVs (`{var}_exp.md`), or survey question dimensions (`{dim}_survey.md`). Contains `## What It Measures`, `## Computation` (or `## Experimental Operationalization` / `## Response Scale`), `## Validity Notes`, `## Papers Using`, and `## Interpretations`. |
| `wiki/constructs/{Construct}.md` | Analytical model parameters (e.g., $\lambda$, $\sigma^2$) and definitional constructs (`## Definition`, `## Mathematical Representation`, `## Role in Model`, `## Papers Defining/Using`). |
| `wiki/methods/{Method}.md` | Novel econometric identification designs (`method.md`), baseline analytical models + variations (`method_analytical.md`), novel experimental designs (`{design}_experimental.md`), and validated survey instruments (`{instrument}_survey_instrument.md`). |
| `wiki/theories/{Theory}.md` | Core theoretical frameworks (`## Description`, `## Key Concepts`, `## Key Propositions/Claims`, `## Evidence Supporting`, `## Criticisms & Limitations`). |
| `source/summary/{citekey}_summary.md` | Structured paper summaries classified by `paper_type` (`archival`, `experimental`, `survey`, `analytical`) plus `{citekey}_review.md` for literature reviews. Every summary separates **Claimed Findings** (authors' theoretical story) from **Ground Truth Findings** (exact coefficients, $p$-values, $n$, survey percentages, or Theorems/Propositions). |
| `source/conversations/` | Saved multi-source Q&A syntheses (`{theme}_{YYMMDD}.md`). |

## Step 1: Execute the 3-Tier Search Hierarchy (`rg` First)

Never look for `_index.md` files. Always search `$KB_ROOT/wiki` and `$KB_ROOT/source/summary` using this strict tool priority:

### Priority 1: `rg` (ripgrep via CLI): Primary Fast Path

1. **Check existing files by filename**:
   ```bash
   rg --files "$KB_ROOT/wiki" "$KB_ROOT/source/summary" | rg -i "{keyword1}|{keyword2}"
   ```
2. **Search YAML frontmatter, headings, definitions, and formulas**:
   ```bash
   rg -i -n -C 2 "{keyword1}|{keyword2}" "$KB_ROOT/wiki" "$KB_ROOT/source/summary"
   ```
3. **Or run the bundled `kb_search.py` helper** (which wraps `rg` automatically and resolves `.kb_root` / `--kb-dir`):
   ```bash
   # Keyword/regex search across wiki and summaries:
   python3 "<skill_dir>/scripts/kb_search.py" --kb-dir "$KB_ROOT" --query "{keyword1}|{keyword2}"

   # Deep 1-hop graph expansion for a specific concept page:
   python3 "<skill_dir>/scripts/kb_search.py" --kb-dir "$KB_ROOT" --deep "{concept_name}"
   ```

### Priority 2: `grep` / `find` (POSIX CLI Fallback if `rg` is not installed)

If `rg` returns command not found:

```bash
# 1. Filename discovery:
find "$KB_ROOT/wiki" "$KB_ROOT/source/summary" -type f -iname "*{keyword}*.md"

# 2. Content search with line numbers and context:
grep -rnI -i -C 2 "{keyword}" "$KB_ROOT/wiki" "$KB_ROOT/source/summary"
```

### Priority 3: Agent Built-in Tools (`Grep` / `Glob` / `Search`)

Use the host agent's built-in `Glob` and `Grep` tools scoped to `$KB_ROOT/wiki/` and `$KB_ROOT/source/summary/` **only** if Bash command execution is disabled or unavailable.

## Step 2: Read & Traverse Candidate Pages

### Standard Query Mode
1. Read the top matching `wiki/concepts/*.md`, `wiki/variables/*.md`, or `wiki/constructs/*.md` files.
2. Follow the `[[source/summary/{citekey}_summary]]` wikilinks inside those wiki pages to read the underlying paper summaries in `$KB_ROOT/source/summary/` whenever you need exact regression coefficients, $p$-values, sample sizes, experimental manipulations, or theorem conditions.

### `--papers` Mode (`/kb-query "{topic}" --papers`)
1. Search `$KB_ROOT/source/summary/` via `rg -i -n -C 3 "{topic}" "$KB_ROOT/source/summary"`.
2. Read the matched summary files, extract their YAML frontmatter (`title`, `authors`, `year`, `journal`, `paper_type`), and compare their **Claimed Findings** vs. **Ground Truth Findings**.

### `--deep` Mode (`/kb-query "{concept}" --deep`)
1. Run `python3 "<skill_dir>/scripts/kb_search.py" --kb-dir "$KB_ROOT" --deep "{concept}"` (or use `rg -o "\[\[[^\]]+\]\]" "$KB_ROOT/wiki/concepts/{concept}.md"`).
2. Read the focal concept page AND all 1-hop linked pages across:
   - `wiki/variables/` and `wiki/constructs/` (how the concept is operationalized across archival, experimental, survey, and analytical papers)
   - `wiki/theories/` and `wiki/methods/` (theoretical grounding and identification strategies)
   - `source/summary/` (primary papers defining or testing the concept)

## Step 3: Synthesize with Grounded `[[Wikilink]]` Citations

Structure your response clearly and ground every claim in the retrieved files:

```markdown
{Direct synthesis answering the question}

### Key Findings & Operationalizations
- **Concept Definition**: ... ([[concepts/{Concept}]])
- **Empirical / Theoretical Evidence**: ... ([[source/summary/{citekey}_summary]])
- **Measures & Proxies**: ... ([[variables/{Variable}]])

### Sources Consulted
- [[concepts/{Concept}]]: {contribution}
- [[variables/{Variable}]]: {formula / operationalization}
- [[source/summary/{citekey}_summary]]: {authors, year, journal, exact Ground Truth finding}
```

### Rules for Synthesis
- **Strict Groundedness**: Never fabricate citations, coefficients, or variable formulas not present in `$KB_ROOT`. If an aspect is missing from the KB, state the gap explicitly.
- **Preserve Honesty to Paper vs. Wiki Name**: Mention both the canonical Wiki Variable Name (`[[variables/Peer_Selection_Count]]`) and the exact paper variable (`InDegree`) when citing empirical results.

## Step 4: Auto-Suggest Saving Valuable Syntheses

If your synthesis references **3+ wiki/summary pages**, bridges **multiple categories** (e.g., concepts + variables + summaries), and exceeds **150 words**, offer at the end of your reply:

> 💡 Want to save this synthesis to your Knowledge Base at `$KB_ROOT/source/conversations/{theme}_{YYMMDD}.md`? Reply "yes" to save.

If the user confirms:
1. Write the Q&A and `[[wikilink]]` sources to `$KB_ROOT/source/conversations/{theme}_{YYMMDD}.md`.
2. Append a log entry to `$KB_ROOT/wiki/log.md`:
   `## [YYYY-MM-DD] query-save | {theme}_{YYMMDD}.md | {question}`
