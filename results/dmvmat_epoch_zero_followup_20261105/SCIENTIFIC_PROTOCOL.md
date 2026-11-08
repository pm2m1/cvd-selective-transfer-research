# Controlled epoch-zero checkpoint experiment — protocol v1

AI-authored, researcher-delegated methodological prespecification, dated 5 November 2026. This is **one new development experiment**, not a correction to historical results or an assertion of independent human/institutional approval. The implementation and public protocol are frozen before any new restricted-data execution. This is a repository preregistration, not registration in an external trial registry. No clinical participant artifacts were accessed while preparing it.

## Question and fixed arms

Does including the pretrained state among target checkpoint candidates improve participant-held-out development AP relative to the original full-adaptation checkpoint rule?

- **A:** the unchanged vendored `train_exploratory_candidates.fit`, full adaptation of the original 8,033-parameter model. Its first eligible checkpoint is epoch1, following the first full training epoch, which may contain several optimizer updates. It is not necessarily the state immediately after one minibatch update.
- **B:** same model and source weights, same full adaptation and optimizer/data order. The sole intentional algorithmic change is evaluating the initial state with the same unweighted STOP BCE and making it eligible as epoch0.
- **C:** the same original source model, without target updates, target stopping selection or target calibration. It is an actual zero-target-conditioning-label reference, not a new network.

No logical selector, compact architecture, learning-rate variant, anchor, class weight, new loss or hyperparameter search is added. The root-cause audit established no SHARE/ADAPT implementation bug. Its epoch-zero counterexample motivates a controlled test but does not prove a real-cohort gain.

## Immutable dependencies and populations

Public dependencies are copied byte-for-byte from the verified label-efficiency follow-up and recorded in IMMUTABLE_DEPENDENCIES.json. Original packages, source hashes, completed experiment outputs and markers remain unchanged. The retained-export validation code and original independent-local authorization/runtime are reused unchanged. The new purpose, protocol, code and outputs have independent bindings.

Only the existing approved development export may be read during a separately authorized independent local operation: source training1,744/65 reported events, source validation581/21, target adaptation pool679/49. These are already public contract counts, not newly inspected values. The loader verifies the original completed-workflow/export/preprocessing/assignment-digest chain and exact38-array layout. It reads old target-validation IDs for nonoverlap but **does not decode its outcomes/features**; it does not reopen original assignments, clinical datasets or any frozen-test arrays. Original draw indices are inspected only to validate inherited membership/provenance. No new export is performed.

The existing source-trained preprocessor is reused: five encoded views4/2/3/4/6; ten raw baseline predictor roles; no target/outer normalization or feature selection. Outcome semantics, source/target ascertainment differences and qualified archive provenance remain inherited. This experiment concerns survey-report prediction, not adjudicated clinical incidence.

## Source initialization and learning

Original model only: five Linear→ReLU→LayerNorm view encoders, fusion80→64→32 and head32→1. Train source once using the unchanged helper: seed20261025, maximum30 epochs, LR.001, AdamW decay.0001, batch64, patience5, STOP-BCE min-delta1e-5 on source validation. This reproduces the public source-learning protocol; it does **not** claim to load an original frozen private checkpoint. All A/B/C conditions use the same freshly source-trained initialization in this new operation.

Target A/B: BCE, LR.001, AdamW decay.0001, batch64, maximum20 epochs, patience5, min-delta1e-5. Fresh optimizers, initially empty moment states; all8,033 parameters eligible for target updates. No source momentum transfer. A/B receive cloned independent model objects and reset identical Python/NumPy/Torch seeds. C receives no optimizer. Source training costs are shared and reported separately.

## Exact epoch-zero and patience semantics

The model state is captured before target updates. Unweighted STOP BCE is computed in eval/no_grad using the exact later-epoch loss. State, RNG and train/eval mode are checked before/after evaluation. The network contains LayerNorm but no BatchNorm running statistics or dropout, and this forward path does not consume randomness. Both arms record the initial loss; only B uses it for selection.

A retains `bestloss=inf`, best_epoch0, bad0; its first finite epoch improves on infinity and resets bad. B starts bestloss at actual epoch-zero BCE, stores actual pretrained weights, best_epoch0, bad0. **The initial evaluation does not increment bad.** Each subsequent epoch uses the original strict improvement rule `new_loss < best_loss − 1e-5`; improvement resets bad, otherwise bad increments; stop when bad≥5. Ties retain the incumbent. B can therefore stop one epoch earlier than A during an uninterrupted initial deterioration, or differ more generally because their reference best losses differ. Those runtime differences are consequences of eligibility, not a changed patience value. Forcing equal stopped epochs would change the experiment.

At selection, actual saved weights are restored. When B selects0, its state digest must equal the initial source state exactly. A/B initial optimizer configuration, parameter membership, update-state/RNG hashes and checkpoint-score curves must match over their common execution prefix. After one arm stops, no matching trajectory is claimed for epochs it never executes. A violation fails the operation; it is not hidden by tolerance or retried.

## Source-only equivalence

C and B epoch0 have the same source `state_dict`, features and forward function. Both inference paths call the same eval/no_grad sigmoid helper. Full-trainability flags on B do not affect a no-grad forward. Thus **raw probabilities are required to be exactly identical** when B selects0, and this is checked at runtime. C has zero *target updates*, while B declares8,033 parameters optimizer-eligible even if it later restores0; report drift/selected epoch separately from eligibility and compute cost.

B can use paid training-side calibration labels even when it selects0; C does not. Hence their calibrated decision thresholds need not be equal or available for C. At fixed.50, equal probabilities must yield equal decisions. B's source-state return does not make its target stopping/calibration labels free.

