# Paper Extraction & Ground Truth Verification Rules

This reference consolidates all methodology-specific paper extraction rules (`archival`, `experimental`, `survey`, `analytical`, `review`) and the Ground Truth reproducibility verification checklist.

## 1. Methodology Selection & Summary Templates

| Paper Type | Recognition Criteria | Summary Template |
| :--- | :--- | :--- |
| **Archival** | Existing observational data sources, econometric regressions | `templates/summary/paper_summary_archival.md` |
| **Experimental** | Manipulated variables, treatment/control groups, human subjects | `templates/summary/paper_summary_experimental.md` |
| **Survey** | Questionnaires, interviews, respondent opinions/judgments/knowledge | `templates/summary/paper_summary_survey.md` |
| **Analytical** | Formal mathematical model, proofs/theorems, no empirical sample | `templates/summary/paper_summary_analytical.md` |
| **Review** | Literature survey synthesizing findings on a core concept | `templates/summary/paper_summary_review.md` |

## 2. Core Extraction Rules (All Methodologies)

### 2.1 Claimed Findings vs. Ground Truth Findings
1. **Claimed Findings FIRST (3–5 key interpretations)**: State the authors' main theoretical story and interpretations.
2. **Ground Truth Findings SECOND (3–5 objective empirical or mathematical results)**:
   - **Correspondence Rule**: Ground Truth Finding $N$ must directly support Claimed Finding $N$.
   - **Archival Format**: `{Paper Variable X} (defined as [exact formula]) has β=YY (p<ZZ) in [model] (n=XXXX).`
   - **Experimental Format**: `With subjects from {background} in {study}, manipulated variable {X} is {positively/negatively} related to dependent variable {Y} (p<ZZ, n=XXXX).`
   - **Survey Format**: `Survey Questions {Q1-Q3} (grouped as {dimension}) show that {percentage/pattern} of respondents {result}.` (Or regression format if statistical model estimated.)
   - **Analytical Format**: `**Theorem/Proposition N**: {exact formal statement with mathematical conditions}.`
   - **Review Format**: Minimal summary focusing on concept wiki consolidation (no Ground Truth section).

### 2.2 Concept -> Construct -> Variable Separation
- **Concepts (`wiki/concepts/`)**: Abstract theoretical ideas (not directly observable), extracted from the Introduction, Hypothesis Development, or Literature Review. If not explicitly defined, provide a concise contextual definition marked `[common-sense definition, not explicitly defined in paper]`.
- **Constructs (`wiki/constructs/` or intermediate column)**: Operational dimensions or analytical model parameters ($\lambda$, $\sigma^2$, Informed Traders).
- **Variables (`wiki/variables/`)**: Directly measurable empirical proxies, experimental manipulations/DVs (`_exp`), or grouped survey dimensions (`_survey`).
  - **Paper Variable** = exact variable token from the paper (always use this in Ground Truth Findings).
  - **Wiki Name** = descriptive common-sense name describing what is directly measured (e.g., `InDegree` -> `Peer_Selection_Count`).
  - Mark PCA components, composite indices, standardized z-scores, fitted values, and routine controls as `[derived]` / `[no wiki]`.

---

## 3. Archival Paper Guidance

This reference provides detailed extraction guidance specific to archival/empirical papers. Use this when processing papers with existing data sources and observational methods.

## Hypothesis Extraction

### Where to Find Hypotheses
- **Hypothesis Development section**: Explicit H1, H2 statements
- **Introduction**: Research questions that imply hypotheses
- **Theory section**: Propositions derived from theory

### If No Explicit Hypothesis
Write: "No explicit hypothesis stated in this paper. The paper is a {descriptive paper type: empirical exploration | descriptive analysis | methodological contribution}."

### Argument Structure Analysis
1. **Identify premises** (supporting evidence/claims for the hypothesis)
2. **Classify each premise source**:
   - Literature-based (prior findings)
   - Theory-based (logical derivation)
   - Assumption-based (taken as given)
   - Data-based (empirical observation)
