# Small-partition stopping and threshold calibration

## Label accounting and isolation

F/design.py:6–27 sorts participant IDs, permutes without outcomes, reserves outer folds, then chooses nested prefixes of the remaining membership. Every fifth selected participant is assigned according to FIT,FIT,FIT,STOP,CALIBRATION. Every conditioning label is counted, including source-relative selector supervision on FIT. STOP labels choose epochs, CALIBRATION labels choose thresholds, and OUTER labels evaluate only. All roles are disjoint within a split. Outer labels remain evaluation-label costs, not free information.

The public 679-person pool gives outer training size 452–453 with three folds. The following is **design arithmetic**, not a private count disclosure. Shown counts use a 452-person training side; at 100% a 453-person side adds one FIT participant.

| Budget | Total labels | FIT | STOP | CALIBRATION | Expected STOP positives* | P(zero STOP positives)* | P(calibration ≥5 of each class)* |
|---|---:|---:|---:|---:|---:|---:|---:|
| 10% | 45 | 27 | 9 | 9 | .649 | .5075 | 0 |
| 25% | 113 | 69 | 22 | 22 | 1.588 | .1873 | .0164 |
| 50% | 226 | 136 | 45 | 45 | 3.247 | .0305 | .2173 |
| 75% | 339 | 204 | 68 | 67 | 4.907 | .0046 | .5433 |
| 100% | 452 | 272 | 90 | 90 | 6.495 | .0007 | .8056 |

*Marginal random-subset calculations using the already public pool totals 49 positive/679. With X~Hypergeometric(N=679,K=49,n), E[X]=nK/N, P(X=0)=C(630,n)/C(679,n). Calibration support sums P(X=k) for 5≤k≤n−5. These are probabilities over the label-blind allocation design conditional on those public totals, not realized fold counts, calibrated precision guarantees, or independent probabilities between roles. Repeated folds/seeds overlap. No extra cohort was inspected to construct this table.

The prior label-informed pool/draw construction and architecture selection are historical label exposure that cannot be undone. The percentage budget is incremental conditioning cost, not a demonstrated prospective annotation saving. Repeats do not create new participants or new independent studies. The old 171-person validation cohort is not used in this follow-up's learning or scoring.

## Exact stopping behavior

`fit`, F/vendor/train_exploratory_candidates.py:46–72:

- Max target 20 epochs, patience five, batch64, AdamW .001/decay .0001.
- Select checkpoint by **unweighted STOP BCE**, strict improvement greater than 1e-5. AP/AUROC/Brier are logged, not selection criteria. There is no AP-driven stopping implementation in these four methods.
- Single-class fitting or stopping is allowed. BCE remains finite; AUROC is undefined for a one-class STOP set, AP undefined when STOP has no positives. No classes are fabricated or favorable split redrawn.
- `bestloss=inf` excludes the pretrained starting point from competition. The first finite epoch wins even if worse than epoch zero. Copying the initial `state_dict` into `best` does not make it eligible without evaluating its loss.
- At low event support, BCE can reward near-zero probabilities and select epochs without evidence of useful event ranking. This is a scientific limitation, not an exception or automatic numerical bug.

Synthetic conflict fixture: the source predicts the stopping labels correctly, but fitting labels request reversal. Initial stopping BCE .12692806; production selects epoch1 BCE .13055249. A nonactive comparison with the initial model would select epoch0. This demonstrates a missing safeguard, not proof it caused either completed experiment's results.

## Threshold behavior

F/design.py:30–38 requires at least five positives and five negatives. Unsupported calibration returns `INSUFFICIENT_CALIBRATION_CLASS_SUPPORT` and threshold None. No fallback, zero substitution, split redraw or support relaxation occurs. A 9-person calibration subset is necessarily unsupported.

Supported calibration maximizes F1 over unique candidate scores plus 0,.5,1; ties select the highest threshold. Classification is p≥threshold, including score ties. This is a **decision-threshold rule**, not probability calibration. No Platt, isotonic or temperature map is fitted. The threshold is frozen before outer outcomes are scored. It does not change AP/AUROC/Brier for unchanged probabilities.

