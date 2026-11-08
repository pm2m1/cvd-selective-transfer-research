# Prospective training/evaluation protocol — engineering candidate V1

This AI-authored protocol specifies public engineering before real inputs are available. It is not a count-policy amendment, a scientific sign-off, an adopted strict HRS endpoint or authorization. Current real modeling remains BLOCKED. The machine counterpart is `configs/training_protocol.json`.

## Question and cohort identity

Within an explicitly adopted source-specific sensitivity research question, does selective adaptation improve target AP relative to full fine-tuning, with head-only and conventional source baselines? HRS screening-assumed MI negatives remain sensitivity-only. ELSA requires verified baseline MI/stroke absence and qualifying personal subsequent reports. Neither is clinically adjudicated onset. Unknown/disputed/censored outcomes must be excluded from binary modeling under the reviewed upstream contract, not assigned zero.

Primary target is W6→W9; W4→W7 is a separate comparator, not a post-hoc replacement or independent replication. Source design metadata is `HRS_2012_2018_SOURCE_SPECIFIC_REPORT`; target is explicitly `W6_W9` or `W4_W7`. Development and test must share the same frozen window. The comparator is retrospective transport, not a model historically deployed before HRS2012 training information existed.

## Partitions and label accounting

Prospective target fractions are40% fitting,10% stopping,10% calibration,10% model selection,30% untouched evaluation. These five roles are **not** the old counter's four-role50/15/15/20 capacity scenario. New support must be established for the actual model design; the old scenario cannot certify it. Use one fixed, outcome-blind hash-to-uniform mapping with fixed cumulative boundaries. A person's role remains stable across windows/subsets with the same fractions and namespace. Do not redraw until event counts look favorable. Preserve exact frozen assignments and prior-use evidence privately.

Source fitting/stopping is independently frozen at75/25 in the synthetic example; actual source capacity and memberships need prior review. The primary fitting budget is100 outcome-blind target-fitting participants; prospective capacities40/100/200 are documented, but no real learning curves are executed here. Stopping, calibration and model-selection labels are additional consumed labels, not free resources. Report fitting labels used, total modeling labels used and all label rows read for integrity. The canonical export should include only the prespecified fitting cohort where practical; this pipeline does not pretend to have zero access to unused fitting-pool labels loaded for integrity checking.

All eight predictors must have justified baseline construct/timing eligibility. Source-training median/mode imputation plus missingness indicators is a benchmark for eligible missing cells, not multiple imputation or evidence of MAR. Missing exams, uncertain nurse chronology, topcoded age without an adopted representation and unobserved outcomes are not repaired by this method.

## Models and selection

Exactly seven families are implemented in `TRAINING_ARCHITECTURE.md`. Hyperparameter space is a singleton per family: no excessive search over sparse validation events. Source weights/preprocessing and initialization are shared across the neural comparisons. Target epoch zero is eligible; the real protocol's efficacy remains unknown. Configurations/folds/seeds are frozen before evaluation. Source preprocessing is never refit on any target role.

Adaptation requires both classes in fitting; otherwise that candidate is recorded unavailable. Source fitting requires both classes. Selection validation requires both classes; otherwise the operation stops without pretending AP is estimable. Incomplete registered comparisons are blocked before final test access. Tiny stopping sets can still yield noisy BCE checkpoint selection and must be judged by the private feasibility assessment, not software success.

Primary development selection is raw AP; ties use lower Brier then fixed method order. Selection data are distinct from optimizer stopping and calibration. It is still development selection and not independent confirmation. All seven methods, hyperparameters and operating points are registered before held-out evaluation; the primary scientific paired contrast is **selective minus full raw AP**, regardless of which deployment method development selected.

## Calibration and decisions

Fixed raw threshold0.50 is always reported, including all-negative behavior, zero recall and undefined precision. Ranking AP/AUROC are calculated on raw scores. A separate target-calibration population fits positive-slope Platt scaling only with at least10 observations of each class; otherwise probability recalibration is unavailable. A nonpositive slope is not used to reverse ranking. F1 threshold selection on training-side calibrated/raw probabilities requires5 per class; ties choose the higher threshold. Insufficient support gives null threshold/metrics, not an invented fallback benefit.

The calibration set's own optimized F1 would be optimistic resubstitution; it is not an independent result. Report operating-point performance on distinct validation or finally locked test participants. Target calibration consumes labels even for a source-only score model. Threshold changes cannot improve raw ranking AP/AUROC. No held-out outcome refits a calibrator, threshold, mask or model.

## Evaluation and uncertainty

Report TP/TN/FP/FN, accuracy, precision, recall/sensitivity, specificity, F1, AP, AUROC, Brier, prevalence, positive-prediction counts, mean prediction and fixed-decile calibration summaries. Undefined quantities remain null. High accuracy from predicting all negatives is not useful event detection. No model performance is predicted from prevalence or event counts.

Use1000 paired participant bootstrap resamples of the same held-out people/paired model predictions, seed20261106; record single-class unavailable resamples. The demonstration uses50 and is not a precision study. Report per-method AP/AUROC/Brier intervals and the prespecified selective-minus-full AP interval. This conditions on fitted models and the sampled participants; it does not include training, imputation-model, complex-survey, censoring or ascertainment uncertainty. A higher point estimate alone does not establish superiority.

Independent-test event/support and precision requirements are in `COUNT_FEASIBILITY_ACCEPTANCE.md`; the project's200-event goal is retained as an aim, not a universal sufficiency theorem. Adequate source development needs its own model-complexity/signal assessment. Missing outcomes, repeated seeds or overlapping windows cannot manufacture independent events.

## Execution and disclosure

Real preflight reads independently permitted evidence/manifest metadata only, never participant-array bytes or the test bundle during development. It checks recorded facts, not the truth of independent scientific judgments or legal rights. Private readiness gates must be supported by actual bound records, not toggled to obtain PASS. Local preflight/authorization statuses stay within the controlled environment until any necessary disclosure clearance; do not present them as a public empirical GO verdict.

Development training and held-out evaluation are separate single-use independent-human purposes. The original runtime's agent/CI guards, interactive attestations, exact config/code/output bindings and permanent consumed destinations remain intact. Test models/thresholds/runtime/algorithm bindings are checked before test-array reads. No old MHAS test, ELSA count authorization or completed diagnostic is reused. A failed operation remains consumed; no automatic retry or subsequent modeling occurs.
