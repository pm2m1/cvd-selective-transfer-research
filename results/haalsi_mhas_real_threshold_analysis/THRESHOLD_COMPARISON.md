# PRIVATE POST-HOC DESCRIPTIVE ANALYSIS — frozen-score threshold sweep

DISCLOSURE NOT CLEARED. Keep all counts, tables, figures and this report inside the authorized environment.
No model fitting, inference, score transformation or test-based threshold selection occurred.
Distinct test participants: 283; positive reports: 21; negative observations: 262.
Ten adaptation draws reuse ONE shared population. They are not ten independent cohorts or 2,830 independent participants.
Predicted positive means probability >= cutoff. Undefined ratios are N/A. AP/AUROC/Brier remain unchanged for unchanged scores.
The complete fixed grid is specified for this supplement, not the original preregistered primary analysis. No best test threshold is selected or highlighted.

Validation threshold status: **ORIGINAL_VALIDATION_OPTIMAL_THRESHOLD_NOT_ESTABLISHED**.
If authentic original validation scores are unavailable, no validation-optimal threshold is established. New scores or test-selected cutoffs are not substitutes.

## Per-draw data

See threshold_metrics_per_draw.private.csv and threshold_sweep.private.json. Each confusion SVG represents ONE model/draw/operating point with integer counts. No fractional mean is plotted as one confusion matrix.

## Descriptive model/threshold means

Each row below is a mean of per-draw metrics on the same people. Mean TP/TN/FP/FN may be fractional; they are descriptive expectations across fitted draws, not one realized matrix. Source-only has one original score vector, not ten duplicated draws.
Means use defined values only. The summary CSV/JSON records n_defined/n_undefined, sample SD, minimum and maximum for every metric; undefined precision is never silently replaced by zero.

