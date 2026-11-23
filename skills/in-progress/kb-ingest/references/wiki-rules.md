# Wiki Page Creation, Filtering & Semantic Collision Rules

This reference defines which wiki pages to create vs. skip, how to name them across methodologies, and how to resolve semantic duplicates using `rg` and `scripts/check_collision.py`.

## 1. Template Mapping by Category & Methodology

All wiki templates live in `templates/wiki/`:

| Category | Methodology | Template | Naming Convention |
| :--- | :--- | :--- | :--- |
| **Concepts** | All | `templates/wiki/concept.md` | `wiki/concepts/{Concept_Name}.md` |
| **Constructs** | Analytical | `templates/wiki/construct.md` | `wiki/constructs/{Construct_Name}.md` |
| **Theories** | All | `templates/wiki/theory.md` | `wiki/theories/{Theory_Name}.md` |
| **Variables** | Archival | `templates/wiki/variable.md` | `wiki/variables/{Descriptive_Wiki_Name}.md` |
| **Variables** | Experimental | `templates/wiki/variable_experimental.md` | `wiki/variables/{Variable_Name}_exp.md` |
| **Variables** | Survey | `templates/wiki/variable_survey.md` | `wiki/variables/{Dimension_Name}_survey.md` |
| **Methods** | Archival (novel only) | `templates/wiki/method.md` | `wiki/methods/{Method_Name}.md` |
| **Methods** | Analytical | `templates/wiki/method_analytical.md` | `wiki/methods/{Baseline_Model_Name}.md` |
| **Methods** | Experimental (novel only) | `templates/wiki/method_experimental.md` | `wiki/methods/{Design_Name}_experimental.md` |
| **Methods** | Survey (novel instrument) | `templates/wiki/method_survey_instrument.md` | `wiki/methods/{Instrument_Name}_survey_instrument.md` |

## 2. Filtering Rules: What to Create vs. Skip

### 2.1 Variables (`wiki/variables/`)
- **CREATE** for:
  - **Archival**: Directly measurable raw counts, binary indicators (0/1), ratios from raw data, network statistics (degree, clustering), and observable firm/manager events.
  - **Experimental**: Measured dependent variables (outcomes) and manipulated independent variables (treatments), documented with `{name}_exp.md`.
  - **Survey**: Multi-question dimensions (`{dimension}_survey.md`) with response scales and reliability metrics (Cronbach's alpha). Never create one page per individual question.
- **SKIP (`[no wiki]` / `[derived]`)** for:
  - Principal components (PCA), composite indices combining multiple distinct proxies, standardized z-scores, regression residuals/fitted values, non-descriptive generic names, routine control variables, and unmanipulated subject demographics.

### 2.2 Methods (`wiki/methods/`)
- **SKIP** for:
  - Standard econometric estimators: OLS, Fixed Effects, Random Effects, standard t/F/Hausman/White tests.
  - Standard causal designs: routine 2SLS, GMM, standard DiD exploiting a regulatory/law shock, standard RDD without a novel threshold mechanism.
  - Standard experimental designs (simple post-test control group) or already-documented survey scales.
- **CREATE** for:
  - **Archival**: Novel identification strategies, non-regulatory natural experiment designs, new econometric estimators or measurement algorithms.
  - **Analytical**: Foundational baseline models (e.g., `Noisy_Rational_Expectations_Model.md`). When a subsequent paper modifies assumptions of an existing baseline model, **append a row to the `Model Variations` table** on the baseline model's page rather than creating a separate method file.
  - **Experimental**: Novel laboratory/field designs or incentive-compatible mechanisms (`{design}_experimental.md`).
  - **Survey**: Newly developed and validated survey instruments (`{instrument}_survey_instrument.md`).

### 2.3 Constructs (`wiki/constructs/`)
- Used for **Analytical Model** papers to record innovative model parameters ($\lambda$, $\sigma_\epsilon^2$) and formal definitional constructs (e.g., `Informed_Traders`, `Price_Informativeness`).
- Apply top-journal filtering (max 5 entries: oldest seminal + newest top-journal extensions).

## 3. Pre-Creation Semantic Check (`rg` + `check_collision.py`)

Before creating any file in `wiki/{category}/`, run:

```bash
# 1. Automated collision scan against all existing wiki/*.md files:
python3 "<skill_dir>/scripts/check_collision.py" --summary "source/summary/{citekey}_summary.md" --json

# 2. Fast rg check for related terms across all categories:
rg -i -n "{core_keyword}" wiki/
```

### Category-Specific Merge vs. Separate Rules

| Category | MERGE Into Existing Page When... | KEEP SEPARATE (With Cross-Link) When... |
| :--- | :--- | :--- |
| **Concepts** | Mathematical reciprocal (`Market-to-Book` vs `Book-to-Market`), specific window/subset (`Announcement_CAR` $\subset$ `Cumulative_Abnormal_Returns`), prefix/suffix variant (`Reporting_Conservatism` vs `Conservatism`), or same phenomenon in different words. | Distinct underlying economic mechanism (e.g., `Timeliness` vs `Asymmetric_Timeliness`) or cause vs. consequence. |
| **Variables** | Mathematical reciprocal (`M/B` vs `B/M`), log transform (`ln(MarketCap)` vs `MarketCap`), same formula with different label, or different event window of the same measure (`3-day CAR` vs `5-day CAR`). | Different formulas measuring the same concept (keep separate or use Canonical + Cross-Link pattern in `kb-consolidate`). |
| **Methods** | Same core regression/procedure under a different name (`Basu Regression` vs `Asymmetric Timeliness Model`) or extension of an existing analytical baseline model. | Genuinely different identification mechanism or distinct mathematical model family. |
| **Constructs** | Same parameter symbol and role within the same analytical model family across papers. | Same Greek symbol used with a completely different economic meaning in an unrelated model. |
| **Theories** | Spelling/phrasing variation of the same theory (`Contracting Theory` vs `Contract Theory`). | Competing theoretical explanations (`Agency Theory` vs `Signaling Theory`). |

## 4. Cross-Linking & Top-Journal Conventions

- Always use Obsidian `[[category/Page_Name]]` links and `[[source/summary/{citekey}_summary]]` citations.
- When updating an existing wiki page with a new paper, add the paper to `Papers Using` / `Constructs & Variables` / `Economic Consequences` while respecting the **Top-Journal Cap** (max 5 rows per table: keep the **oldest seminal** papers + **newest** papers from top journals: AER, JPE, QJE, Econometrica, RES; JF, RFS, JFE, JFQA, RoF; TAR, CAR, JAR, RAST, JAE; AMJ, AMR, SMJ, OS; JMR, JM, MS, JCR).
