# INVENTED SYNTHETIC EXAMPLE — frozen-score threshold sweep

DISCLOSURE NOT CLEARED. Keep all counts, tables, figures and this report inside the authorized environment.
SYNTHETIC DATA ONLY; NOT CLINICAL FINDINGS.
Distinct test participants: 283; positive reports: 21; negative observations: 262.
Ten adaptation draws reuse ONE shared population. They are not ten independent cohorts or 2,830 independent participants.
Predicted positive means probability >= cutoff. Undefined ratios are N/A. AP/AUROC/Brier remain unchanged for unchanged scores.
The complete fixed grid was specified before this calculation. No best test threshold is selected or highlighted.

Validation threshold status: **ORIGINAL_VALIDATION_OPTIMAL_THRESHOLD_NOT_ESTABLISHED**.
If authentic original validation scores are unavailable, no validation-optimal threshold is established. New scores or test-selected cutoffs are not substitutes.

## Per-draw data

See threshold_metrics_per_draw.private.csv and threshold_sweep.private.json. Each confusion SVG represents ONE model/draw/operating point with integer counts. No fractional mean is plotted as one confusion matrix.

## Descriptive model/threshold means

Each row below is a mean of per-draw metrics on the same people. Mean TP/TN/FP/FN may be fractional; they are descriptive expectations across fitted draws, not one realized matrix. Source-only has one original score vector, not ten duplicated draws.

| Model | Draws | Cutoff | TP | TN | FP | FN | accuracy | precision | recall | specificity | f1 | balanced_accuracy | auroc | ap | brier |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| INVENTED_LOGICAL | 10 | 0.05 | 19.200000 | 21.000000 | 241.000000 | 1.800000 | 0.142049 | 0.073771 | 0.914286 | 0.080153 | 0.136524 | 0.497219 | 0.511596 | 0.092182 | 0.147918 |
| INVENTED_LOGICAL | 10 | 0.10 | 17.400000 | 42.200000 | 219.800000 | 3.600000 | 0.210601 | 0.073370 | 0.828571 | 0.161069 | 0.134797 | 0.494820 | 0.511596 | 0.092182 | 0.147918 |
| INVENTED_LOGICAL | 10 | 0.15 | 15.900000 | 65.500000 | 196.500000 | 5.100000 | 0.287633 | 0.074922 | 0.757143 | 0.250000 | 0.136346 | 0.503571 | 0.511596 | 0.092182 | 0.147918 |
| INVENTED_LOGICAL | 10 | 0.20 | 14.600000 | 92.200000 | 169.800000 | 6.400000 | 0.377385 | 0.079405 | 0.695238 | 0.351908 | 0.142506 | 0.523573 | 0.511596 | 0.092182 | 0.147918 |
| INVENTED_LOGICAL | 10 | 0.25 | 12.800000 | 112.900000 | 149.100000 | 8.200000 | 0.444170 | 0.079383 | 0.609524 | 0.430916 | 0.140421 | 0.520220 | 0.511596 | 0.092182 | 0.147918 |
| INVENTED_LOGICAL | 10 | 0.30 | 11.200000 | 132.400000 | 129.600000 | 9.800000 | 0.507420 | 0.079882 | 0.533333 | 0.505344 | 0.138878 | 0.519338 | 0.511596 | 0.092182 | 0.147918 |
| INVENTED_LOGICAL | 10 | 0.35 | 8.900000 | 152.100000 | 109.900000 | 12.100000 | 0.568905 | 0.075247 | 0.423810 | 0.580534 | 0.127711 | 0.502172 | 0.511596 | 0.092182 | 0.147918 |
| INVENTED_LOGICAL | 10 | 0.40 | 6.800000 | 175.800000 | 86.200000 | 14.200000 | 0.645230 | 0.073656 | 0.323810 | 0.670992 | 0.119862 | 0.497401 | 0.511596 | 0.092182 | 0.147918 |
| INVENTED_LOGICAL | 10 | 0.45 | 5.300000 | 195.900000 | 66.100000 | 15.700000 | 0.710954 | 0.074901 | 0.252381 | 0.747710 | 0.115319 | 0.500045 | 0.511596 | 0.092182 | 0.147918 |
| INVENTED_LOGICAL | 10 | 0.50 | 3.600000 | 219.100000 | 42.900000 | 17.400000 | 0.786926 | 0.077832 | 0.171429 | 0.836260 | 0.106784 | 0.503844 | 0.511596 | 0.092182 | 0.147918 |

## Unchanged ranking metrics

| Model | AP mean | AUROC mean | Brier mean |
|---|---:|---:|---:|
| INVENTED_LOGICAL | 0.092182 | 0.511596 | 0.147918 |

## Original-validation-selected operating points

| Model | Draw | Selected cutoff | TP | TN | FP | FN | accuracy | precision | recall | specificity | f1 | balanced_accuracy | auroc | ap | brier |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| INVENTED_LOGICAL | ORIGINAL_VALIDATION_OPTIMAL_THRESHOLD_NOT_ESTABLISHED | N/A | N/A | N/A | N/A | N/A | N/A | N/A | N/A | N/A | N/A | N/A | N/A | N/A | N/A |

## Interpretation limits

These test thresholds are supplementary descriptive analyses of an already examined frozen test. They cannot establish an optimized or newly confirmed operating point. A threshold chosen retrospectively from this table would require genuinely new independent evaluation.
Authentic original-validation F1 selection, when supported, uses only171 validation participants/13 positive reports, with highest-threshold tie breaking before test probabilities are opened. It remains post-hoc and unstable. The validation-set optimized F1 itself would be optimistic; it is not reported here as independent performance.
Across-draw sample SD/ranges describe correlated fitted models, not independent-test uncertainty. Undefined precision is N/A, not zero or successful performance. The21 test positives limit sensitivity precision; one changed case changes recall by1/21. High all-negative accuracy is not useful event detection.
AP is the ranked average precision statistic, not fixed-threshold precision or trapezoidal area under these ten displayed grid points. Threshold changes cannot alter AP/AUROC/Brier without changing scores. No calibration fitting or score transformation occurs.
The registered historical findings and inconclusive comparison remain unchanged. This output does not establish clinical validity, superiority, external confirmation or permission for deployment. Do not update the B.Tech report or release cells without applicable disclosure review.