3. **Determine reasoning approach**:
   - **Deductive**: Conclusion necessarily follows (mathematical/logical certainty)
   - **Inductive**: Conclusion probabilistically follows (empirical generalization)
4. **Evaluate**:
   - Deductive papers: **Sound** if valid AND all premises empirically true; **Unsound** otherwise
   - Inductive papers: **Cogent** if strong AND all premises empirically true; **Uncogent** otherwise

## Methods Filtering for Archival Papers

### SKIP - Do NOT create wiki/methods/ page for:

**Standard econometric methods**:
- OLS, Fixed Effects, Random Effects
- Standard tests: t-tests, F-tests, Hausman tests, White tests

**Standard causal identification methods**:
- 2SLS (Two-stage least squares)
- GMM (Generalized method of moments)
- DiD (Difference-in-differences) exploiting new regulation/law as exogenous shock
- Regression Discontinuity - unless novel threshold/cutoff design

**Standard data methods**:
- Panel data construction, variable winsorization

### CREATE wiki/methods/ page for:

- **Novel identification designs**: Unique research design settings for causality (e.g., novel instrument, DiD with non-regulation shock, novel RD threshold)
- **Novel methodological contributions**: New measurement approaches, new estimators, new tests
- **Combined approaches**: Novel combinations of standard methods with unique twist

### Methods Section in Summary

**If using standard methods only**:
```markdown
## Methods
- **Standard Methods**: OLS with Industry×Year fixed effects (no wiki page created)
- **Data**: {data sources}, n={sample size}
```

**If novel design**:
```markdown
## Methods
- **Novel Design**: {description of what makes it novel}
- **Model**: {key equations or framework}
→ Create wiki/methods/{method_name}
```

## Summary Requirements for Archival Papers

### Claimed Findings: 3-5 Key Interpretations FIRST

Select the authors' **main theoretical claims**:
- What they conclude from the empirical results
- The story they tell about why results matter

**Write Claims BEFORE Ground Truth** - this establishes the interpretive framework first.

### Ground Truth Findings: 3-5 Key Findings SECOND

Select the **most important** empirical results:
- Main coefficients from primary regression tables
- Key novel variables/measures from the paper
- Statistically significant results (p<0.05 or better)

**Correspondence Requirement**: The first N Ground Truth findings should directly support the N Claimed findings above. Finding 1 supports Claim 1, Finding 2 supports Claim 2, etc.

DO NOT extract every finding. Quality over quantity.

### Ground Truth Format for Regression Results

Each finding must be **reproducible** - use the paper's actual variable names:

```
{Paper Variable Name} (defined as [exact formula from paper]) has coefficient β=YYY (p<ZZ) in [model type] (n=XXXX).
```

**Key rules**:
- Use **paper's exact variable names** (e.g., "PCOMP1", "InDegree") - be honest to the paper
- Include computational definition from paper (Results section, Variable Definitions)
- If a variable is defined once, subsequent findings can reference "see Finding N" or "see Variables table"
- The Variables table maps paper names to common-sense wiki names

## Measures/Variables for Archival Papers

### Wiki Page Criteria

**CREATE wiki/variables/ page for** (directly measurable/basic):
- **BE FOCUS**: Focus on variables central to the paper.
- **Raw counts**: Number of items (e.g., peer selections, employees, transactions)
- **Indicators**: Binary variables (0/1 flags for observable events)
- **Ratios from raw data**: Computable from observable inputs (e.g., proportions, percentages)
- **Network statistics**: Directly computed from network structure (e.g., degree, clustering coefficient)
- **Observable measurements**: Variables that can be directly counted/measured

**SKIP - NO wiki page for** (derived/composite):
- **PCA components**: Principal components (e.g., PCOMP1, PCOMP2) - these are constructed indices
- **Constructed indices**: Variables combining multiple measures through mathematical transformation
- **Standardized variables**: Z-scores, normalized versions of other variables
- **Fitted/predicted values**: Outputs from regression models (e.g., "Fitted Pay")
- **Generic names**: Variables with non-descriptive names that could apply to any paper
- **Control Variables**: **DO NOT** create wiki page for control variables not essential to the paper.