| Model | Draws | Cutoff | TP | TN | FP | FN | accuracy | precision | recall | specificity | f1 | balanced_accuracy | auroc | ap | brier |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| calibrated_logical | 10 | 0.05 | 21.000000 | 0.000000 | 262.000000 | 0.000000 | 0.074205 | 0.074205 | 1.000000 | 0.000000 | 0.138158 | 0.500000 | 0.702854 | 0.142664 | 0.067654 |
| calibrated_logical | 10 | 0.10 | 3.800000 | 238.600000 | 23.400000 | 17.200000 | 0.856537 | 0.139551 | 0.180952 | 0.910687 | 0.157288 | 0.545820 | 0.702854 | 0.142664 | 0.067654 |
| calibrated_logical | 10 | 0.15 | 0.000000 | 260.100000 | 1.900000 | 21.000000 | 0.919081 | 0.000000 | 0.000000 | 0.992748 | 0.000000 | 0.496374 | 0.702854 | 0.142664 | 0.067654 |
| calibrated_logical | 10 | 0.20 | 0.000000 | 262.000000 | 0.000000 | 21.000000 | 0.925795 | N/A | 0.000000 | 1.000000 | 0.000000 | 0.500000 | 0.702854 | 0.142664 | 0.067654 |
| calibrated_logical | 10 | 0.25 | 0.000000 | 262.000000 | 0.000000 | 21.000000 | 0.925795 | N/A | 0.000000 | 1.000000 | 0.000000 | 0.500000 | 0.702854 | 0.142664 | 0.067654 |
| calibrated_logical | 10 | 0.30 | 0.000000 | 262.000000 | 0.000000 | 21.000000 | 0.925795 | N/A | 0.000000 | 1.000000 | 0.000000 | 0.500000 | 0.702854 | 0.142664 | 0.067654 |
| calibrated_logical | 10 | 0.35 | 0.000000 | 262.000000 | 0.000000 | 21.000000 | 0.925795 | N/A | 0.000000 | 1.000000 | 0.000000 | 0.500000 | 0.702854 | 0.142664 | 0.067654 |
| calibrated_logical | 10 | 0.40 | 0.000000 | 262.000000 | 0.000000 | 21.000000 | 0.925795 | N/A | 0.000000 | 1.000000 | 0.000000 | 0.500000 | 0.702854 | 0.142664 | 0.067654 |
| calibrated_logical | 10 | 0.45 | 0.000000 | 262.000000 | 0.000000 | 21.000000 | 0.925795 | N/A | 0.000000 | 1.000000 | 0.000000 | 0.500000 | 0.702854 | 0.142664 | 0.067654 |
| calibrated_logical | 10 | 0.50 | 0.000000 | 262.000000 | 0.000000 | 21.000000 | 0.925795 | N/A | 0.000000 | 1.000000 | 0.000000 | 0.500000 | 0.702854 | 0.142664 | 0.067654 |
| head_only | 10 | 0.05 | 21.000000 | 0.000000 | 262.000000 | 0.000000 | 0.074205 | 0.074205 | 1.000000 | 0.000000 | 0.138158 | 0.500000 | 0.702490 | 0.142376 | 0.067665 |
| head_only | 10 | 0.10 | 3.800000 | 238.500000 | 23.500000 | 17.200000 | 0.856184 | 0.138981 | 0.180952 | 0.910305 | 0.156933 | 0.545629 | 0.702490 | 0.142376 | 0.067665 |
| head_only | 10 | 0.15 | 0.000000 | 260.100000 | 1.900000 | 21.000000 | 0.919081 | 0.000000 | 0.000000 | 0.992748 | 0.000000 | 0.496374 | 0.702490 | 0.142376 | 0.067665 |
| head_only | 10 | 0.20 | 0.000000 | 262.000000 | 0.000000 | 21.000000 | 0.925795 | N/A | 0.000000 | 1.000000 | 0.000000 | 0.500000 | 0.702490 | 0.142376 | 0.067665 |
| head_only | 10 | 0.25 | 0.000000 | 262.000000 | 0.000000 | 21.000000 | 0.925795 | N/A | 0.000000 | 1.000000 | 0.000000 | 0.500000 | 0.702490 | 0.142376 | 0.067665 |
| head_only | 10 | 0.30 | 0.000000 | 262.000000 | 0.000000 | 21.000000 | 0.925795 | N/A | 0.000000 | 1.000000 | 0.000000 | 0.500000 | 0.702490 | 0.142376 | 0.067665 |
| head_only | 10 | 0.35 | 0.000000 | 262.000000 | 0.000000 | 21.000000 | 0.925795 | N/A | 0.000000 | 1.000000 | 0.000000 | 0.500000 | 0.702490 | 0.142376 | 0.067665 |
| head_only | 10 | 0.40 | 0.000000 | 262.000000 | 0.000000 | 21.000000 | 0.925795 | N/A | 0.000000 | 1.000000 | 0.000000 | 0.500000 | 0.702490 | 0.142376 | 0.067665 |
| head_only | 10 | 0.45 | 0.000000 | 262.000000 | 0.000000 | 21.000000 | 0.925795 | N/A | 0.000000 | 1.000000 | 0.000000 | 0.500000 | 0.702490 | 0.142376 | 0.067665 |
| head_only | 10 | 0.50 | 0.000000 | 262.000000 | 0.000000 | 21.000000 | 0.925795 | N/A | 0.000000 | 1.000000 | 0.000000 | 0.500000 | 0.702490 | 0.142376 | 0.067665 |
| full_finetune | 10 | 0.05 | 20.800000 | 24.300000 | 237.700000 | 0.200000 | 0.159364 | 0.080470 | 0.990476 | 0.092748 | 0.148846 | 0.541612 | 0.685714 | 0.140845 | 0.067472 |
| full_finetune | 10 | 0.10 | 5.500000 | 233.700000 | 28.300000 | 15.500000 | 0.845230 | 0.164799 | 0.261905 | 0.891985 | 0.200462 | 0.576945 | 0.685714 | 0.140845 | 0.067472 |
| full_finetune | 10 | 0.15 | 0.100000 | 256.500000 | 5.500000 | 20.900000 | 0.906714 | 0.009091 | 0.004762 | 0.979008 | 0.006250 | 0.491885 | 0.685714 | 0.140845 | 0.067472 |
| full_finetune | 10 | 0.20 | 0.000000 | 262.000000 | 0.000000 | 21.000000 | 0.925795 | N/A | 0.000000 | 1.000000 | 0.000000 | 0.500000 | 0.685714 | 0.140845 | 0.067472 |
| full_finetune | 10 | 0.25 | 0.000000 | 262.000000 | 0.000000 | 21.000000 | 0.925795 | N/A | 0.000000 | 1.000000 | 0.000000 | 0.500000 | 0.685714 | 0.140845 | 0.067472 |
| full_finetune | 10 | 0.30 | 0.000000 | 262.000000 | 0.000000 | 21.000000 | 0.925795 | N/A | 0.000000 | 1.000000 | 0.000000 | 0.500000 | 0.685714 | 0.140845 | 0.067472 |
| full_finetune | 10 | 0.35 | 0.000000 | 262.000000 | 0.000000 | 21.000000 | 0.925795 | N/A | 0.000000 | 1.000000 | 0.000000 | 0.500000 | 0.685714 | 0.140845 | 0.067472 |
| full_finetune | 10 | 0.40 | 0.000000 | 262.000000 | 0.000000 | 21.000000 | 0.925795 | N/A | 0.000000 | 1.000000 | 0.000000 | 0.500000 | 0.685714 | 0.140845 | 0.067472 |
| full_finetune | 10 | 0.45 | 0.000000 | 262.000000 | 0.000000 | 21.000000 | 0.925795 | N/A | 0.000000 | 1.000000 | 0.000000 | 0.500000 | 0.685714 | 0.140845 | 0.067472 |
| full_finetune | 10 | 0.50 | 0.000000 | 262.000000 | 0.000000 | 21.000000 | 0.925795 | N/A | 0.000000 | 1.000000 | 0.000000 | 0.500000 | 0.685714 | 0.140845 | 0.067472 |
| random_calibrated_logical | 10 | 0.05 | 21.000000 | 0.000000 | 262.000000 | 0.000000 | 0.074205 | 0.074205 | 1.000000 | 0.000000 | 0.138158 | 0.500000 | 0.701327 | 0.141824 | 0.067670 |
| random_calibrated_logical | 10 | 0.10 | 3.700000 | 238.600000 | 23.400000 | 17.300000 | 0.856184 | 0.136166 | 0.176190 | 0.910687 | 0.153310 | 0.543439 | 0.701327 | 0.141824 | 0.067670 |
| random_calibrated_logical | 10 | 0.15 | 0.000000 | 260.100000 | 1.900000 | 21.000000 | 0.919081 | 0.000000 | 0.000000 | 0.992748 | 0.000000 | 0.496374 | 0.701327 | 0.141824 | 0.067670 |
| random_calibrated_logical | 10 | 0.20 | 0.000000 | 262.000000 | 0.000000 | 21.000000 | 0.925795 | N/A | 0.000000 | 1.000000 | 0.000000 | 0.500000 | 0.701327 | 0.141824 | 0.067670 |
| random_calibrated_logical | 10 | 0.25 | 0.000000 | 262.000000 | 0.000000 | 21.000000 | 0.925795 | N/A | 0.000000 | 1.000000 | 0.000000 | 0.500000 | 0.701327 | 0.141824 | 0.067670 |
| random_calibrated_logical | 10 | 0.30 | 0.000000 | 262.000000 | 0.000000 | 21.000000 | 0.925795 | N/A | 0.000000 | 1.000000 | 0.000000 | 0.500000 | 0.701327 | 0.141824 | 0.067670 |
| random_calibrated_logical | 10 | 0.35 | 0.000000 | 262.000000 | 0.000000 | 21.000000 | 0.925795 | N/A | 0.000000 | 1.000000 | 0.000000 | 0.500000 | 0.701327 | 0.141824 | 0.067670 |
| random_calibrated_logical | 10 | 0.40 | 0.000000 | 262.000000 | 0.000000 | 21.000000 | 0.925795 | N/A | 0.000000 | 1.000000 | 0.000000 | 0.500000 | 0.701327 | 0.141824 | 0.067670 |
| random_calibrated_logical | 10 | 0.45 | 0.000000 | 262.000000 | 0.000000 | 21.000000 | 0.925795 | N/A | 0.000000 | 1.000000 | 0.000000 | 0.500000 | 0.701327 | 0.141824 | 0.067670 |
| random_calibrated_logical | 10 | 0.50 | 0.000000 | 262.000000 | 0.000000 | 21.000000 | 0.925795 | N/A | 0.000000 | 1.000000 | 0.000000 | 0.500000 | 0.701327 | 0.141824 | 0.067670 |
| source_multiview | 1 | 0.05 | 7.000000 | 228.000000 | 34.000000 | 14.000000 | 0.830389 | 0.170732 | 0.333333 | 0.870229 | 0.225806 | 0.601781 | 0.688659 | 0.135493 | 0.069207 |
| source_multiview | 1 | 0.10 | 0.000000 | 261.000000 | 1.000000 | 21.000000 | 0.922261 | 0.000000 | 0.000000 | 0.996183 | 0.000000 | 0.498092 | 0.688659 | 0.135493 | 0.069207 |
| source_multiview | 1 | 0.15 | 0.000000 | 262.000000 | 0.000000 | 21.000000 | 0.925795 | N/A | 0.000000 | 1.000000 | 0.000000 | 0.500000 | 0.688659 | 0.135493 | 0.069207 |
| source_multiview | 1 | 0.20 | 0.000000 | 262.000000 | 0.000000 | 21.000000 | 0.925795 | N/A | 0.000000 | 1.000000 | 0.000000 | 0.500000 | 0.688659 | 0.135493 | 0.069207 |
| source_multiview | 1 | 0.25 | 0.000000 | 262.000000 | 0.000000 | 21.000000 | 0.925795 | N/A | 0.000000 | 1.000000 | 0.000000 | 0.500000 | 0.688659 | 0.135493 | 0.069207 |
| source_multiview | 1 | 0.30 | 0.000000 | 262.000000 | 0.000000 | 21.000000 | 0.925795 | N/A | 0.000000 | 1.000000 | 0.000000 | 0.500000 | 0.688659 | 0.135493 | 0.069207 |
| source_multiview | 1 | 0.35 | 0.000000 | 262.000000 | 0.000000 | 21.000000 | 0.925795 | N/A | 0.000000 | 1.000000 | 0.000000 | 0.500000 | 0.688659 | 0.135493 | 0.069207 |
| source_multiview | 1 | 0.40 | 0.000000 | 262.000000 | 0.000000 | 21.000000 | 0.925795 | N/A | 0.000000 | 1.000000 | 0.000000 | 0.500000 | 0.688659 | 0.135493 | 0.069207 |
| source_multiview | 1 | 0.45 | 0.000000 | 262.000000 | 0.000000 | 21.000000 | 0.925795 | N/A | 0.000000 | 1.000000 | 0.000000 | 0.500000 | 0.688659 | 0.135493 | 0.069207 |
| source_multiview | 1 | 0.50 | 0.000000 | 262.000000 | 0.000000 | 21.000000 | 0.925795 | N/A | 0.000000 | 1.000000 | 0.000000 | 0.500000 | 0.688659 | 0.135493 | 0.069207 |
| target_logistic | 10 | 0.05 | 19.700000 | 23.100000 | 238.900000 | 1.300000 | 0.151237 | 0.076437 | 0.938095 | 0.088168 | 0.141291 | 0.513132 | 0.593421 | 0.146731 | 0.110408 |
| target_logistic | 10 | 0.10 | 16.500000 | 77.700000 | 184.300000 | 4.500000 | 0.332862 | 0.082504 | 0.785714 | 0.296565 | 0.149169 | 0.541140 | 0.593421 | 0.146731 | 0.110408 |
| target_logistic | 10 | 0.15 | 13.700000 | 123.900000 | 138.100000 | 7.300000 | 0.486219 | 0.090893 | 0.652381 | 0.472901 | 0.159365 | 0.562641 | 0.593421 | 0.146731 | 0.110408 |
| target_logistic | 10 | 0.20 | 11.800000 | 155.200000 | 106.800000 | 9.200000 | 0.590106 | 0.100082 | 0.561905 | 0.592366 | 0.169697 | 0.577136 | 0.593421 | 0.146731 | 0.110408 |
| target_logistic | 10 | 0.25 | 9.200000 | 180.900000 | 81.100000 | 11.800000 | 0.671731 | 0.101789 | 0.438095 | 0.690458 | 0.164968 | 0.564277 | 0.593421 | 0.146731 | 0.110408 |
| target_logistic | 10 | 0.30 | 7.400000 | 200.400000 | 61.600000 | 13.600000 | 0.734276 | 0.106696 | 0.352381 | 0.764885 | 0.163612 | 0.558633 | 0.593421 | 0.146731 | 0.110408 |
| target_logistic | 10 | 0.35 | 6.700000 | 214.900000 | 47.100000 | 14.300000 | 0.783039 | 0.124511 | 0.319048 | 0.820229 | 0.178887 | 0.569638 | 0.593421 | 0.146731 | 0.110408 |
| target_logistic | 10 | 0.40 | 5.700000 | 224.900000 | 37.100000 | 15.300000 | 0.814841 | 0.133508 | 0.271429 | 0.858397 | 0.178230 | 0.564913 | 0.593421 | 0.146731 | 0.110408 |
| target_logistic | 10 | 0.45 | 4.300000 | 233.500000 | 28.500000 | 16.700000 | 0.840283 | 0.132765 | 0.204762 | 0.891221 | 0.159741 | 0.547992 | 0.593421 | 0.146731 | 0.110408 |
| target_logistic | 10 | 0.50 | 3.800000 | 240.700000 | 21.300000 | 17.200000 | 0.863958 | 0.158138 | 0.180952 | 0.918702 | 0.166916 | 0.549827 | 0.593421 | 0.146731 | 0.110408 |