`results_report.py:46–58` sums confusion matrices only on outer folds with supported calibration, and computes fixed-.50 comparison on those identical folds. Unsupported coverage is explicit; the calibrated subset is not compared with a larger fixed-threshold denominator. Primary ranking summaries require complete OOF coverage. Tests reproduce support-matched aggregation and missing-calibration handling.

All-negative predictions with some actual events give recall0/F1=0, undefined precision and undefined MCC. Correctly reporting precision None matters: accuracy can be high without detecting any events. With no observed negatives specificity and AUROC are undefined; with no positives recall/AP/AUROC are undefined. Constant-score AP equals prevalence when positives exist; no special favorable ranking is invented.

## Reproduced instability

The tests cover zero/one STOP positives; 0,1,4,5,6 calibration positives; all-negative predictions; single-class outcomes; constant scores; near ties; highly skewed scores; and deterministic tie handling. Class-support failure remains unavailable.

An invented calibration population (100 observations/10 positives) was resampled 100 times without replacing unsupported resamples with favorable ones. Of 100 resamples, 99 supported the rule; selected thresholds ranged .04381–.37368 (median .25149). On one separate fixed invented evaluation population, recall ranged .03–.94 and F1 .0583–.2968 solely because of calibration resampling. At .50 the same invented model had recall0 and undefined precision. This is a stress example, not a confidence interval, not a real outcome report, and not evidence that lowering a threshold guarantees future sensitivity.

## Future interventions: feasibility and risks

1. **Retain source/epoch zero as a prespecified STOP-BCE checkpoint candidate.** No additional labels; small engineering change, but it guarantees only the chosen stopping loss cannot exceed the candidate source loss, not improvement in AP or future generalization. Reusing STOP to choose this source/adapted model is part of paid model selection.
2. **Inner out-of-fold threshold calibration.** Could use more training-side observations for calibration, but every OOF prediction must exclude that observation from weight fitting, stopping, selector supervision and preprocessing fit. All labels count toward budget; a final refit may have a different score scale. More fits, tiny per-fold class support and correlated OOF scores remain limitations. A new protocol is needed; no in-place split change.
3. **Prespecified sensitivity objective with uncertainty.** The sensitivity target must come from a decision/clinical-cost rationale before outcomes. Five calibration events cannot provide a reliable high-sensitivity guarantee. Report binomial uncertainty and specificity costs on untouched outer participants; do not select a convenient target from completed results.
4. **Regularized sigmoid/Platt calibration.** Requires both classes and sufficient calibration events; fitting intercept/slope to nine or 22 low-event observations may be unstable. Fit only training-side or cross-fitted data. A positive-slope monotone transform preserves rankings but may improve or worsen Brier; negative-slope fitting changes rankings and must not be called a mere threshold adjustment. Evidence from modern networks does not certify calibration in these survey cohorts. See [Guo et al., 2017](https://proceedings.mlr.press/v70/guo17a.html).
5. **Isotonic calibration.** Low priority at these sample sizes; nonparametric steps overfit scarce observations, and ties can change ranking metrics. The [official scikit-learn reference](https://scikit-learn.org/stable/modules/generated/sklearn.calibration.CalibratedClassifierCV.html) warns against isotonic with very small calibration samples (well below 1,000). This is guidance, not a project-specific event threshold or authorization.
6. **Class-prior-aware threshold/intercept correction.** Only justified under appropriate sampling/prior-shift assumptions and an independently defensible target prior. Different survey ascertainment may violate those assumptions. An intercept shift cannot repair poor ranking; never estimate a target prior from outer outcomes to tune predictions.
7. **Bootstrap threshold stability.** Resample training-side calibration observations only, retain unsupported repetitions, report threshold/decision instability locally. Bootstrapping five events creates no new independent information and does not justify clinical claims.
8. **Alternative stopping losses.** BCE is defined for single-class sets and often more stable numerically than AP, but emphasizes probability fit; AP/weighted losses on one or two events are noisy. Fixed source-validated epochs or cross-fitted losses require a prespecified study with outer isolation. Do not switch stopping objective after looking at the same evaluation outcomes and call it confirmation.

Any new calibration/stopping study needs fresh independent execution authorization, versioned outputs and a new decision record. No clinical tuning or new private operation was performed in this audit.
