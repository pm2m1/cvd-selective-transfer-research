# DMV-MAT label-efficiency follow-up — public package v1

This is a new retrospective development experiment. It does not rerun or modify the completed seven-candidate workflow, original HAALSI/MHAS experiment, assignments, checkpoints or locked test. Codex used public code and invented fixtures only. Actual training/results remain unperformed until a new independently authorized local execution.

## Install only this public package

Use the same independently controlled Python environment used for the completed run (tested public environment: Python 3.12.14 and the versions in `requirements-synthetic.lock.txt`). No automatic dependency downloads or private-file transfer occur. From this extracted public package, in an ordinary independent Terminal:

```sh
python3 -B install_public_followup.py --destination '<NEW_ISOLATED_FOLLOWUP_TOOL_DIRECTORY>'
```

The destination must be new, absolute and outside this source tree and all old fingerprinted tool roots. The installer copies only the public manifest's named files, verifies their bytes, and creates directories 0700/files 0600. It never copies `synthetic_only/`, weights, prediction files or any repository/dataset tree. Existing destinations are refused, not overwritten. Ownership/permissions do not prove physical isolation or licence scope.

## Configure the new retained-export operation locally

Copy `followup_config.template.json` into approved private storage **outside AI-accessible folders** and populate it locally. No private paths, hashes derived from protected artifacts, or configurations should be pasted into Codex.

`protocol` is a `{path, sha256}` descriptor for this installation's unchanged `protocol_v1.json`. Keep `outer_folds=3`, `no_locked_test=true`, `no_prior_validation_outcomes=true`. The separately registered five-fold extension can be chosen *before* executing a new separately authorized operation; do not switch designs after seeing favorable/unfavorable curves.

Supply explicit local `{path, sha256}` descriptors under `inputs` for these existing, immutable artifacts:

- `development_bundle`: completed export `development_bundle.private.npz` (38 arrays).
- `development_manifest`: the matching `development_manifest.private.json`.
- `source_preprocessing`: the matching `source_preprocessing.private.json`.
- `completed_workflow_receipt`: the completed seven-candidate workflow's `workflow.completion.private.json`, not an intermediate export acknowledgment.

Descriptor preparation and all protected-file handling require the independent operator's applicable permission scope. The operator may calculate hashes in that environment; this package does not discover private files or hash them in Codex. It never needs raw datasets, the old private assignment file, old test labels/predictions, a questionnaire, or prior target-model checkpoints. It validates the retained export via the recorded original exporter/assignment/public-source identities and the completed workflow's manifest binding. That reuses the existing verified membership chain, not independent publisher authentication.

The loader decodes source train, source validation and target adaptation pool features/labels; it reads the old target-validation **IDs only** for disjointness, and original draw-index arrays for historical label-cost accounting. It never decodes that old validation cohort's features or outcomes. Whole retained-file hashing still covers their serialized bytes; that is an authorized integrity read, not use in fitting/calibration. Extra test-role arrays or any non-contract bundle key are rejected.

## Fresh human authorization and run

From the new installed tool directory, use two original-contract commands:

```sh
python3 -B learning_curves.py --authorize-local --config '<PRIVATE_FOLLOWUP_CONFIG>' --authorization '<NEW_FOLLOWUP_AUTHORIZATION>' --output '<NEW_PRIVATE_FOLLOWUP_OUTPUT>'
python3 -B learning_curves.py --execute-local --config '<PRIVATE_FOLLOWUP_CONFIG>' --authorization '<NEW_FOLLOWUP_AUTHORIZATION>' --output '<NEW_PRIVATE_FOLLOWUP_OUTPUT>'
```

The original, byte-identical local authorization/runtime helper rejects AI/CI/noninteractive operation, requires the human's original name/scope confirmation dialogue, binds configuration/code/output and consumes an exclusive new output attempt. Do not pipe confirmations, clear agent flags, reuse old authorization or reset an output marker. Output parents must be approved/private (0700); outputs must be outside the public tool root. Any failure/interruption remains consumed with no automatic resume. This is a separate new purpose and operation; old completed artifacts are inputs only and remain unchanged.

Scope must cover retained participant data, new source/target fitting, private predictions/memberships/checkpoints, and aggregate reporting. A prior export authorization is not this follow-up authorization. No results are uploaded, displayed publicly or sent back to AI automatically. Native/Python logs stay in the new private output. A completion acknowledgment means artifact creation, not scientific acceptance.

## What runs

See `SCIENTIFIC_PROTOCOL.md`. Primary design: 3 folds × 3 seeds × 5 budgets × 4 methods = **180 target fits**, plus nine source-only evaluations and two cached source pretraining runs. All registered conditions are attempted even when class support or metrics are insufficient; no favorable split is redrawn. Five folds mean 300 target fits and 15 source-only evaluations, with separate authorization. No real completion-time guarantee follows from the synthetic checks.

The four methods and hyperparameters are fixed. Existing class-geometry/SHARE/ADAPT logic is copied unchanged. Early stopping uses a disjoint inner stopping subset; F1 thresholds use a different calibration subset. All their labels are charged to the budget. Outer labels never fit models, class weights, normalization, stopping, selector geometry or thresholds.