### Measures/Variables Table

Map paper variable names to wiki names with computational definitions:

| Paper Variable | Wiki Name | Constructs | Concept | Computational Definition | Wiki Page |
|----------------|-----------|------------|---------|--------------------------|-----------|
| InDegree | Peer_Selection_Count | Network position | Outside Opportunities | Number of firms selecting focal firm as peer | [[variables/Peer_Selection_Count]] |
| PCOMP1 | [derived] | Talent Transferability | Competition | First principal component of 5 measures | [no wiki] |

**Columns explained**:
- **Paper Variable**: Exact name used in the paper (honest to source) - use this in Ground Truth findings
- **Wiki Name**: Common-sense descriptive name (if wiki page created) or "[derived]" if no wiki
- **Wiki Page**: Link if directly measurable, "[no wiki]" if composite/constructed

**Rules**:
- Computational Definition must be **exact formula or operational rule**
- Ground Truth findings use **Paper Variable** names; wiki pages use **Wiki Name**

Ground Truth findings reference paper names: "InDegree (see Variables table) has β=..." → wiki maps to Peer_Selection_Count

---

## 4. Experimental & Analytical Paper Guidance

### 4.1 Experimental Papers
- **Ground Theories Table**: Link to pre-existing theories (`[[theories/{theory}]]`) tested by the experiment.
- **The Context Table**: Extract external validity factors (Task Complexity, Location, Time Constraints, Incentives, Subject Pool).
- **Experimental Design**: Document Design Type (post-test only, pre/post-test, factorial between/within), Control Group cleanliness, Randomization, Counterbalancing, and step-by-step Procedure.
- **Variables (`{variable}_exp.md`)**: Document exact measurement method for Dependent Variables and exact manipulation method/levels/checks for Manipulated Independent Variables so the study can be replicated.

### 4.2 Analytical Model Papers
- **SKIP `wiki/variables/`**: Model parameters ($\lambda$, $\sigma_\epsilon^2$, $a$, $c$) are theoretical constructs, not empirical variables.
- **CREATE `wiki/constructs/{construct}.md`** for novel model parameters and definitional constructs.
- **CREATE or UPDATE `wiki/methods/{baseline_model}.md`** using `templates/wiki/method_analytical.md` and record comparative statics or assumption extensions in the `Model Variations` table.

---

## 5. Survey Paper Guidance

This reference provides detailed extraction guidance for survey research papers. Use this when processing papers that collect data through questionnaires (mail, telephone, e-mail, internet) or face-to-face interviews.

## Survey Paper Recognition

Paper is a survey if:
- Primary data collection via questionnaires or interviews
- No manipulation of variables (no treatment/control groups)
- Subjects/respondents report opinions, judgments, or knowledge
- Variables are responses to survey questions

## Survey vs Experimental

| Survey | Experimental |
|--------|--------------|
| No manipulation | Manipulated variables |
| Natural responses | Treatment/control groups |
| Opinions/judgments/knowledge | Observable behavior/outcomes |
| Random sampling (if possible) | Random assignment |
| External validity focus | Internal validity focus |

## Summary Requirements for Survey Papers

### Claim Findings: 3-5 Key Interpretations FIRST

Select the authors' **main interpretations** of survey results:
- What they conclude from the survey findings
- The story they tell about why results matter

**Write Claims BEFORE Ground Truth** - this establishes the interpretive framework first.

### Ground Truth Findings: 3-5 Key Findings SECOND

Select the **most objective** survey results:
- Primary question-based results (response patterns, percentages)
- Statistical analysis results (if regression/correlation conducted)
- Key dimensions with significant findings

**Correspondence Requirement**: The first N Ground Truth findings should directly support the N Claim findings above. Finding 1 supports Claim 1, Finding 2 supports Claim 2, etc.

DO NOT extract every finding. Quality over quantity.

