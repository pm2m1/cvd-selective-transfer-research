# Ranked interventions and one next development experiment

These are AI-authored prospective methodological recommendations, not clinical findings, permission records or modifications to completed protocols. No intervention is known to improve real HAALSI/MHAS prediction from this audit.

## Ranked by plausibility and diagnostic value

| Rank | Intervention | Hypothesis and potential benefit | Cost, failure modes and evidence requirement |
|---|---|---|---|
| 1 | Include pretrained epoch zero in target stopping competition; retain source-only control | Avoid forced post-update degradation on stopping BCE; directly tests a demonstrated design mechanism | Almost no extra compute/labels; stopping BCE may still disagree with AP; new registered development operation, not old-run retry |
| 2 | Reduce target LR from .001 to a prespecified .0001 | Smaller displacement may preserve useful source information with scarce target events | Can underfit genuine conditional shifts; more epochs may then be needed but must not be changed simultaneously in a clean diagnostic. Lower LR variants existed in the first experiment, but that does not settle the new design |
| 3 | Source-anchored L2-SP-style fine-tuning | Penalize deviation from pretrained parameters rather than relying only on decay toward zero | Requires prespecified penalty scaling; can prevent necessary adaptation. The old unexecuted shrinkage candidate averages squared displacement over non-head trainable coordinates with coefficient .01; not automatically the same as any literature setting |
| 4 | Prespecified partial freezing / module-specific LR | Limit large fusion1 updates; test head-only or a restricted fusion2 mask without noisy selection | May miss target-specific view changes. Head-only already exists, so compare on identical folds rather than claiming novelty. Discriminative LR increases search burden |
| 5 | Inner cross-fitted threshold evidence plus stability reporting | Use limited labels more efficiently and reveal sensitivity/F1 instability without same-validation resubstitution | More fits, class support failures, refit-to-calibration score mismatch; no new ranking improvement from changing only a threshold. Needs separate prespecified evaluation and label accounting |