## Private results

- `followup_results.private.json`: label accounting/history, per-split AP/AUROC/Brier/confusion/decision metrics, paired differences, calibration coverage, parameter counts, epoch traces and measured costs; conditional participant-bootstrap AP intervals.
- `label_budget_comparison.private.md`: learning-curve, threshold-on-identical-supported-participants and compute tables.
- `label_learning_curves.private.svg/.png`: private development plots; AP shading is participant-cluster bootstrap uncertainty conditional on the fitted models.
- `outer_predictions.private.json`, `fold_memberships.private.json`, `checkpoints/`: protected participant-level/model artifacts. Do not upload these.
- `followup_execution.private.json`, original-runtime start/completion and private logs: provenance and consumed-attempt evidence.

A shared participant appears once per repeat in outer predictions. Three repeats do not create three independent cohorts. Validation-selected threshold metrics are evaluated on distinct outer participants for each fitted model, but this is still retrospective development after prior architecture selection. Do not compare these CV scores to frozen-test scores as if they shared an evaluation population. AP is average precision, not every alternative trapezoidal PR-AUC definition. Threshold changes do not change AP/AUROC/Brier for unchanged scores.

Any aggregate released outside the private environment requires the applicable disclosure review; all detailed records remain local. No new clinical or independent-generalization claim is generated.

## Future independent test — currently unavailable

`INDEPENDENT_TEST_NOT_AVAILABLE`: no genuinely unused eligible cohort was established or accessed in this task. Existing MHAS locked-test participants and the already examined validation/pool are not new tests. `register_independent.py` and `evaluate_independent.py` are an inactive future interface, not evidence that a cohort exists.

They need independently reviewed/harmonized *new* participant features, a complete custodian-produced prior-person token registry and a model/threshold finalized before external outcomes. The private registry must cover all previous partitions/access, including the original locked test, without this software reading old test materials. Candidate and prior tokens must use the same recorded tokenization context/private salt and resolved cross-dataset person identities. Namespaced IDs alone are insufficient. Tokens are protected pseudonyms, not public anonymous data.

Fill the empty `independent_proposal.template.json` and registration/evaluation templates locally only when actual new evidence exists. Required scientific contract: population, eligibility/exclusions, outcome definition, baseline timing/horizon; feature provenance linked to frozen source preprocessing; frozen architecture/checkpoint/hyperparameters; numerical threshold with training-side calibration provenance. Availability/no-prior-use/linkage fields are operator assertions requiring real supporting evidence, not automatically generated approvals. The feature NPZ must contain only `ids` and five encoded views (no labels); outcomes are a separate `ids,y` NPZ inaccessible to registration. A final full-development model/calibration fit and its provenance are a separate future decision—not automatically selected from a favorable CV fold here.

Only for that genuinely new cohort, with fresh purposes/authorizations and unused output destinations:

```sh
python3 -B register_independent.py --authorize-local --config '<PRIVATE_REGISTRATION_CONFIG>' --authorization '<NEW_REGISTRATION_AUTHORIZATION>' --output '<NEW_PRIVATE_REGISTRATION_OUTPUT>'
python3 -B register_independent.py --execute-local --config '<PRIVATE_REGISTRATION_CONFIG>' --authorization '<NEW_REGISTRATION_AUTHORIZATION>' --output '<NEW_PRIVATE_REGISTRATION_OUTPUT>'
python3 -B evaluate_independent.py --authorize-local --config '<PRIVATE_EVALUATION_CONFIG>' --authorization '<NEW_EVALUATION_AUTHORIZATION>' --output '<NEW_PRIVATE_EVALUATION_OUTPUT>'
python3 -B evaluate_independent.py --execute-local --config '<PRIVATE_EVALUATION_CONFIG>' --authorization '<NEW_EVALUATION_AUTHORIZATION>' --output '<NEW_PRIVATE_EVALUATION_OUTPUT>'
```

Registration has no outcomes descriptor, opens no outcome file, checks strict checkpoint architecture/finite weights with `weights_only=True`, and freezes package/proposal/feature/model/calibration/protocol fingerprints. Evaluation verifies registration completion and membership, loads weights with `weights_only=True`, predicts with the frozen model/threshold *before* opening outcomes, and never trains or retunes. An exclusive permanent marker under that new registration prevents evaluating it again with a new output path, even after failure. It never alters original study markers. Duplicate registration copies/re-registering an already exposed cohort are forbidden by the no-prior-use contract; this software cannot independently certify a dishonest/incomplete registry or provider approval. Primary AP participant-bootstrap procedure is fixed before outcomes; secondary decision/ranking metrics are descriptive. No clinical success is inferred from counts.

## Synthetic verification only

```sh
python3 -B -m unittest discover -s tests -q
python3 -B learning_curves.py --synthetic-demo --output '<NEW_SYNTHETIC_ONLY_OUTPUT>'
```

Demo mode accepts no external config/authorization, creates invented participants and uses one repeat, two-epoch caps and reduced 9/19 selector repetitions. Its results are not clinical scores. Tests use temporary invented artifacts and mock/fixture provenance; no genuine permission or private data is a fixture. See `VALIDATION_REPORT.md` for actual test totals.
