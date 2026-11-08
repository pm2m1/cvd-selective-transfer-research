# Phase 1 supervisor guide

[Repository home](../README.md) · [Report-to-code map](PHASE1_REPORT_TO_CODE_MAP.md) · [Figure inventory](PHASE1_FIGURE_INVENTORY.md) · [Academic-report publication status](../reports/nitw-btech-phase1/README.md)

This guide covers **Early Prediction of Cardiovascular Diseases using Deep Learning**, the completed HAALSI → MHAS experiment. Read the [frozen manuscript](FINAL_SUBMISSION_MANUSCRIPT.md) for the full scientific account and the [supplement](SUPPLEMENTARY_AGGREGATE_RESULTS.md) for all approved results. The B.Tech PDF/LaTeX is not publicly distributed pending separate report/authorship review. Public visibility of this branch does not establish manuscript, institutional or data-provider approval.

## What question did we test?

Prediction can change across populations because of differences in participant characteristics, diagnosis access, measurements and follow-up. The question was whether a source-pretrained network could adapt with limited target labels while selectively controlling which representations update. Possible domain shift motivates the experiment; the results do not identify a unique cause of any performance change.

The design is inspired by [Cui et al.'s EEG DMV-MAT](https://doi.org/10.1109/TNNLS.2024.3350085). We re-engineered it for tabular clinical views and a calibrated logical module selector. It is neither an exact EEG reproduction nor a demonstrated novel algorithm. The contribution is an auditable implementation and empirical comparison with useful negative findings.

## Cohorts, endpoint and clinical views

The source is **HAALSI, South Africa**; the target is **MHAS, Mexico**. These are selected analytic cohorts with observed follow-up, not all participants in either survey.

| Fixed role | Participants | Positive reports |
|---|---:|---:|
| HAALSI source training | 1,744 | 65 |
| HAALSI source validation | 581 | 21 |
| HAALSI source held-out | 581 | 21 |
| MHAS target adaptation pool | 679 | 49 |
| MHAS target validation | 171 | 13 |
| MHAS locked target test | 283 | 21 |

The totals are 2,906 source participants/107 positive reports and 1,133 target participants/83 reports. These counts are documented in the [frozen manuscript](FINAL_SUBMISSION_MANUSCRIPT.md) and [dataset description](phase1/dataset-and-endpoint.md). The endpoint is **wave-observed, doctor-reported heart attack or stroke, conditional on observed follow-up**, after baseline-negative eligibility. It is not clinically adjudicated incidence, an exact onset date or independently validated clinical risk. Missing follow-up/death without prior positive evidence is not automatically a negative.

| View | Baseline clinical roles |
|---|---|
| Background | Age, sex |
| Haemodynamic | Systolic and diastolic blood pressure |
| Metabolic | BMI, total cholesterol, HDL cholesterol |
| Behaviour | Smoking status |
| Comorbidity/medication | Diabetes, antihypertensive treatment |

The encoded widths are **4, 2, 3, 4, 6**. These 19 encoded inputs are not 19 raw clinical variables. The public generic synthetic schema contains a historical fasting-glucose slot and is not the separately versioned real-study diabetes construction. The [feature documentation](phase1/dataset-and-endpoint.md) preserves that distinction rather than claiming exact clinical reconstruction. Source-fitted preprocessing is reused by transfer models; target-only baselines fit preprocessing on their target adaptation draw.

## Architecture and SHARE/ADAPT

[MultiViewRiskNet](../src/dmv_mat_cvd/models/multiview_mlp.py) has five Linear–ReLU–LayerNorm encoders, each producing 16 features. Concatenation gives width 80; two fusion modules have widths 64 and 32, followed by one binary-logit head. The real-study architecture has **8,033 parameters**, including **33 head parameters**. Synthetic input widths can give different totals.

Source pretraining uses binary cross-entropy, source validation for checkpoint selection and AdamW. After pretraining, detached source-validation and target-adaptation representations produce MMD and source-relative class-geometry evidence. **MMD is a selector statistic, not an added training loss.** The public implementation preserves `legacy_topk`, `calibrated_threshold` and the primary `calibrated_logical` policy; they are not interchangeable.

For the logical rule, valid geometry must support either upper retention below 0.75, or domain p ≤ 0.05 together with retention below 0.8 and upper retention below 1. Invalid geometry causes **ABSTAIN → SHARE**; valid geometry failing the predicate also yields SHARE. SHARE freezes weights, ADAPT enables updates, and the head remains trainable. A shared block's output can still change if an upstream adapted block changes. Frozen views are not shown to be clinically unimportant. See [mathematics and pseudocode](phase1/model-architecture.md), [calibration](../src/dmv_mat_cvd/transfer/calibration.py) and [freezing](../src/dmv_mat_cvd/transfer/adapt.py).

## Evaluation design: hold-out, not cross-validation

The study used **fixed hold-out evaluation with ten repeated stratified target-adaptation draws**. It was **not 3-fold, 5-fold or 10-fold cross-validation**. Every primary adapted model was evaluated on the same locked **283-person MHAS test cohort, with 21 positive reports**. Overlapping draws do not create independent test populations.

The primary fitting budget was **25 positive + 75 negative labels** per draw; the nested secondary budget was **10 positive + 30 negative**. Outcome enrichment means these are not outcome-blind random-labeling budgets. Another 171 labeled target-validation participants, including 13 positives, influenced early stopping/development reporting. Thus “100 adaptation labels” does not mean only 100 target labels influenced development.

Historical neural settings were AdamW, learning rate 0.001, weight decay 0.0001, batch 64, maximum 30 source/20 target epochs and patience 5. The released training function uses validation BCE and evaluates its first eligible checkpoint after an optimizer epoch; epoch zero is not a stopping candidate. Generic CLI defaults are not the complete historical overrides. [Protocol](phase1/experimental-protocol.md) documents this and the failed original test attempt followed by separately authorized recovery, without presenting recovery as a fresh untouched test.

## All 13 registered comparisons

| Historical method ID | Scientific purpose |
|---|---|
| `source_logistic` | Source-only logistic regression |
| `source_xgboost` | Source-only boosted trees |
| `source_flat_mlp` | Source-only flat neural network |
| `source_multiview` | Source-only five-view network |
| `head_only` | Adapt the classifier head only |
| `full_finetune` | Update the entire pretrained network |
| `target_logistic` | Target-only logistic regression |
| `target_multiview` | Target-only five-view network |
| `fixed_mask` | Prespecified fusion adaptation |
| `random_calibrated_logical` | Parameter-matched random-mask control |
| `legacy_topk` | Ranked fixed-cardinality module selection |
| `calibrated_threshold` | Calibrated threshold selector |
| `calibrated_logical` | Prespecified primary logical selector |

[All 13 numerical results](phase1/baselines-and-results.md) remain available for both budgets. These historical IDs do not all equal generic CLI mode names: for example, the public runner uses `source_only` for its pretrained multiview control and `full` for full adaptation. Public baseline/model primitives do not replace the missing original clinical runner and saved model inventory. The [code map](PHASE1_REPORT_TO_CODE_MAP.md) specifies the limits.

## Findings and uncertainty

| Primary-budget method | AP | AUROC | Brier |
|---|---:|---:|---:|
| Source-only five-view network | 0.135493 | 0.688659 | 0.069207 |
| Head-only fine-tuning | 0.142376 | 0.702490 | 0.067665 |
| Full fine-tuning | 0.140845 | 0.685714 | 0.067472 |
| Calibrated logical | 0.142664 | 0.702854 | 0.067654 |

The prespecified mean within-draw logical-minus-full AP difference is **+0.001819**, with descriptive 95% joint participant-bootstrap interval **[−0.024809, +0.032340]**. **Superiority was not established.** The source is the unchanged [approved aggregate JSON](../results/aggregate_only_results.json), not newly trained models. Lower Brier is better; Brier alone does not establish adequate clinical calibration.

The 2,000-replicate bootstrap jointly resampled the same test participants across every method and draw. It did not treat ten adaptation draws as independent cohorts, pool 2,830 people or average model probabilities before AP calculation. The new [paired-contrast plot](../figures/08_primary_paired_ap_contrasts.svg) displays stored approved intervals; it does not rerun that bootstrap. Every displayed interval includes zero. Individual-method error-bar overlap is not the registered paired contrast.

## Parameter economy and the secondary budget

Logical adapted no internal module in **9/10 primary draws**, averaging **41/8,033 trainable parameters (0.51%)** including the head. Head-only updates 33 (0.41%); full fine-tuning updates 8,033. Parameter-matched random masks matched logical in 9/10 primary and all secondary draws. This limits the control's distinctiveness. Fewer updated weights are not proof of better prediction, reduced wall-clock cost or a clinically important learned subset.

At 10+30 labels, logical/full AP were **0.140706/0.132768**; the secondary paired difference was **+0.007938**, interval **[−0.014184,+0.032761]**. This is also inconclusive. Logical-minus-random was exactly zero because the corresponding masks/trained states coincided, not because an independent replication confirmed the selector. See the [complete supplement](SUPPLEMENTARY_AGGREGATE_RESULTS.md).

## Threshold software versus restricted threshold findings

The public [threshold module](../src/dmv_mat_cvd/thresholds.py), [invented demonstration](../examples/threshold_demo.py) and [tests](../tests/test_thresholds.py) calculate TP/TN/FP/FN, accuracy, precision, recall, specificity, F1 and balanced accuracy on unchanged scores. Undefined precision remains N/A. Changing a binary cutoff does not change AP, AUROC or Brier. A probability cutoff of 0.05 is unrelated to the module-selector statistical criterion p ≤ 0.05.

The completed empirical fixed-cutoff sweep is now [publicly available](../results/haalsi_mhas_real_threshold_analysis) on explicit researcher attestation of completed review/clearance: 510 original matrices, all six response families, comparison plots and numerical aggregates. No separate documentary clearance record or independent legal/institutional certification is claimed. Original privacy/post-hoc labels and bytes remain intact. Participant predictions/IDs and private operational records stay excluded. The sweep is retrospective description of an already examined test, not a validated clinical cutoff. `ORIGINAL_VALIDATION_OPTIMAL_THRESHOLD_NOT_ESTABLISHED` remains. [Methodology and disclosure boundary](phase1/threshold-analysis.md) explain the limits.

## Phase 2 and limitations

HRS → ELSA remains a separate feasibility/engineering investigation. Operator-reported source registration, a diagnostic and a review worksheet do not establish valid eligible-event counts. Mappings and eligibility interpretation remain unresolved/partial; **no real HRS → ELSA training or performance result is established**. Its synthetic training infrastructure is in the separate research workspace, not this repository. Read the [dated update](../phase2/STATUS_20261107.md); the earlier Phase-2A documents remain historical.

Thirteen validation and 21 test positives limit stable stopping, threshold calibration and metric precision. Shared validation selection/reporting is not independent validation. Survey-report semantics, attrition, enriched adaptation prevalence and potential cohort shift limit generalization. Clinical usefulness, deployment readiness and selective-adaptation superiority have not been demonstrated. Licensing, precise MHAS product citations/notification, final authorship/manuscript wording and institutional approval still require independent author review.

## A practical review route

1. Read this guide and the [frozen manuscript](FINAL_SUBMISSION_MANUSCRIPT.md).
2. Inspect the [approved results](SUPPLEMENTARY_AGGREGATE_RESULTS.md) and [paired contrast](../figures/08_primary_paired_ap_contrasts.svg).
3. Follow the [report-to-code map](PHASE1_REPORT_TO_CODE_MAP.md) and [figure inventory](PHASE1_FIGURE_INVENTORY.md).
4. Run the [synthetic-only reproduction commands](phase1/reproducibility.md), inspect [tests](../tests) and [CI configuration](../.github/workflows/public-checks.yml).
5. Review [report-publication status](../reports/nitw-btech-phase1/README.md), [disclosure rules](phase1/data-access-and-disclosure.md) and unresolved items before approving a broader release.

Public execution demonstrates software behavior on invented cohorts. It cannot reconstruct the historical empirical results from this checkout alone: controlled datasets, exact mappings/memberships, fitted models, original clinical runner and joint test-bootstrap executor are not distributed. This is an explicit reproducibility boundary, not a promised one-command clinical replication.

**Source archive update:** the [original research implementation packages](../research/README.md), historical baseline/selective source and joint-bootstrap statistics source are now included. Three historical source files explicitly project private bindings/paths. Earlier unavailable-executor statements describe the prior release, not the new reference-source archive. Academic report files remain excluded by author instruction.