## Ground Truth Format for Survey Papers

### Question-Based Results

For surveys with direct question results (most common):

```
The survey Question {Q1-Q3} (grouped as {dimension name}) shows that {percentage/response pattern} of respondents {result description}.
```

**Grouping rule**: If question text is too long (over 3 questions), group them with a short summary and indicate question numbers.

**Example**:
```
Finding 1: The survey Questions Q1-Q4 (grouped as "Budgetary Participation") shows that 65% of respondents report moderate participation in budget setting.
```

### Statistical Analysis Results

If survey conducts statistical analysis (regression, correlation):

Use archival ground truth format:
```
{Variable X} (defined as {formula}) has coefficient β=YYY (p<ZZ) in {model type} (n=XXXX).
```

## Concepts Extraction for Survey Papers

Survey concepts are **easier to extract** than archival papers:

**Where to find concepts**:
- **Research question**: Often directly stated
- **Title**: Paper title frequently indicates core concept
- **Introduction**: Concepts introduced with their importance

**Concept structure for surveys**:
- Each concept measured by **survey dimensions** (multiple questions)
- Dimension = grouping of related questions
- Record dimensions in Concepts table

## Variables Extraction for Survey Papers

### Survey Variables = Survey Questions

Survey variables differ from archival/experimental:
- **Archival/Experimental**: Variables = computational measures
- **Survey**: Variables = responses to questions (scalar/yes-no)

### Grouping Questions by Dimensions

One concept is typically measured by **several dimensions**, each dimension contains **multiple questions**.

**Grouping structure**:
```
Concept → Dimensions → Questions (grouped)
```

**Example**:
- Concept: "Budgetary Participation"
- Dimensions: Budget Setting, Budget Review
- Questions: Q1-Q3 (Budget Setting), Q4-Q5 (Budget Review)

**Key insight**: Questions are **GROUPED** by dimension. One variable wiki page = all questions measuring one dimension.

### Wiki Naming for Survey Variables

Survey wiki naming differs from archival/experimental:

| Category | Naming Rule | Marker |
|----------|-------------|--------|
| **Concepts** | Standard: `[[concepts/{concept}]]` | NO `_survey` |
| **Variables** | `{dimension}_survey` (grouped questions) | YES `_survey` |
| **Methods (instruments)** | `{instrument}_survey_instrument` | YES `_survey_instrument` |

**Variable naming**: One wiki page per dimension (NOT per individual question).

**Example**:
| Dimension | Concept | Questions Grouped | Wiki Page |
|-----------|---------|-------------------|-----------|
| Budget_Setting | Budgetary_Participation | Q1-Q3 | [[variables/Budget_Setting_survey]] |
| Budget_Review | Budgetary_Participation | Q4-Q5 | [[variables/Budget_Review_survey]] |

**Why grouped**: Multiple questions measuring same dimension share one wiki page. The wiki page summarizes what that dimension measures and lists the specific questions.

## Survey Design Extraction

### Survey Type
Identify delivery method:
- Mail survey
- Telephone survey
- E-mail survey
- Internet platform survey
- Face-to-face interview
- Custom type

### Respondent Target
Similar to experimental "subjects":
- Target population (managers, accountants, students, etc.)
- Sample size
- Sampling method (random, convenience, stratified)

### Response Categories
What does the survey ask for:
- **Opinions**: Subjective views (e.g., "I believe...")
- **Judgments**: Evaluations (e.g., "This is effective...")
- **Knowledge**: Factual recall (e.g., "What is...?")
- Custom categories

### Question Sequence
Order of questions:
- Easiest (shortest) to hardest
- Hardest to easiest
- Random order
- Logical flow (topic grouping)

### Survey Instrument

**Well-established instruments** (from previous research):
- Self-reported performance scales
- Budgetary participation instruments
- Tolerance of ambiguity scales
- etc.

**New instruments**:
- If paper develops new instrument
- Summarize validity testing (construct validity, content validity)
- **CREATE wiki/methods/{instrument}_survey_instrument.md**
- Wiki page marked as `_survey_instrument`