## Splits and paid label budgets

Reuse exactly the copied label-blind split/budget implementation and base protocol:

- Three outer folds; repeat seeds20261105,20261106,20261107.
- Canonical participant IDs sorted and permuted without labels; outer members reserved first.
- Prefix budgets10/25/50/75/100%, rounded down from outer-training size.
- Allocation cycle FIT,FIT,FIT,STOP,CALIBRATION, giving nested membership in each role.
- Target seed `repeat_seed + 1000*fold + budget_n` for both arms.
- Every label used for fitting/stopping/calibration counts; outer evaluation labels and prior development exposure are reported separately.

Registered target conditioning counts are45,113,226,339,452–453. The10% calibration sample has nine observations, so five positives/five negatives cannot both be present. This is retained as unavailable, without enlarging a budget, imputing a class, redrawing or changing the minimum support rule. Fewer than two FIT observations or no STOP observations is recorded insufficient. Single-class FIT/STOP remains allowed under BCE, with actual class support recorded privately. No target label informs acquisition order. The prior architecture/design decisions and historical label-informed pool selection remain exposure; these are retrospective development curves, not newly independent research participants or prospective annotation savings.

## Thresholds and outcome access

Fixed.50 for every arm. For A/B, a separate CALIBRATION subset must contain≥5 observed positives and≥5 negatives. Select maximum calibration F1 over unique scores plus0,.5,1; ties choose the highest threshold. Freeze each numerical threshold before outer outcomes are accessed for scoring. Unsupported calibration returns None with an explicit issue; no fallback. This is training-side threshold selection, **not fitted probability calibration**. The minimum support is not a precision or clinical sensitivity guarantee.

Report calibrated/fixed comparisons on the same supported outer subsets; full fixed metrics remain separate. Single-class outer outcomes yield undefined AP when no positives and undefined AUROC when either class is absent. Undefined precision for no positive predictions remains N/A. No missing outcome is turned into a negative. Changing only the threshold cannot change AP, AUROC or Brier.

## Primary estimand and uncertainty — fixed in advance

The primary family contains **five budget-specific contrasts**, each B−A outer-fold AP. For each budget, compute AP separately within each outer fold, difference on identical participants, average the three folds equally within each repeat, then average the three repeats equally. This is the mean of nine paired differences, not pooled AP. Every one of the nine cells must be evaluated and have defined AP for that budget's primary estimate; otherwise primary status is unavailable. A separately labeled available-fold mean may be shown but cannot replace the primary result. No budget is chosen as a winner after results.

Resample the679 participant indices as clusters1,000 times using seed20261108. Use the **same global participant resample across all repeat/fold/arm predictions**. Within each resample, restrict its multiplicities to each fold and recompute each fold AP difference before the same equal averaging. This is not a bootstrap of nine supposedly independent fits. Zero-positive or empty resampled folds make that replicate undefined; never redraw to obtain a favorable sample. Report defined/undefined repetitions. Require≥950 defined replicates and a defined primary estimate to present an interval; otherwise mark uncertainty insufficient.

Report percentile2.5/97.5 intervals and, to discourage five-budget selection, descriptive.5/99.5 intervals (99% per budget; a Bonferroni-style five-comparison level). These conditional bootstrap intervals are **not confirmatory familywise certification**: they omit retraining/source/model-selection uncertainty, survey clustering, and previous design exposure. Do not declare superiority merely from an increased mean or treat repeats as independent cohorts. Direction consistency, interval support and metric trade-offs must all be discussed; no clinically meaningful AP margin has been established, and none is invented here.

Secondary: paired fold AUROC/Brier; A−C/B−C; per-repeat pooled OOF AP/AUROC/Brier, explicitly a different estimand; B epoch0 selection rate; selected/stopped epochs; layer-relative L2 drift; fixed.50 recall/F1/confusion matrices; supported calibrated operating points; runtime and update counts. Pooled fold-model scores can differ in scale, so compare pooled and within-fold findings without substituting the favorable summary. No automatically assigned scientific winner or improvement flag is generated.

## Execution, privacy and failure

The unchanged independent-local runtime rejects agent/CI/noninteractive operation before reading private configuration or authorization. A new distinct authorization purpose binds all public Python code, the private config digest and a new output destination. New reviewed config additionally binds package manifest, exact protocol and runtime versions. Operator/provider/institutional scope must be confirmed independently; source preparation creates no authorization.

The exclusive output directory records STARTED_CONSUMED **before retained-input processing**. Outputs use private permissions, with native/Python logs redirected privately. Existing outputs prevent a retry. Interruption or failure consumes the operation and preserves partial cells/checkpoints plus a failure receipt; subsequent conditions are NOT_RUN_DUE_TO_CONSUMED_FAILURE, not silently omitted or retried. No automatic resume. Any later recovery requires a separate reasoned protocol/version and authorization; changing the output path alone is not a sanctioned recovery. Earlier runs and authorizations are not touched or reused.

Detailed scores, participant membership/predictions, checkpoint fingerprints, paths, class counts and empirical decisions remain private. The real CLI prints only static execution acknowledgments independent of comparative outcome; applicable disclosure review is required before sharing any empirical result. No restricted data are processed by Codex. Synthetic demos are visibly labeled, reject external config/authorization inputs and use a distinct unused output destination.

**INDEPENDENT_TEST_NOT_AVAILABLE.** A genuinely unused authorized cohort, nonoverlap evidence, harmonized definitions and a frozen model/preprocessor/numerical threshold would be required for separate one-shot evaluation. The original locked MHAS test cannot be reused as a newly independent test. No Phase2B or external-test authorization is created by this package.