## Unchanged ranking metrics

| Model | AP mean | AUROC mean | Brier mean |
|---|---:|---:|---:|
| calibrated_logical | 0.142664 | 0.702854 | 0.067654 |
| head_only | 0.142376 | 0.702490 | 0.067665 |
| full_finetune | 0.140845 | 0.685714 | 0.067472 |
| random_calibrated_logical | 0.141824 | 0.701327 | 0.067670 |
| source_multiview | 0.135493 | 0.688659 | 0.069207 |
| target_logistic | 0.146731 | 0.593421 | 0.110408 |

## Original-validation-selected operating points

| Model | Draw | Selected cutoff | TP | TN | FP | FN | accuracy | precision | recall | specificity | f1 | balanced_accuracy | auroc | ap | brier |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| calibrated_logical | ORIGINAL_VALIDATION_OPTIMAL_THRESHOLD_NOT_ESTABLISHED | N/A | N/A | N/A | N/A | N/A | N/A | N/A | N/A | N/A | N/A | N/A | N/A | N/A | N/A |
| head_only | ORIGINAL_VALIDATION_OPTIMAL_THRESHOLD_NOT_ESTABLISHED | N/A | N/A | N/A | N/A | N/A | N/A | N/A | N/A | N/A | N/A | N/A | N/A | N/A | N/A |
| full_finetune | ORIGINAL_VALIDATION_OPTIMAL_THRESHOLD_NOT_ESTABLISHED | N/A | N/A | N/A | N/A | N/A | N/A | N/A | N/A | N/A | N/A | N/A | N/A | N/A | N/A |
| random_calibrated_logical | ORIGINAL_VALIDATION_OPTIMAL_THRESHOLD_NOT_ESTABLISHED | N/A | N/A | N/A | N/A | N/A | N/A | N/A | N/A | N/A | N/A | N/A | N/A | N/A | N/A |
| source_multiview | ORIGINAL_VALIDATION_OPTIMAL_THRESHOLD_NOT_ESTABLISHED | N/A | N/A | N/A | N/A | N/A | N/A | N/A | N/A | N/A | N/A | N/A | N/A | N/A | N/A |
| target_logistic | ORIGINAL_VALIDATION_OPTIMAL_THRESHOLD_NOT_ESTABLISHED | N/A | N/A | N/A | N/A | N/A | N/A | N/A | N/A | N/A | N/A | N/A | N/A | N/A | N/A |

## Interpretation limits

These test thresholds are supplementary descriptive analyses of an already examined frozen test. They cannot establish an optimized or newly confirmed operating point. A threshold chosen retrospectively from this table would require genuinely new independent evaluation.
Authentic original-validation F1 selection, when supported, uses only171 validation participants/13 positive reports, with highest-threshold tie breaking before test probabilities are opened. It remains post-hoc and unstable. The validation-set optimized F1 itself would be optimistic; it is not reported here as independent performance.
Across-draw sample SD/ranges describe correlated fitted models, not independent-test uncertainty. Undefined precision is N/A, not zero or successful performance. The21 test positives limit sensitivity precision; one changed case changes recall by1/21. High all-negative accuracy is not useful event detection.
AP is the ranked average precision statistic, not fixed-threshold precision or trapezoidal area under these ten displayed grid points. Threshold changes cannot alter AP/AUROC/Brier without changing scores. No calibration fitting or score transformation occurs.
The registered historical findings and inconclusive comparison remain unchanged. This output does not establish clinical validity, superiority, external confirmation or permission for deployment. Do not update the B.Tech report or release cells without applicable disclosure review.
