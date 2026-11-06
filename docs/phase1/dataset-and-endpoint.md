# Dataset construction and endpoint

[Phase 1 index](overview.md) · [Frozen manuscript, sections 3–4](../FINAL_SUBMISSION_MANUSCRIPT.md)

HAALSI Wave 1 supplied the source cohort; the MHAS 2012 examination cohort supplied the target cohort. They are selected analytic populations, not representative samples of every adult in either country. Complete predictor availability, prior-disease exclusions and observed follow-up restrict inclusion.

| Fixed role | Participants | Positive reports | Permitted use |
|---|---:|---:|---|
| HAALSI training | 1,744 | 65 | Source fitting and preprocessing fit |
| HAALSI validation | 581 | 21 | Source checkpoint selection and selector reference geometry |
| HAALSI source held-out | 581 | 21 | Not used in the registered MHAS test comparison |
| MHAS adaptation pool | 679 | 49 | Original paired adaptation draws |
| MHAS validation | 171 | 13 | Early stopping and development reporting |
| MHAS final test | 283 | 21 | Frozen registered comparison |

These counts match Table 1 of the frozen manuscript. No participant assignments or identifiers are distributed.

## Observation rule

The endpoint is **wave-observed, doctor-reported heart attack or stroke, conditional on observed follow-up**, among baseline-negative participants. A new positive at an intermediate or final planned wave contributes a positive report. A final observed negative with no earlier positive is a known negative under the frozen rule. Death or noninterview without an earlier positive is not a negative outcome. The follow-up is approximately six years and wave-based; exact onset dates and adjudicated clinical incidence are not established.

The HAALSI source landmark is the baseline collection episode. The target landmark is the MHAS examination, limited to 0–30 calendar days after a completed baseline interview. Disease arising between interview and examination cannot always be excluded. MHAS harmonized Version-D indicators carry prior positive reports forward. HAALSI reversals were handled component by component: explicit “never had,” “misdiagnosed” and unexplained reversals were uncertain; “no longer has” did not erase an earlier positive. A separately valid positive of the other component could retain the composite. See the frozen manuscript for the complete qualified interpretation.

## Baseline clinical views

| View | Predictors | Measurement considerations |
|---|---|---|
| Background | Age, baseline sex | Baseline demographic coding |
| Haemodynamic | Systolic and diastolic blood pressure | Examination measurements; timing matters |
| Metabolic | BMI, total cholesterol, HDL cholesterol | HAALSI lipids converted from mmol/L to mg/dL |
| Behaviour | Smoking status | Survey categories require harmonization |
| Comorbidity/medication | Doctor-reported diabetes, antihypertensive treatment | Report constructions and treatment access differ |

The ten raw predictors become encoded view dimensions **4, 2, 3, 4 and 6**, respectively, before the neural encoders. Each neural view embedding has width 16. Raw predictor counts and encoded dimensions are different quantities. Source-training medians and scales are applied unchanged to transfer-model target inputs; target-only methods fit preprocessing on their adaptation draw. No outcome, death flag, identifier or follow-up predictor enters a view.

The public generic/synthetic schema includes a historical fasting-glucose slot. It does not implement the separately versioned real-study diabetes construction. A diabetes-omitted nine-feature sensitivity was not trained in the frozen final registration. Neither the synthetic schema nor that unperformed sensitivity should be described as the complete clinical study.

Cross-country reporting, diagnosis access, biomarker availability, participant mix and attrition can affect transportability. Their existence as potential sources of shift does not establish which factor caused the observed model results.

## Original data and citations

Use the [HAALSI ICPSR V4 record](https://www.icpsr.umich.edu/web/NACDA/studies/36633) and [MHAS official data products](https://www.mhasweb.org/DataProducts/Home.aspx), under their respective access and citation terms. The original manuscript bibliography retains the study citations. Exact MHAS product names, release years, retrieval dates and research-product notification status remain author-review items; this release does not invent them.
