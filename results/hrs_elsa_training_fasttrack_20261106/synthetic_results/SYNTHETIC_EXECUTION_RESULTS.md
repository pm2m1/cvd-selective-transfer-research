# ACTUALLY EXECUTED — INVENTED DATA ONLY

This is a software demonstration, **not HRS/ELSA participant data, clinical results, a feasibility count or a method-improvement claim**. Generated source/target distributions differ, share correlated feature views, contain missing predictors and imbalanced later-report labels, and exclude invented prior/unknown-follow-up cases. Splits are outcome-blind and participant-disjoint.

Actual source-tree execution:

```sh
.venv/bin/python -B results/hrs_elsa_training_fasttrack_20261106/scripts/run_experiment.py --synthetic-demo --output results/hrs_elsa_training_fasttrack_20261106_SYNTHETIC_FINAL_RUN --device cpu
```

It completed with `SYNTHETIC_ONLY COMPLETE NO_REAL_COHORT_OR_CLINICAL_PERFORMANCE_CLAIM`.

## Invented held-out results

All metrics below use the separate invented test after development selected/froze the models. They must not be compared numerically with historical MHAS metrics as equivalent populations.

| Method | Raw AP | Raw AUROC | Raw Brier | TP/TN/FP/FN at0.50 | Recall at training-side operating point |
|---|---:|---:|---:|---|---:|
| source_logistic | 0.340730 | 0.546738 | 0.192309 | 2/76/3/24 | 0.462 |
| source_regularized | 0.328111 | 0.550146 | 0.207762 | 4/66/13/22 | 0.538 |
| source_boosting | 0.235595 | 0.457400 | 0.192085 | 0/79/0/26 | 0.731 |
| source_dmvmat | 0.308888 | 0.497079 | 0.191867 | 0/79/0/26 | 0.538 |
| head | 0.308888 | 0.497079 | 0.191867 | 0/79/0/26 | 0.538 |
| full | 0.308888 | 0.497079 | 0.191867 | 0/79/0/26 | 0.538 |
| selective | 0.308888 | 0.497079 | 0.191867 | 0/79/0/26 | 0.538 |

Development selected **source_dmvmat** using development AP only. The held-out values were not used to revise that selection. All adapted neural methods selected epoch zero in this demonstration; they therefore retain the source score here. This is a valid execution outcome, not evidence that adaptation works or fails on the real studies. Actual optimizer updates/backpropagation and selected-weight restoration were exercised; training curves are retained in the aggregate JSON.

The new network has8,017 parameters and33 head parameters. Final frozen parameter masks and trainable counts are recorded per method. Total target-label use includes fitting, stopping, calibration and model-selection roles; integrity-read label rows are also separately reported. Full fixed0.50 and training-side calibrated threshold metrics, unavailable states, calibration summaries and paired bootstrap outputs are in `SYNTHETIC_evaluation.json`. They are illustrative; the50-resample demonstration is not a formal precision guarantee.

Only these invented aggregate results are distributed in the public ZIP. The separate public invented run directory also contains generated arrays and model artifacts for local inspection/reproduction; no actual clinical inputs/checkpoints were copied. First exploratory debug runs were not overwritten. No original experiment or protected count operation was rerun.