Source anchoring is established prior art; the original paper recommends an explicit penalty toward pretrained weights, not an invention of this project. Its evidence is in convolutional transfer, not clinical survey validation: [Li, Grandvalet and Davoine, 2018](https://proceedings.mlr.press/v80/li18a.html). Deployment of an anchor here would require its own study.

Lower priority alternatives:

- **Source-only fallback/gating:** a prespecified training-side loss gate is more interpretable than choosing source-only after seeing outer scores. No outer-label gate is permitted; target utility is not guaranteed by source retention.
- **Residual/low-rank adapters:** plausible parameter constraints, but introduce a new architecture and initialization. They need independent benchmarking, parameter-matched controls and new code validation; not a justified immediate remedy for an unproven bug.
- **Smaller networks:** compact is already tested as a separate source-trained architecture. Keep an architecture-matched zero-adaptation reference; improvement may arise before target adaptation.
- **Weighted BCE/focal:** not active causes in the four current methods. With natural sparse labels they may change gradient balance; with enriched25/75 draws an arbitrary population-imbalance weight can double-correct sampling. Estimate weights from fitting labels only, retain calibration evaluation, and never impute absent positive support. These alter probability targets and may hurt Brier.
- **Fixed or source-validated epochs:** can avoid noisy event-poor STOP selection, but consume a different model-selection contract. Do not use the current outer results to choose the epoch.
- **Platt / prior correction / isotonic:** see STOPPING_CALIBRATION_AUDIT.md for support requirements and overfitting risks. Probability or decision calibration is not evidence of improved ranking or clinically valid risk.

All alternatives require a new prespecified development protocol and applicable independent authorization. Additional raw data are not inherently required for the first four diagnostics if the existing authorized retained bundle is adequate; genuinely independent generalization does require unused eligible participants or a new external cohort. No old locked MHAS test is a new test.

## Exactly one recommended next experiment

### Source-retention checkpoint eligibility experiment (proposal v1; inactive)

**Question:** Does excluding the pretrained source state from target checkpoint selection explain an avoidable part of adaptation loss, when every other learning choice is held fixed?

**Competing hypotheses**

- H_retention: target updates sometimes worsen inner STOP BCE immediately; retaining epoch zero reduces such harmful selections and improves held-out development AP.
- H_metric: the chosen STOP-BCE improvements do not track AP, so an epoch-zero option may improve selected BCE without improving held-out ranking.
- H_null: epoch zero rarely wins or held-out differences remain inconclusive; source-retention eligibility does not explain the observed development pattern.

**Controls/conditions:** (1) fixed original source-only reference; (2) unchanged original full adaptation (`matched_control`); (3) identical full adaptation with **epoch zero eligible**. No new architecture, LR, loss, penalty, patience or selector threshold is changed. This isolates one factor. Logical/compact/threshold grids are not added to this experiment.

**Population and roles:** only the already authorized development adaptation pool, using the unchanged three outer folds, three seeds and five budget fractions, source train/validation and source-fitted preprocessing. Preserve old171 validation as previously examined data; do not score or tune on the original frozen test. Use identical random prefix and fit/stop/calibration assignments across conditions. Retain every configured unsupported condition; no enrichment, favorable redraw or event-count-based early termination. Source-only is evaluated once per outer fold and paired with each target condition, not retrained per budget.

**One change:** at target initialization, compute unweighted STOP BCE, initialize best state/loss to the actual source state/loss and best_epoch=0; use the same min-delta1e-5 and patience thereafter. This is a new versioned candidate contract, not a correction to historical results. If epoch zero wins, selected model is exactly the source clone. All other optimizer steps, maximum epochs and learning rates remain unchanged. The isolated synthetic counterexample in audit_core.py proves the comparison semantics; no real execution adapter is activated here.

**Primary contrast/metric:** same-participant outer-fold AP difference, epoch-zero-eligible minus unchanged full adaptation, with source-only paired contrasts reported as diagnostic controls. Report all folds, per-repeat pooled OOF AP and within-fold differences so fold score offsets are visible. Register the averaging and uncertainty code before execution; do not choose whichever aggregation favors a conclusion. AP must be explicitly unavailable in zero-positive outer folds, with coverage reported; no data-driven replacement fold.

**Secondary measurements:** AUROC, Brier, source-validation AP change, initial/best STOP BCE, selected epoch (including0), fit/stop event support, per-layer relative L2 drift, gradient norms, fixed-.50 confusion matrices, and training-side calibrated operating-point coverage. Calibration uses the same existing inner rule; no threshold retuning on outer outcomes. Store source fingerprints and optimizer memberships.

**Uncertainty:** participant-cluster paired resampling shared across repeats is a conditional-on-fitted-model description, not a retraining uncertainty estimate or external confirmation. Show per-repeat direction and fold support. Participant reuse and prior architecture/design exposure remain explicit; don't treat nine outer fits as nine independent trials. If using a pooled OOF AP interval, label it as a different summary from mean within-fold AP, not an interval for that latter estimand. A registered retraining bootstrap could address additional uncertainty but is not necessary to answer the engineering question and increases cost substantially.

**Acceptance criteria before interpreting any result:** exact source/data/configuration/runtime bindings; identical roles and budgets; no outer-label influence; bitwise source equality when epoch0 selected; no shared-input mutation; no overwrite/retry of prior operations; every registered condition accounted for. These are correctness criteria, not scientific success.

**Interpretation criteria:** the mechanism is supported only if epoch zero is selected under the documented loss comparison and corresponding source/adapted paired predictions show the hypothesized direction. Positive AP differences alone are exploratory; report their full uncertainty and Brier trade-off. A gain claim requires evidence robust to the prespecified aggregation and participant reuse, not an arbitrarily favorable seed. If AP uncertainty includes zero or signs vary materially, label the experiment inconclusive. No minimum clinically useful AP gain is established by current evidence; do not invent one. Even a favorable result authorizes neither a clinical claim nor a new locked-test evaluation.

**Data/permission prerequisites:** fresh independent authorization for a distinct development operation, approved retained bundle and preprocessing provenance, exact new public protocol/adapter hashes, new private output/authorization/attempt destinations, private locally reviewed reports, no AI access to participant artifacts. No new respondent derivation, held-out access or provider permission is assumed. If the actual permission scope does not cover this operation, it remains blocked. Existing successful and failed attempts stay byte-for-byte unchanged.

**Generalization requirement:** any method finalized after this experiment still needs genuinely unused, eligible and nonoverlapping participants, frozen preprocessing/architecture/hyperparameters/numerical threshold and a separately authorized one-shot evaluation. Current status remains INDEPENDENT_TEST_NOT_AVAILABLE from the public follow-up contract.
