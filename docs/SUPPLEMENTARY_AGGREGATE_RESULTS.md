# Final HAALSI → MHAS aggregate results

**Frozen study:** `public-haalsi-mhas-v2`. **Endpoint:** wave-observed, doctor-reported heart attack or stroke among participants with an observed outcome. **Status:** experimental phase closed. All held-out values below come from the existing [aggregate-only recovery result](../results/aggregate_only_results.json), SHA256 `b23106ccae093c0bcfcc63a2754d443a9b67f50ea65cbaafc04dbed003595bf3`. No participant-level test data were opened for this report.

## Primary registered contrast

The locked MHAS test contains **283 people and 21 positive reports**. Ten frozen, paired 25-positive/75-negative adaptation draws were evaluated on this **one shared test population**. Mean calibrated-logical AP was **0.142664**; mean full-fine-tuning AP was **0.140845**. The registered mean within-draw paired difference was **+0.001819**. Its descriptive 95% joint participant-bootstrap percentile interval was **−0.024809 to +0.032340** (2,000 replicates, seed `20261026`, zero invalid AP replicates). This interval spans differences in both directions. **Selective-adaptation superiority is not established.** No post-test method or threshold was selected.

## Held-out method inventory

AP intervals are descriptive joint participant-bootstrap 95% percentile intervals, not intervals from ten independent test cohorts. AUROC and Brier are point estimates; their intervals are retained in the frozen aggregate JSON. The four source-only models use one checkpoint each; adapted models are arithmetic means over ten paired draws. Observed test prevalence is **21/283 = 0.0742**.

### Primary 25 + 75 adaptation labels

| Registered method | AP (95% interval) | AUROC | Brier |
|---|---:|---:|---:|
| Source logistic regression | 0.0946 (0.0562, 0.1608) | 0.5885 | 0.0695 |
| Source XGBoost | 0.1309 (0.0729, 0.2745) | 0.6078 | 0.0693 |
| Source flat MLP | 0.1177 (0.0729, 0.2108) | 0.6652 | 0.0698 |
| Source five-view network | 0.1355 (0.0807, 0.2416) | 0.6887 | 0.0692 |
| Head-only fine-tuning | 0.1424 (0.0843, 0.2577) | 0.7025 | 0.0677 |
| Full fine-tuning | 0.1408 (0.0845, 0.2491) | 0.6857 | 0.0675 |
| Target logistic regression | 0.1467 (0.0821, 0.2682) | 0.5934 | 0.1104 |
| Target-only five-view network | 0.1243 (0.0806, 0.2064) | 0.6042 | 0.0891 |
| Fixed fusion mask | 0.1431 (0.0857, 0.2547) | 0.6879 | 0.0675 |
| Parameter-matched random | 0.1418 (0.0842, 0.2560) | 0.7013 | 0.0677 |
| Legacy top-k | 0.1428 (0.0857, 0.2538) | 0.6873 | 0.0675 |
| Calibrated threshold | 0.1427 (0.0846, 0.2584) | 0.7029 | 0.0677 |
| **Calibrated logical, prespecified primary** | **0.1427 (0.0846, 0.2584)** | **0.7029** | **0.0677** |

The secondary AP contrasts for logical minus head-only and logical minus matched random were **+0.000288** (−0.000707, +0.001350) and **+0.000841** (−0.000120, +0.002669), respectively. Logical minus source-only five-view AP was **+0.007172** (−0.003773, +0.035074). All these intervals include zero. Logical minus full AUROC was +0.017139 (−0.027646, +0.060456); logical minus full Brier was +0.000182 (−0.000364, +0.000812), where lower Brier is better.

### Secondary 10 + 30 adaptation labels

| Registered method | AP (95% interval) | AUROC | Brier |
|---|---:|---:|---:|
| Source logistic regression | 0.0946 (0.0562, 0.1608) | 0.5885 | 0.0695 |
| Source XGBoost | 0.1309 (0.0729, 0.2745) | 0.6078 | 0.0693 |
| Source flat MLP | 0.1177 (0.0729, 0.2108) | 0.6652 | 0.0698 |
| Source five-view network | 0.1355 (0.0807, 0.2416) | 0.6887 | 0.0692 |
| Head-only fine-tuning | 0.1401 (0.0827, 0.2507) | 0.6979 | 0.0678 |
| Full fine-tuning | 0.1328 (0.0814, 0.2361) | 0.6689 | 0.0678 |
| Target logistic regression | 0.1194 (0.0742, 0.2079) | 0.5530 | 0.1326 |
| Target-only five-view network | 0.1215 (0.0804, 0.1979) | 0.5774 | 0.0999 |
| Fixed fusion mask | 0.1335 (0.0822, 0.2363) | 0.6717 | 0.0677 |
| Parameter-matched random | 0.1407 (0.0835, 0.2515) | 0.6973 | 0.0677 |
| Legacy top-k | 0.1330 (0.0809, 0.2360) | 0.6696 | 0.0677 |
| Calibrated threshold | 0.1413 (0.0840, 0.2536) | 0.6978 | 0.0677 |
| **Calibrated logical** | **0.1407 (0.0835, 0.2515)** | **0.6973** | **0.0677** |

