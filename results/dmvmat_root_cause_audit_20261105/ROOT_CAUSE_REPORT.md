# DMV-MAT CVD public root-cause audit — 5 November 2026

AI-authored engineering and methodological assessment. Scope: public implementation and invented synthetic observations. No independent human scientific approval is claimed. No clinical data, private configurations, private results, authorization records, frozen-test materials or protected directories were accessed. The user's descriptions of real development findings are hypotheses to explain, not measurements independently verified here.

## Decision

**No confirmed implementation bug was established in the tested SHARE/ADAPT, freezing, optimizer, split-isolation or threshold paths.** Logical parameter-count variation is expected from module masks. This conclusion is limited to inspected code and tested invariants; it is not a certification of all possible executions.

Three reproducible design mechanisms deserve priority over assuming a broken selector:

1. **Adaptation is forced to choose a post-update checkpoint.** The source/epoch-zero model is copied into `best`, but its stopping loss is never evaluated: `bestloss=inf` means the first finite target epoch wins. A synthetic case returned stopping BCE 0.13055249 instead of the better initial 0.12692806. This is a missing source-retention option, not a violation of the currently written protocol.
2. **Small random label partitions make calibration unsupported or unstable.** The 10% condition reserves nine calibration labels and cannot meet five positives plus five negatives. Stopping uses BCE and still runs when there are zero positives; this is numerically defined but carries almost no positive-event selection evidence. No synthetic label was changed to repair this condition.
3. **Pooled cross-fold scores can penalize adapted models even without worse within-fold ranking.** Two perfect-ranking folds with differing score offsets gave pooled AP 0.833333 and AUROC 0.75, versus 1.0/1.0 for a shared source reference. This is a real property of the registered pooled-OOF estimand, not evidence that its calculation is wrong. Actual contribution to the private study remains unknown.

## Classification of findings

| Finding | Classification | Evidence boundary |
|---|---|---|
| Logical count changes with selected modules; fusion layers dominate count | EXPECTED BY DESIGN | Exact module counts and all 128 masks tested |
| Shared parameters frozen; optimizer contains exactly trainable parameters | EXPECTED BY DESIGN | Bitwise checks and optimizer-ID assertions |
| Invalid/uncertain geometry abstains to SHARE, with head still trainable | EXPECTED BY DESIGN | Reference-rule tests; no fallback to full adaptation |
| All seven internal modules may adapt when all seven satisfy the rule | EXPECTED BY DESIGN | No top-k/quota rule exists for logical |
| Epoch zero is excluded from stopping competition | EXPECTED BY DESIGN; risk demonstrated | Synthetic counterexample; no frozen implementation changed |
| Zero-positive fitting/stopping can lower ranking despite better Brier | PLAUSIBLE BUT UNVERIFIED for real study | Reproduced on invented data |
| Aggressive LR, forgetting, real conditional shift, clinical miscalibration | PLAUSIBLE BUT UNVERIFIED | Private drift/gradient/curve evidence was not inspected |
| Statistical evidence of real negative transfer or causal explanation of rank reversal | INSUFFICIENT EVIDENCE | User observations alone do not establish paired effects or cause |
| Confirmed frozen-code specification violation | None established | No production patch proposed or deployed |

## Source-code evidence index

`F` below is `../label_efficiency_followup_20261105/`. `S` is `../supervisor_metrics_and_improvement_20261104/public_development_staging_20261104/`. These are public source locations, not private experiment outputs. Line numbers refer to the bytes fingerprinted in the audit.

| Claim | Public source/function and lines |
|---|---|
| Five encoders, fusion sizes, seven selectable modules | F/vendor/frozen_public/models/multiview_mlp.py:10–17, 26–60 |
| Exact freezing/head behavior; immutable shared-module comparison | F/vendor/frozen_public/transfer/adapt.py:13–45 |
| Fresh AdamW, BCE, epoch selection and no initial-loss comparison | F/vendor/train_exploratory_candidates.py:37–72 (`fit`) |
| Four shared configurations and old seven-candidate execution | Same file:100–142 (`candidate_plan`, `run`) |
| MMD, bootstrap geometry, logical decisions and validity screens | F/vendor/frozen_public/transfer/calibration.py:17–179 |
| Source-relative point geometry and validity definitions | F/vendor/frozen_public/transfer/scores.py:12–57 |
| Source cache, clone initialization, fit-only selection, inner stop, no outcome access in inference | F/experiment.py:17–83 (`TrainingAdapter`) |
| Budgets, status handling and threshold freeze before outer scoring | F/experiment.py:91–140; F/design.py:6–38 |
| Pooled OOF, support-matched threshold comparison, conditional bootstrap | F/results_report.py:14–98 |
| Threshold tie rule and undefined metrics | F/vendor/compute_classification_metrics.py:12–25 |
| Source-fitted preprocessing and original development membership export | S/experiment_tools/prepare_development_inputs.py:18–39 |
| Continuous medians/scales; categorical encodings; held-out guards | S/public_project/src/dmv_mat_cvd/data/public_preprocessing.py:14–90 |
| Actual written follow-up contract | F/SCIENTIFIC_PROTOCOL.md:5–47; F/protocol_v1.json |

The inspected original and follow-up trainer/metric implementations are byte-identical copies; `SOURCE_INTEGRITY.json` records this and checks the existing public pins. The audit does not inspect checkpoints to establish that any private run actually used a particular clone: that remains the existing independent runtime's responsibility.

## Work completed

- 30 focused invented-data tests passed, zero failures. One test exhaustively covers all 128 masks; another compares 3,054 logical-rule boundary/random combinations with an independent scalar reference.
- Six prespecified synthetic mechanisms × three seeds × four adapted methods = 72 target fits, plus six source fits and 36 source-reference evaluations. No seed or scenario was dropped after outcomes.
- Captured layer-relative drift, gradient magnitudes, exact optimizer membership, source-validation AP changes, initial/selected stopping BCE, class support and full learning curves on invented data.
- Independent NumPy geometry and explicit-kernel permutation-MMD checks agreed with production on the tested fixtures.
- Explicit-source before/after hashes agree. Original scripts, protocols, source pins, historical experiments and reports were left unchanged.

## Interpretation and next action

Real negative transfer would require matched source/adapted predictions on the same outer participants and a clearly defined metric/aggregation, with uncertainty and prior development exposure acknowledged. A Brier improvement with AP deterioration is not a uniform degradation. Parameter drift alone does not prove harmful forgetting: in the synthetic relationship reversal, source performance dropped while target prediction improved substantially.

The minimum next scientific experiment is a separately authorized **epoch-zero checkpoint eligibility comparison**, holding all other target-learning choices fixed. Its complete design is in [FUTURE_EXPERIMENT_PROPOSAL.md](FUTURE_EXPERIMENT_PROPOSAL.md). No real-data operation or new authorization mechanism was implemented here. Existing completed operations must not be rerun or repurposed.

See [selector audit](SHARE_ADAPT_SELECTOR_AUDIT.md), [negative-transfer audit](NEGATIVE_TRANSFER_AUDIT.md), [stopping/calibration audit](STOPPING_CALIBRATION_AUDIT.md), [protocol comparison](CROSS_EXPERIMENT_COMPARABILITY.md), and [synthetic evidence](SYNTHETIC_DIAGNOSTICS.md).
