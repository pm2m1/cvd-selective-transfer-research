# HRS → ELSA eight-role baseline feature contract

Prepared 6 November 2026. **HRS mapping readiness: PARTIAL. ELSA mapping readiness: PARTIAL. Real clinical training remains blocked.** This is an AI-authored public engineering contract, not a claim that usable modeling rows, endpoint compatibility or independent scientific acceptance have been established.

## Scope and exact role order

The existing eight-role, five-view design is retained. It is not the older HAALSI/MHAS ten-feature contract, and its encoded dimensions/parameter count must not be described as the historical 8,033-parameter network without measuring the actual new model.

| Position | Role | View | HRS 2012 baseline source | ELSA W6 baseline source; W4 comparator |
|---|---|---|---|---|
|0|age|background|RAND2022V1 `r11agey_e`|Original Core `indager` at W6; W4 `indager` |
|1|sex|background|RAND2022V1 `ragender`, subject to baseline-availability proof|Original Core `indsex`, W6/W4 |
|2|sbp|haemodynamic|Gateway HRS D `r11systo`|Nurse6 `SYSVAL` / Nurse4 `sysval` |
|3|dbp|haemodynamic|Gateway HRS D `r11diasto`|Nurse6 `DIAVAL` / Nurse4 `diaval` |
|4|bmi|metabolic|Gateway HRS D `r11mbmi`|Nurse6 `BMIVAL` / Nurse4 `bmival` |
|5|smoking|behaviour|RAND `r11smokev` + `r11smoken`|H `r6smokev` + `r6smoken`; W4 `r4...` |
|6|diabetes|comorbidity_medication|RAND `r11diabe`, with verified baseline information boundary|Original personal Core history through W6/W4, not a future-revised harmonized diagnosis |
|7|bp_treatment|comorbidity_medication|Gateway D `r11rxhibp`|H `r6rxhibp`; W4 `r4rxhibp` |

Raw view widths are `(2,2,1,1,2)`. Canonical role aliases must be explicit: prior `smoking_status`→`smoking` and `antihypertensive_treatment`→`bp_treatment`. No other name may be matched fuzzily. One-hot encoding or missing indicators can increase model widths; that is preprocessing under this new implementation, not unchanged historical architecture.

`FEATURE_HARMONIZATION_MATRIX.csv` is the variable-level matrix including definition, units, missing codes, waves, timing, evidence, readiness and dependencies. Its conditional statuses distinguish established source identities from still-unverified usable baseline values. Public mapping evidence does not certify the private rows or actual frozen-source metadata.

## Canonical value and evidence requirements

- **Age:** years, valid observed nonnegative numeric age. Original ELSA `indager=-7` explicitly means disclosure-collapsed age90+, not an observed exact age. It must remain a censored/topcoded state until a prespecified common age representation is adopted. Do not silently set it to90 or replace it with later age. The frozen count engine's treatment is unchanged by this feature contract; any eligibility change requires a separately justified amendment.
- **Sex:** source survey coding male1/female2 maps to canonical0/1 only after source validity and baseline availability are established. This is a recorded binary survey variable, not a comprehensive gender measure. HRS cross-wave `ragender` must not be silently taken from a future first-nonmissing report. No unverified original-Core replacement field is invented here.
- **SBP/DBP:** mmHg; positive finite provider-valid means with documented measurement protocol. ELSA nurse `-1` means invalid/incomplete readings. Physical measures are not replaced by self-reported hypertension or by later waves.
- **BMI:** kg/m²; positive finite provider-valid BMI. ELSA `bmival` includes BMI calculated using estimated weights above130kg. Measurement provenance must retain that limitation; this is not an exclusively directly measured-weight phenotype.
- **Smoking:** canonical never0/former1/current2 is derived only from coherent ever/current pairs `(0,0)`, `(1,0)`, `(1,1)`. `(0,1)` is contradictory/unknown; missing is not never. Encoders must use prespecified categorical handling, not a data-driven recoding that changes meaning.
- **Diabetes:** reported history, not glucose/HbA1c. ELSA's original history reconstruction gives1 for prior confirmed personal reports,0 for verified absence, otherwise missing. Unknown, disputed and proxy-only evidence does not become no diabetes. Follow-up waves cannot supply baseline diabetes status. Diabetes is not automatically an MI/stroke baseline exclusion.
- **BP treatment:** documented medication treatment/prevention report. It is not interchangeable with hypertension diagnosis or high measured BP. Missing/skipped evidence is not untreated, and a medication screened zero never establishes a disease-negative outcome.