### Non-Response Handling
Extract how paper:
- Encourages response (incentives, reminders, etc.)
- Addresses non-response bias
- Calculates response rate

### Reliability Measures
Extract reliability testing:
- **Test-Retest reliability**: Same survey administered twice
- **Split-half reliability**: Correlation between halves of survey
- **Cronbach's Alpha**: Internal consistency
- Custom reliability measures

**Record coefficients**: Report actual reliability values (e.g., α = 0.85)

## Face-to-Face Interview Specifics

### Interview Type
Three types of interviews:
- **Structured Interview**: Fixed questions, fixed order
- **Semi-Structured Interview**: Core questions + flexible probing
- **Unstructured Interview**: Open-ended conversation

### Interviewee Selection
Extract:
- How interviewees chosen (random, purposive, convenience)
- Why chosen (expertise, position, experience)
- Selection acknowledgment in paper

## Hypothesis Extraction for Survey Papers

Survey papers CAN develop hypotheses when:
- Theory-driven causal predictions
- Testing relationships between concepts
- Brown (1995) emphasizes need for good theory to underpin causal relationships

### If Hypothesis Exists

Use archival guidance argument structure analysis:
1. Identify premises (supporting evidence for hypothesis)
2. Classify premise sources (literature, theory, assumption)
3. Determine reasoning approach (deductive/inductive)
4. Evaluate (sound/unsound/cogent/uncogent)

→ Refer to `archival_extract_guidance.md` for detailed argument structure analysis.

### If No Hypothesis
Write: "No explicit hypothesis stated in this paper. The survey is {descriptive study | exploratory study | knowledge assessment}."

## Survey Limitations

Common survey limitations to extract:
- **Internal validity**: Inability to assign subjects randomly, inability to rule out rival hypotheses
- **External validity**: Response bias, non-response bias, sample representativeness
- **Construct validity**: Question wording effects, social desirability bias
- **Reliability**: Measurement reliability concerns

## Wiki Pages for Survey Papers

### Concepts Wiki Pages
- Standard concept template
- Standard naming: `[[concepts/{concept}]]` (NO `_survey` marker)
- Include survey dimensions in "Constructs & Variables" section

### Variables Wiki Pages
- One wiki page per **dimension** (group of questions)
- Naming: `[[variables/{dimension}_survey]]`
- NOT per individual question (questions grouped by dimension)
- Wiki page summarizes what dimension measures, lists specific questions

### Methods Wiki Pages
- Only for **new survey instruments**
- Naming: `[[methods/{instrument}_survey_instrument]]`
- Skip standard instruments (existing validated scales)

---

## 6. Literature Review Paper Guidance

This reference provides extraction guidance for review papers. Review papers consolidate existing knowledge about a concept; they focus on updating wiki pages rather than creating a full summary.

## Review Paper Recognition

Paper is a review if:
- Surveys existing literature on a specific concept
- Synthesizes findings across multiple papers
- No new empirical data collection
- No hypothesis testing with new data
- Title often includes "Review", "Survey" (as literature survey), "Overview"

## Review Paper Workflow

Review papers have a **different workflow** from archival/experimental/survey papers:

```
Review → Check concept wiki → Create/Update concept wiki → NO full summary creation
```

### Step 1: Check Concept Page Existence

1. Identify the **core concept** the review paper is about
2. Check if wiki page exists for the concept using `rg --files wiki/concepts/`.

### Step 2: Create Concept Page (If Not Exists)

If no wiki page for the concept:

1. Read `<skill_dir>/templates/wiki/concept.md` template
2. Fill in with information from the review paper
3. Use **concise sentences** to conclude main points
4. Source papers: Record **oldest 2 and nearest 3** papers only

**We don't want wiki pages growing as long as review papers.** Instruct readers to read the review if they need more information.

### Step 3: Update Concept Page (If Exists)

If wiki page already exists for the concept:

