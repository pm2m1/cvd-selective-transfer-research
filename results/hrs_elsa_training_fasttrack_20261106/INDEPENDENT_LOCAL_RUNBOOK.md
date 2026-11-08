# Shortest valid independent-local path

This runbook separates public demonstration from restricted research operations. **The existing ELSA count attempt remains consumed and the private diagnostic findings are not adopted as a resolution.** No clinical command below has been executed by Codex. Never reset markers, overwrite outputs, reuse authorizations or disguise an AI/CI environment.

## 1. Verify and demonstrate the public package

From the new public package root in an appropriate Python environment:

```sh
python3 -B scripts/verify_release.py
python3 -B scripts/run_experiment.py --synthetic-demo --output "/ABSOLUTE/NEW/PUBLIC_SYNTHETIC_OUTPUT" --device cpu
```

The output directory must be unused. These are invented-data training/evaluation results, not clinical findings. `--device mps` may be used only where the available hardware/runtime supports it; an unavailable backend must stop rather than claim MPS verification. Do not compare demonstration metrics to historical held-out MHAS scores as if they were the same evaluation.

The public ZIP can be transferred to the isolated environment and verified there. Install public files into a **new** tools directory with the supported installer:

```sh
python3 -B scripts/verify_release.py --install-to "/ABSOLUTE/NEW/ISOLATED_PUBLIC_TOOLS"
```

This copies only the enumerated public release. It does not transfer datasets, private configurations, diagnostic outputs or old authorizations. Do not merge it into any frozen installation. Keep the runtime/virtual environment outside the fingerprinted tools tree.

## 2. Review the already-completed private status diagnostic

Under independently applicable permission, a qualified independent reviewer examines the existing protected diagnostic and its integrity metadata **locally**. Do not rerun the status diagnostic. Do not send its cells, matrices, participant context or private verdict to Codex.

The reviewer must distinguish explicit-zero disagreement, unavailable participation, invalid source states, proxy fallback and linkage coverage. Then establish the documented joint-field/source interpretation for the affected waves. Successful artifact creation does not mean a defect is demonstrated or that a precedence/quarantine policy is scientifically adopted.

The review can justify observability-only changes, a demonstrated implementation correction, or a prospective scientific amendment. Changing eligibility, source precedence, unresolved-history handling or exclusions requires the corresponding supported protocol decision. The public error-code split alone cannot make the rejected input acceptable.

**Current blocker:** no private finding is publicly available or adopted, so no semantic correction is assumed in this package. This is a precise missing scientific/source decision, not a request for another general code-review cycle.

## 3. Fresh corrected count operation — conditional and currently unavailable

After a defensible resolution, prepare a separately versioned count release and exact new scientific/configuration/source/runtime bindings. Reuse the existing registered clinical sources in place only if that resolution supports them. Do not re-download, relabel, re-register or rewrite them merely to make checks pass.

There is **no currently justified corrected count controller** to invoke. Consequently this runbook deliberately provides no invented correction command and no command to rerun the frozen `run_counts.py`. The old count authorization/output remains consumed. A future corrected release must document its actual CLI, pass the relevant synthetic regressions, and require fresh independent count scope, interactive authorization and new private destinations.

That operation must produce the chosen-window baseline/exclusion waterfall, separate MI/stroke and composite states, observed nonevents, unknown/disputed/censored outcomes, follow-up support, measurement/predictor availability and independent partition-event support. Review its actual private evidence against `COUNT_FEASIBILITY_ACCEPTANCE.md`; do not substitute synthetic counts or an arbitrary event threshold for a scientific decision.

If valid counts or harmonization do not support the proposed evaluation, retain NO_GO for that modeling design. Investigate a narrower prespecified question or new data rather than weakening labels or reusing an examined test.

## 4. Independently permitted canonical input export

Only after the scientific and feasibility prerequisites pass, establish appropriate permission for the distinct modeling-row derivation/export. The raw-source extractor is not supplied speculatively while eligibility rules remain unresolved. An independently reviewed exporter must implement the adopted source/target contracts and `REAL_DATA_INPUT_CONTRACT.md` exactly.

Export separate development and held-out-test bundles in private storage. The development file contains only source train/stop and target fit/stop/calibration/validation roles. The target test remains physically separate and untouched during development. Verify exact membership, source snapshots, timing, feature definitions, outcome ascertainment and prior-use/nonoverlap; row totals alone are insufficient.

Create a **new** private development configuration from `configs/development.template.json` and a readiness record from `configs/readiness.UNADOPTED.template.json` using their actual schemas. Populate input and readiness descriptors locally. The readiness schema is `hrs-elsa-independent-readiness-v1`; its eight gates all start false, its six evidence descriptors start unresolved, and its `approved_manifest_sha256` must bind the exact development manifest. Record true gates only when the underlying independently reviewed facts exist. Do not edit an old count/registration configuration, copy an old authorization, or mark unresolved science as accepted just to run a preflight. All personal data, output artifacts and config values remain outside AI-accessible workspaces.

## 5. Metadata-only development preflight

From the new isolated tool installation:

```sh
python3 -B scripts/run_experiment.py --preflight --config "/ABSOLUTE/PRIVATE/NEW/development.reviewed.json"
```

This is a read-only readiness step under independently applicable local metadata-review permission. It reads and verifies the new config, readiness/evidence files and manifest, and checks participant-array locations, but it does **not** open or hash the participant-array bundle. Its supported success message is `PASS ISSUE=METADATA_PREFLIGHT_ONLY_ARRAY_BYTES_NOT_VERIFIED`. It does not train or certify the cohort. A successful structural check is not proof that private scientific judgments, access rights or untouched membership are true. The execution performs its required array-integrity and content validation after the single-use attempt is consumed.

