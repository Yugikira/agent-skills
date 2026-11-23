---
name: kb-consolidate
description: Audit and consolidate Knowledge Base wiki pages by merging duplicate concepts/variables, removing misplaced entries, and applying top-journal filtering. Use for /kb-consolidate.
disable-model-invocation: true
---

# kb-consolidate - Wiki Consolidation and Cleanup

Maintain wiki quality as papers accumulate by auditing `wiki/concepts/`, `wiki/constructs/`, and `wiki/variables/`. Read [references/consolidation-rules.md](references/consolidation-rules.md) for the full checklists, Canonical + Cross-Link merge rules, detection patterns, and top-journal list before auditing or editing.

## Usage

```text
/kb-consolidate                          # Full audit: all types, all sections
/kb-consolidate --concepts               # Audit only concept pages
/kb-consolidate --constructs             # Audit only construct pages
/kb-consolidate --variables              # Audit only variable pages
/kb-consolidate {name}                   # Audit specific wiki page
/kb-consolidate {name} --section {sec}   # Audit specific section in specific page
```

Valid sections for `--section`:
- concepts: `definition`, `variables`, `determinants`, `consequences`, `identification`
- constructs: `papers-defining`, `papers-using`
- variables: `interpretations`, `papers-using`

## Execution Phases

### Phase 1: Scope Detection

1. Parse user arguments (type filter, page filter, section filter).
2. Resolve `KB_ROOT` (from `--kb-dir`, `.kb_root`, `$KB_ROOT`, or `./`) and list target files using `rg --files` first (fallback to `find` or built-in `Glob`):
   - `--concepts`: `rg --files "<kb_root>/wiki/concepts"`
   - `--constructs`: `rg --files "<kb_root>/wiki/constructs"`
   - `--variables`: `rg --files "<kb_root>/wiki/variables"`
   - No filter: scan all three directories.
3. If a specific page is given, read that page only.

### Phase 2: Issue Detection

Load [references/consolidation-rules.md](references/consolidation-rules.md). For each wiki page in scope, read the full file and flag:
- **Similar variables** (identical formula or same underlying phenomenon across indicator/capped/log/count transforms)
- **Incorrect variables** (formula does not measure the concept)
- **Duplicate entries** (same base definition, determinant, or consequence split by parenthetical qualifiers)
- **Misplaced items** (moderators, behavioral responses, or validity tests listed as consequences)
- **Unfiltered tables** (>5 paper entries without oldest + newest top-journal filtering)

### Phase 3: Cross-File Similar Concept Detection

Compare concept pages for definition keyword overlap, >50% shared variables, or >50% shared theories. Flag pairs above 70% similarity for manual user decision; never auto-merge distinct concepts without approval.

### Phase 4: Audit Report & User Approval

Present a structured report listing pages audited, issue counts by type, a per-page table (`Issue Type | Entry | Fix | Details`), and any high-similarity concept pairs needing manual review.

Stop and ask the user for approval (`Apply these fixes? (Y/n)`) before modifying any wiki page.

### Phase 5: Execute Approved Fixes

After user approval, apply fixes sequentially:
1. **Variable merges**: Create/update canonical variable page, convert alternatives to cross-link stubs, and update the parent concept's `Constructs & Variables` table.
2. **Section moves**: Relocate moderators to `Heterogeneity`, behavioral responses to `Determinants` / `Behavioral Response`, and validity tests to `Validity Tests`.
3. **Top-journal filtering**: Trim >5-row reference tables to oldest seminal + newest top-journal papers.
4. **Integrity check**: Preserve all relative Markdown file links and run `kb_lint.py` (if available) to confirm zero newly broken links.

### Phase 6: Summary

Report pages modified, issues fixed by type, cross-links created, and any remaining manual-review concept pairs.