The secondary logical-minus-full AP contrast was **+0.007938** (−0.014184, +0.032761). Logical minus head-only was +0.000651 (−0.002907, +0.004723). Logical minus matched random was **exactly zero**, including its registered interval, because the ten corresponding masks and trained states coincided. This is control degeneracy, not independent confirmation of selector performance. No AP, AUROC or Brier bootstrap replicates were discarded in the registered primary or secondary analyses.

## Across-draw variation and negative transfer

| Budget | Method | Test AP SD across ten draws | Test AP range | Draws below source five-view AP |
|---|---|---:|---:|---:|
| 25 + 75 | Logical | 0.00271 | 0.13687–0.14548 | 0/10 |
| 25 + 75 | Head-only | 0.00256 | 0.13687–0.14548 | 0/10 |
| 25 + 75 | Full | 0.01282 | 0.12521–0.16822 | 4/10 |
| 25 + 75 | Matched random | 0.00311 | 0.13680–0.14548 | 0/10 |
| 10 + 30 | Logical | 0.00426 | 0.13543–0.15017 | 1/10 |
| 10 + 30 | Head-only | 0.00294 | 0.13543–0.14367 | 1/10 |
| 10 + 30 | Full | 0.01681 | 0.10770–0.15701 | 4/10 |
| 10 + 30 | Matched random | 0.00426 | 0.13543–0.15017 | 1/10 |

The last column is a descriptive count of frozen adaptation draws whose test AP was below the single frozen source five-view AP (0.13549). It is **not** a population negative-transfer rate: the draws overlap and share the same test people. It was derived arithmetically from the already public per-draw aggregate metrics; no predictions were recomputed.

## Parameter use and selector diagnostics

The five-view network has **8,033** parameters. Its 33-parameter head is always trainable during adaptation. All fractions below include the head.

| Method | Primary mean trainable | Primary fraction | Low-label mean trainable | Low-label fraction |
|---|---:|---:|---:|---:|
| Head-only | 33 | 0.41% | 33 | 0.41% |
| Full fine-tuning | 8,033 | 100% | 8,033 | 100% |
| Fixed fusion mask | 7,489 | 93.23% | 7,489 | 93.23% |
| Matched random | 44.2 | 0.55% | 564.2 | 7.02% |
| Legacy top-k | 7,693.8 | 95.78% | 7,183.4 | 89.42% |
| Calibrated threshold | 41 | 0.51% | 572.2 | 7.12% |
| Calibrated logical | 41 | 0.51% | 564.2 | 7.02% |

Calibrated logical selected **no view or fusion module in nine of ten draws at each budget**. It selected haemodynamic once in the primary budget and fusion1 once in the low-label budget. Background, metabolic, behaviour and comorbidity/medication had `uncertain_source_geometry` in all ten draws per budget, causing the frozen selector to abstain to SHARE. This is a class-geometry evidential limitation, not evidence those clinical views are unimportant. The mean pairwise logical mask Jaccard was 0.800 in both budgets, mostly driven by nine all-SHARE masks. The random mask equalled the logical mask in **9/10 primary** and **10/10 low-label** draws; many budgets had only one feasible closest-budget mask. Fixed and legacy masks trained most of the network because the fusion blocks dominate parameter count. The detailed 6B mask and selector records remain internal; this release includes a [method and reproducibility summary](PHASE1_METHOD_AND_REPRODUCIBILITY.md).

## Validation, calibration, and interpretation

Development validation used the **same 171 people with 13 positive reports** for early stopping and reporting. Under 25 + 75 labels, logical, full, head-only and matched-random validation AP means were **0.1840, 0.1878, 0.1859 and 0.1847**. Their held-out test means were **0.1427, 0.1408, 0.1424 and 0.1418**. Under 10 + 30, logical and full validation AP were **0.1769 and 0.2044**, versus test AP **0.1407 and 0.1328**. These shifts are descriptive; the validation and test partitions differ, and 13/21 positive reports make AP unstable. The test did not trigger another checkpoint choice.

Adaptation draws were deliberately enriched to **25%** positive labels, versus about **7.4%** in the locked test. Mean predicted probability and fixed-bin calibration summaries are in the public/private aggregate scheme, but small-cell observed bin fractions remain private. No recalibrator was fitted. Brier score is reported as a scoring rule; none of these probabilities is established as calibrated individual clinical risk. The endpoint is a survey-reported outcome conditional on observed follow-up, with possible diagnosis misclassification and attrition selection.

The 0–14-day timing analysis was deferred because its inherited test/validation event counts were below the primary floors. The nine-feature diabetes-omitted configuration and alternative endpoint definitions had no frozen models in this final registration; **no final-test sensitivity result exists** for them. Their absence must be reported rather than filled in after seeing test results.