1. Compare existing content with review paper information
2. Update with new information from review
3. Maintain concise style
4. Add review paper to source papers (oldest 2 + nearest 3)

## What NOT to Create

**ONLY create concept page for the main concept.**

Do NOT create:
- Multiple concept pages (only main concept)
- New variable pages (review papers don't introduce new measures)
- New method pages (review papers don't introduce new methods)
- Full paper summary (review is consolidation, not extraction)

## Cross-Linking from Review Paper

For variables/methods/related concepts/theories mentioned in review:

1. Check existing wiki pages for these items
2. If exists: Establish correct links in concept page
3. If not exists: **Do NOT create**; wait for empirical papers to define them

## Concept Page Content from Review

### Definition
- Synthesize definition from review
- Note if multiple definitions exist (alternative definitions section)

### Constructs & Variables
- List measures discussed in review
- Link to existing variable pages
- Do NOT create new variable pages

### Related Theories
- List theories discussed in review
- Link to existing theory pages

### Economic Consequences
- Synthesize consequences discussed in review
- Cite oldest 2 + nearest 3 papers

### Future Works
- Extract future research directions from review
- These guide future paper ingestion

## Source Papers Management

Wiki pages should remain concise. Source papers:

**Pattern**: Oldest 2 papers + Nearest 3 papers

**Example**:
| Source Papers | Year | Contribution |
|---------------|------|--------------|
| [[source/summary/first_paper]] | 1990 | First definition |
| [[source/summary/second_paper]] | 1995 | Alternative definition |
| [[source/summary/review_paper]] | 2024 | Comprehensive review |
| [[source/summary/near_paper_1]] | 2023 | Recent finding |
| [[source/summary/near_paper_2]] | 2022 | Recent extension |

**Why this pattern**: 
- Oldest papers establish concept origin
- Nearest papers show current state
- Review paper synthesizes all

## Review Paper Summary (Minimal)

Review papers do NOT use the full summary template.

Create a minimal reference file instead:

```markdown
---
title: "{Review Title}"
citekey: {citekey}
paper_type: review
target_concept: {concept name}
---

# {Review Title}

## Core Concept
{concept reviewed}

## Wiki Update Action
- [Concept page created] or [Concept page updated]

## Key Contributions
{2-3 sentences on what the review adds to existing knowledge}

## Related Papers (for wiki cross-linking)
{Papers mentioned in review that should be linked}
```

Store minimal summary in `source/summary/{citekey}_review.md`.

## When to Create Full Summary

**Exception**: If review paper introduces novel theoretical framework:

1. Create full summary using `paper_summary_analytical.md` template
2. Treat as analytical model paper (theoretical contribution)
3. This is rare; most reviews consolidate existing knowledge

## Integration with kb-ingest

When ingesting a review paper:

1. **Phase 3**: Skip standard extraction
2. Use this review extraction guidance
3. **Phase 4**: Focus on wiki consolidation quality check
4. No collision resolution needed (only updating one concept page)

## Related Skills

- **kb-consolidate**: Wiki page consolidation and merging. May be relevant if review reveals multiple similar concept pages.

---

## 7. Self-Verification Checklist (Ground Truth Reproducibility Gate)

Before creating wiki pages, verify every Ground Truth Finding against these 3 rules:

1. **Objective Observation**:
   - Archival/Experimental/Survey: Includes exact variable names, direction/coefficient ($\beta$ or percentage), $p$-value, model/design type, and sample size ($n$).
   - Analytical: Includes exact Theorem/Proposition number and mathematical conditions.
2. **Complete Operational Definition**:
   - Every variable or symbol in Ground Truth Findings is defined inline, in an earlier Finding (`see Finding 1`), or in the `Measures/Variables` / `Model Parameters` table (`see Variables table`).
   - Never leave abstract concept names in Ground Truth Findings without their operational proxy.
3. **Self-Contained Reproducibility**:
   - A reader can understand exactly what was regressed, manipulated, asked, or proved from the summary file alone without re-reading the raw PDF.