If preflight is blocked, preserve the reason and resolve only that dependency. Do not alter a frozen hash, discard an unknown outcome, invent a readiness certificate or reset an attempt. A prepared engineering pipeline does not override the formal scientific NO_GO.

## 6. Separate authorized development training

Once all private evidence and actual permission are established, use the same new config, authorization and unused output for both commands:

```sh
python3 -B scripts/run_experiment.py --authorize-local --config "/ABSOLUTE/PRIVATE/NEW/development.reviewed.json" --authorization "/ABSOLUTE/PRIVATE/NEW/development.authorization.json" --output "/ABSOLUTE/PRIVATE/NEW/development_output"
python3 -B scripts/run_experiment.py --execute-local --config "/ABSOLUTE/PRIVATE/NEW/development.reviewed.json" --authorization "/ABSOLUTE/PRIVATE/NEW/development.authorization.json" --output "/ABSOLUTE/PRIVATE/NEW/development_output"
```

Development purpose is `hrs_elsa_fasttrack_development_v1_20261106`. The original independent runtime prompts the human directly; do not pipe confirmations, fabricate a name, manipulate environment detection or create a receipt manually. Authorization acknowledgment means no training has yet run. Execution creates its consumed marker before protected data processing. An interrupted/failed output remains permanently consumed; no silent retry is permitted.

Review `development.private.json`, `freeze.private.json` and their bound `frozen_models.private.joblib` locally, including AP, AUROC, Brier, calibration, operating-point metrics, positive predictions, checkpoint/restoration behavior and parameter masks. All candidates use the same designated data roles and fixed protocol. The active fitting budget is 100 outcome-blind target-fitting labels **plus** separately reported stopping/calibration/selection label use. Target validation selects models by raw AP; it is not an untouched external confirmation. Positive-slope Platt fitting requires ten calibration observations per class and F1 threshold selection five per class; unsupported estimates remain unavailable. Do not call calibration-sample F1 an unbiased estimate of future performance.

Development does not open or hash the separate target-test bundle. No frozen MHAS test is part of this workflow.

## 7. Lock and independently authorize held-out evaluation

Before opening test outcomes, freeze the selected/declaration-required methods, preprocessing, hyperparameters, numerical calibration/thresholds, outcome definition, test membership/provenance and primary comparison/uncertainty plan. Establish that the target test is genuinely unused and disjoint from every fitting/stopping/calibration/selection role and prior development use.

Create the separate new evaluation configuration using `configs/evaluation.template.json`, bound to the frozen development `artifact` and `freeze` descriptors and the separate target-test `data`/`manifest`. Its readiness record must approve that exact test-manifest SHA256. Its phase is `evaluation` **in the JSON**; no CLI `--phase` flag is supported or needed. It cannot retrain, select a threshold or change a candidate from test outcomes. All seven frozen methods are evaluated; the primary contrast is selective-minus-full raw AP, not whichever comparison looks best on the test.

```sh
python3 -B scripts/run_experiment.py --preflight --config "/ABSOLUTE/PRIVATE/NEW/evaluation.reviewed.json"
python3 -B scripts/run_experiment.py --authorize-local --config "/ABSOLUTE/PRIVATE/NEW/evaluation.reviewed.json" --authorization "/ABSOLUTE/PRIVATE/NEW/evaluation.authorization.json" --output "/ABSOLUTE/PRIVATE/NEW/evaluation_output"
python3 -B scripts/run_experiment.py --execute-local --config "/ABSOLUTE/PRIVATE/NEW/evaluation.reviewed.json" --authorization "/ABSOLUTE/PRIVATE/NEW/evaluation.authorization.json" --output "/ABSOLUTE/PRIVATE/NEW/evaluation_output"
```

Evaluation purpose is `hrs_elsa_fasttrack_locked_evaluation_v1_20261106`, distinct from development and every old operation. Use new private locations and independent authorization. Test results cannot trigger retraining, threshold reselection or another test run. A favorable point estimate or bootstrap interval is not automatically clinical validity or a causal transportability result.

## 8. Preserve and disclose correctly

Keep actual arrays, participant pseudonyms, labels, predictions, checkpoints, manifests, fingerprints, private reports, exact cells and logs inside the controlled environment. Operational success statuses are not scientific acceptance. Share only disclosure-cleared findings under the applicable rules. Do not upload private artifacts to AI or GitHub.

The shortest valid path is therefore: **review the existing private diagnostic → justify/version the scientific correction if any → fresh count and feasibility acceptance → permitted canonical export → development preflight and distinct authorization → development training → frozen registration and distinct held-out evaluation.** The current package completes public engineering and synthetic validation; it does not claim the upstream private decisions or real data already exist.

## Frozen evaluation and operational caution

The evaluation checks exact registered methods, numerical operating points, algorithm hashes and runtime package versions before loading the separate test arrays. Incomplete comparisons do not consume an untouched test for a different unregistered question. Use the same frozen code/runtime environment; a legitimate version migration requires a separately reviewed registration, not editing frozen hashes. Target fraction capacities in the new five-role design must be assessed separately from the old four-role count scenario.

Preflight acknowledgments describe permitted local metadata checks and must not be shared as data-conditioned scientific GO verdicts without applicable clearance. Recorded readiness booleans and their bound documents cannot themselves manufacture the independent judgments they claim.
