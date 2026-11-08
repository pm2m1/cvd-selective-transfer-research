# Existing training interface — unchanged and still conditional

The seven-method fast-track package is reused, not copied, rebuilt or tuned. The review tool writes evidence worksheets, **not** its readiness certificate or canonical rows. A completed human decision would be only one upstream evidence item; it cannot directly feed training as arrays or override unresolved count/feature/precision gates.

## Remaining variable and timing requirements

The full cited public map is copied unchanged to `references/OFFICIAL_VARIABLE_MAPPING.csv`; citation locators are in `references/OFFICIAL_SOURCES.json`. Documentary identities do not certify actual release/baseline availability.

| Role | HRS selected public mapping | ELSA selected public mapping | Evidence still required privately |
|---|---|---|---|
| Age | RAND2022V1 `r11agey_e` | Core4/6 `indager` | Interview-baseline timing; ELSA −7 is90+ topcoding, not numeric90 or ordinary missing |
| Sex | RAND `ragender` | Core4/6 `indsex` | Source code and baseline-available correction history; explicit1/2→0/1 mapping |
| SBP/DBP | HRS D `r11systo/r11diasto`; `inw11pm/r11bpcomp` distinct completion evidence | Nurse4 `sysval/diaval`; Nurse6 `SYSVAL/DIAVAL`, `vismon/visyear` | Exact authorized nurse products, valid measurement rules and conservative prebaseline timing; no later nurse backdating |
| BMI | HRS D `r11mbmi` | Nurse4 `bmival`, Nurse6 `BMIVAL` | Valid derived measure and timing; ELSA may include estimated weight>130kg |
| Smoking | RAND `r11smokev/r11smoken` | H `r4/r6smokev/smoken` | Coherent ever/current categories, specials unknown, baseline availability |
| Diabetes | RAND `r11diabe`, originalNC010 route | Personal Core history through baseline | No postbaseline harmonized revision used as baseline evidence; diagnosis not measured glucose |
| BP treatment | HRS D `r11rxhibp`, rawNC006 route | H `r4/r6rxhibp` | Condition-specific treatment semantics/routing; missing skip not automatic no |

Hypertension diagnosis may be a covariate, not an MI/stroke exclusion. Education, socioeconomic measures, alcohol, physical activity, other medication and labs are not enabled in the fixed eight-feature design; do not invent them to satisfy a view. Exact HRS DBP/BMI construction and actual baseline availability still require selected-release review where prior public records were the available evidence.

HRS MI screening-assumed negatives remain **sensitivity-only**. Paired RAND stroke response/Q evidence must distinguish definite interval events from lifetime, TIA and dispute routes. HRS raw 2018 −8 web nonresponse remains unknown. ELSA disease absence needs complete qualifying personal history/interval evidence; W9 missing MI-confirmation field is not fabricated. Death/exit/proxy/attrition are not automatically negatives. Nonidentical survey reports are not clinically adjudicated incidence.

## Interface compatibility and leakage gates

- Existing canonical order: age, sex, SBP, DBP, BMI, smoking, diabetes, BP treatment. Source-only preprocessing produces five encoded views, widths4/4/2/4/4. Item missingness may be prespecified NaN only after construct/timing eligibility; unknown outcomes and unavailable exams cannot be imputed into eligibility.
- Exactly24 development arrays: x/y/ids/availability for source_train/source_stop/target_fit/target_stop/target_calibration/target_validation. Separate test has four arrays. Unexpected test roles are rejected before payload reads; exact private memberships and prior-use/nonoverlap need authentic upstream verification.
- Five target roles are40/10/10/10/30; the old counter's four-role50/15/15/20 capacity scenario cannot certify them. Baseline-free cases, nonevents, unknowns, exclusions, source support and prediction precision need actual accepted counts. Event goals are not universal adequacy theorems.
- Bind the reviewed ELSA resolution, fresh counts, HRS endpoint/support, harmonization/export, statistical feasibility and independent membership evidence. All eight existing readiness gates stay false until genuine independent judgments exist. This helper never populates them.
- A separately reviewed, permitted raw-to-canonical exporter is still needed. Development training and frozen evaluation require distinct authorizations/new destinations. No previously examined MHAS test is reused. No threshold/model choice is learned from held-out outcomes.

Public source-integrity and focused synthetic interface checks are documented in TEST_REPORT.md. The prior full seven-method invented demonstration is reused as existing evidence; no additional model-training or hyperparameter cycle is necessary for this metadata-only tool. Real mapping readiness remains PARTIAL and real modeling BLOCKED.