Field-specific Stata tagged/plain missing, negative missing/error codes, structural missingness, refusal and invalid values must be classified before numeric import. NaN is a canonical unavailable **predictor cell**, not a raw survey-code interpretation and never an unknown outcome label. Invalid/unreviewed categorical codes fail the adapter rather than being clipped into a valid category. Source and target must share canonical role order and units; they need not share raw code values.

## Baseline time and measurement eligibility

HRS baseline is the2012 Core interview. Existing public timing fields are Gateway `inw11pm` (physical-measures participation/eligibility) and `r11bpcomp` (completed at least one BP test), alongside independently valid measured SBP/DBP/BMI. They do not by themselves establish complete anthropometry, arbitrary exact dates or every required information-availability condition. Source-specific same-Core ordering/landmark assumptions must be retained explicitly in the reviewed real input provenance.

ELSA baseline is the original Core W6 interview (W4 for the comparator). Core age/sex and supported reported-history predictors must be known by that baseline. For nurse measures use original `visyear`/`vismon` month bounds. Under the frozen final-count rule, the **latest possible measurement/availability date must precede the earliest possible baseline date**. A same-month or later nurse examination is not backdated. A nurse-based landmark would be a different, prospectively amended cohort and endpoint, not a looser date tolerance chosen to gain events.

The ten registered ELSA history products are Harmonized H plus Core1–9. They do **not** include the two nurse products required by the automatic measured-feature adapter: `wave_4_nurse_data.dta` and `wave_6_elsa_nurse_data_v2.dta`. No claim is made that those products are unavailable to the researcher; their independently registered/usable status is not established by the ten history descriptors. Without nurse inputs or independently reviewed equivalent baseline feature evidence, SBP/DBP/BMI completeness is not established.

The W4 comparator has an earlier target calendar window than HRS2012 source. Using a model trained on later HRS observations for that comparator is retrospective cross-cohort transportability, not proof that the model could have been deployed in2008 or independent temporal validation. No future participant-level feature information is permitted in either design.

## Missing predictors versus missing disease evidence

First establish disease-free eligibility, endpoint observability, source interpretation and measurement eligibility. Predictor imputation cannot repair missing interviews, ambiguous timing, an unobserved examination, unsupported negative disease histories or missing outcomes.

Complete-case analysis and a source-training-only missing-cell strategy are distinct prospective analyses. If training uses median/mode fills and missing indicators, fit all fills/scaling only on the training portion of that fold; freeze transformations for source validation, target adaptation, calibration and held-out evaluation. Reject wholly unobserved training features and unsupported category domains. Structural measurement absence and timing ineligibility must remain distinguishable from ordinary missing cells. Do not call this multiple imputation or claim missing-at-random is established. A missingness strategy cannot create observed positive events.

## Endpoint boundary is separate and remains binding

HRS interval MI zero labels in the selected Gateway route may be screening-assumed. Strict directly observed HRS MI negatives remain unsupported without the requisite original Core evidence. Any working composite using those zeros is explicitly **screening-assumed-negative sensitivity**, not a strict common clinical primary endpoint. Definite HRS interval stroke requires the adopted paired response/`rWstrokq` route with Q=2. No TIA is silently promoted to stroke.

ELSA labels require verified baseline histories, qualifying personal follow-up and branch/confirmation/dispute/timing evidence. The completed status-only diagnostic does not itself resolve the interview conflict or authorize a new count rule. Unknown/disputed/censored outcomes are not binary zero. A compatible feature matrix cannot establish cohort or endpoint validity.

## Optional variables intentionally excluded

Education, socioeconomic measures, diagnosed hypertension, alcohol, activity, general health, functional limitations, family history and lipids are not silently added to the executable eight-role real-data contract. Some have public candidate stubs, but cross-country categories, timing, quantity definitions or exact fields remain insufficiently reviewed for this experiment. Adding them is a separately versioned feature-tier decision with new evidence and fair-comparator handling. Labs are not fabricated to preserve an EEG-derived architecture or the old ten-feature contract.

## Real-training prerequisites from the feature workstream

1. Resolve the ELSA interview/participation interpretation with the protected diagnostic's permitted independent review; no data-conditioned conclusion is drawn here.
2. Establish usable baseline physical measures and actual timing in both cohorts, including the nurse-product or equivalent feature-evidence chain.
3. Preserve exact labels/source-specific sensitivity designation and documented negative/history evidence.
4. Produce independently authorized validated modeling inputs with baseline-only feature provenance, unknown-outcome handling, immutable nonoverlapping partitions and untouched-test evidence.
5. Establish event, feature, precision and independent-evaluation sufficiency before real fitting. None is proved by public field names or synthetic training.
