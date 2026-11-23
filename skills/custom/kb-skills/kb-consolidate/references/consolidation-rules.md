# Consolidation Checklists, Detection Patterns & Examples

Load this reference during Phase 2 and Phase 6 of `kb-consolidate`.

## Top-Journal Filtering Criteria

Apply to all tables with paper references (max 5 entries):
- **Oldest from Top journals**: earliest seminal paper
- **Newest from Top journals**: latest usage

**Top Journals by Domain:**
- Economics: AER, JPE, QJE, Econometrica, RES
- Finance: JF, RFS, JFE, JFQA, RoF
- Accounting: TAR, CAR, JAR, RAST, JAE

## Verification Checklists

### Concepts

| Check | Section | Issue Pattern | Fix |
|-------|---------|---------------|-----|
| Duplicate definitions | Definition, Alternative Definitions | Same definition from different papers | Keep oldest + note variations |
| Similar variables | Constructs & Variables | Different names measuring same underlying phenomenon (count, log, capped, indicator variants) | Create canonical + cross-links with formula notes |
| Incorrect variables | Constructs & Variables | Variable not measuring concept | Remove or move to appropriate section |
| Duplicate determinants | Determinants | Same determinant with different measurement names | Consolidate with mechanism variations |
| Duplicate consequences | Economic Consequences | Same consequence with parenthetical qualifiers | Merge + add Heterogeneity note |
| Misplaced moderators | Economic Consequences | "X moderation", "who benefits more" | Move to Heterogeneity subsection |
| Misplaced behavioral responses | Economic Consequences | What subjects DO vs outcome | Move to Determinants |
| Misplaced validity tests | Economic Consequences | "validate", "confirm", "rule out" | Move to Validity Tests section |
| Top-journal filtering | All tables | >5 entries without filtering | Apply oldest + newest criteria |

### Constructs

| Check | Section | Issue Pattern | Fix |
|-------|---------|---------------|-----|
| Duplicate definitions | Papers Defining | Same construct defined differently | Keep oldest top-journal + note variations |
| Missing top-journal filter | Papers Defining/Using | >5 entries unfiltered | Keep oldest + newest from top journals |

### Variables

| Check | Section | Issue Pattern | Fix |
|-------|---------|---------------|-----|
| Similar computation | Computation | Different names measuring same underlying phenomenon (count, log, capped, indicator variants) | Create canonical + cross-links with formula notes |
| Duplicate interpretations | Interpretations | Same interpretation from different papers | Keep oldest + newest top-journal |
| Missing top-journal filter | Interpretations | >5 entries unfiltered | Apply oldest + newest criteria |

## Canonical + Cross-Link Merge Strategy

When similar variables measure the same underlying phenomenon with different formulas:

1. **Identify canonical**: most commonly used name OR most precise formula (log preferred over capped, continuous preferred over indicator).
2. **Create canonical variable page** with combined sources.
3. **Convert alternative names into cross-link pages**:
   ```markdown
   > **Canonical Variable**: [{canonical}]({canonical}.md)
   > This is an alternative operationalization of {underlying_measurement}.
   > Formula: {alt_formula} (vs canonical's {canonical_formula})
   ```
4. **Update concept "Constructs & Variables" table**:
   - Keep canonical entry only.
   - Add note: `Also measured as: {alt1} ({formula_type1}), {alt2} ({formula_type2})` (types: capped, indicator, log, raw count, ratio).
   - Source oldest + newest top-journal papers for each variant.

## Detection Patterns

### Similar Variables

- **Type A (Identical Computation)**: Same formula with different names (e.g., `Ln(NVisit)` and `Visit_Num` both defined as `ln(1 + number of site visits)`). Normalize whitespace and notation, then flag 100% matches.
- **Type B (Same Underlying Measurement)**: Different operationalizations (indicator, capped count, log, raw count, ratio) of the same phenomenon and data source (e.g., `Visit`, `Visit_freq`, `Ln(NVisit)`, `Visit_Num` all measure visitor count). Group by underlying measurement target and consolidate via Canonical + Cross-Link.

### Incorrect Variables (Not Measuring Concept)

Flag variables whose computational formula measures a different outcome than the concept definition (e.g., `ABN_ABSAR` measures stock returns, not corporate site visits).

### Duplicate Consequences (Parenthetical Qualifiers)

Strip parenthetical qualifiers (`Stock price impact (overall)`, `(info env)`, `(manufacturing)`). When the same base consequence appears more than once, merge into one row and fold qualifiers into a **Heterogeneity** note.

### Misplaced Items

- **Moderators** ("moderation", "who benefits", "when effect stronger", "amplifies", "heterogeneity"): Move to **Heterogeneity** subsection under the main consequence.
- **Behavioral Responses** ("decisions", "choices", "behavior", "response", "adjustment"): Distinction is what subjects DO vs. outcomes that HAPPEN TO them. Move to **Determinants** or a **Behavioral Response** subsection.
- **Validity Tests** ("validate", "confirm", "rule out", "falsification", "robustness", "alternative explanation"): Move to **Validity Tests** section.

## Proper Structure Template (Concepts)

```markdown
## Economic Consequences of {Concept}

{Concept} generates {N} primary outcomes: {outcome1}, {outcome2}.

### {Outcome Category 1}

| Consequence | Mechanism | Key Paper | Finding |
|-------------|-----------|-----------|---------|
| {Main consequence} | {Mechanism} | [{citekey}_summary](../../source/summary/{citekey}_summary.md) | {Key statistic} |

**Heterogeneity**: Effects stronger for {condition1}, {condition2}; weaker for {condition3}.

## Validity Tests

| Test | Purpose | Key Paper | Finding |
|------|---------|-----------|---------|
| {Falsification test} | Rule out {alternative} | [{citekey}_summary](../../source/summary/{citekey}_summary.md) | {Result} |
```

## Before/After Examples

- **Corporate_Site_Visit**: 16 mixed Economic Consequences entries reduced to 3 categories with Heterogeneity notes + Validity Tests section; `Ln(NVisit)`, `Visit_Num`, `Visit_freq` merged into canonical `Ln_NVisit` with cross-links; `ABN_ABSAR` removed as non-proxy.
- **Information_Acquisition**: Duplicate determinants merged; misplaced behavioral response moved to Behavioral Response subsection.
