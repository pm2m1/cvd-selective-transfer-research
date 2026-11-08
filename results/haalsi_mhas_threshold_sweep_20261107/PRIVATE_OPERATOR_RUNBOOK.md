# Independent local execution — retained frozen predictions only

Codex has not executed these commands on private inputs. Use the genuinely independent authorized Terminal/environment, outside AI tools/indexers. Do not alter environment markers to defeat the original guard. Do not paste private reports, paths, hashes, IDs, predictions or errors into AI. Old inference and0.50-metrics authorizations remain consumed and cannot authorize this supplement.

## 1. Install this separate public source release

Transfer/extract the public ZIP into a new public staging directory. From its root:

```sh
python3 -B verify_release.py
python3 -B verify_release.py --install-to "$HOME/ResearchPrivate/dmvmat_threshold_sweep_20261107_tools"
```

The parent must exist; destination must be unused. The installer copies only manifest-enumerated public files and refuses overwrite. Do not merge into the old metrics/training tools or copy the full repository. Use the existing compatible NumPy/scikit-learn/Matplotlib environment; versions tested are pinned in requirements.txt. Keep any environment outside the fingerprinted source tree. No dependency download occurs automatically.

## 2. Reuse recorded descriptors, without opening scores during preparation

Independently establish permission to read the prior calculation's protected configuration/provenance/completion metadata and create a fresh private preparation configuration. This is not established by the user's general instruction or by filesystem ownership. No new source array is needed.

Create a new private run directory, then prepare from the **completed original0.50 calculation's provenance**:

```sh
mkdir -m 700 "$HOME/ResearchPrivate/dmvmat_threshold_sweep_20261107_run"
python3 -B threshold_sweep.py --prepare-from-metrics-provenance "$HOME/ResearchPrivate/dmvmat_metrics_20261104/output/classification_metrics_v2/provenance.private.json" --new-config "$HOME/ResearchPrivate/dmvmat_threshold_sweep_20261107_run/thresholds.reviewed.json"
```

Run from the new tools directory. The provenance filename is established by the public original writer; its parent is the verified report location supplied by the researcher. Codex did not check that file's existence. The preparer verifies its script identity/no-fitting/no-inference flags and the same directory's successful consumed `completion.private.json`. It extracts **the exact recorded configuration** by descriptor, preserves model/draw/checkpoint maps, label/ID/array keys, and writes an exclusive0600 unresolved new configuration. It does not open prediction/label/ID arrays, rerun0.50 metrics, produce an authorization or replace an old file.

If that provenance is unavailable, use the actual independently identified original reviewed configuration, **not a reconstructed template or guessed payload path**:

```sh
python3 -B threshold_sweep.py --prepare-from-metrics-config "/ABSOLUTE/RECORDED/ORIGINAL_METRICS.reviewed.json" --new-config "/ABSOLUTE/NEW_PRIVATE_RUN/thresholds.reviewed.json"
```

Do not use both preparation modes or overwrite an existing destination. An unexplained script/version/hash mismatch requires independent provenance resolution, not edits to frozen expected hashes. Relative private payload paths without documented absolute locations are rejected; no folder search or key guessing occurs. The bundled public metric-reference file may replace its old location only because its exact registered bytes/hash match.

## 3. Establish the new statistics-only scope

Independently establish provider/institutional permission and actual isolation for reading retained test probabilities, labels and ordered IDs; frozen metadata; any authentic original validation if recorded; reconciliation; the ten descriptive cutoffs; and protected reports/figures. Supplementary data access and external disclosure rights are distinct. No scope permits retraining, inference, source dataset reads or clinical deployment.

Only after those facts genuinely exist, edit the new private JSON locally to record:

```json
"source_use_review": "INDEPENDENTLY_ESTABLISHED_FOR_THIS_NEW_THRESHOLD_SWEEP",
"reviewed_scope": [
  "READ_RECORDED_METRICS_CONFIGURATION_AND_COMPLETION_METADATA",
  "READ_RETAINED_FROZEN_TEST_PROBABILITIES_LABELS_AND_ORDERED_IDS",
  "READ_FROZEN_REGISTRATION_MANIFEST_AND_REFERENCE_BINDINGS",
  "RECONCILE_FROZEN_AP_AUROC_BRIER_BEFORE_REPORTING",
  "DESCRIBE_FIXED_TEST_THRESHOLDS_WITHOUT_TEST_OPTIMIZATION",
  "READ_AUTHENTIC_ORIGINAL_VALIDATION_IF_RECORDED",
  "WRITE_NEW_PRIVATE_SUPPLEMENTARY_AGGREGATES_AND_FIGURES"
]
```

These values record independently established scope; they do not create it. Preserve the fixed grid, prohibitions and source metadata hashes. Leave `original_validation: null` unless genuine retained original validation evidence has been established. No helper automatically approves a field or answers an authorization prompt.

## 4. Metadata-only preflight

```sh
python3 -B threshold_sweep.py --preflight --config "$HOME/ResearchPrivate/dmvmat_threshold_sweep_20261107_run/thresholds.reviewed.json"
```

Supported success: `PASS ISSUE=METADATA_ONLY_NO_SCORE_ARRAYS_READ`. It verifies configuration/source metadata and public references, checks participant-file existence/type/permissions, and verifies relevant metadata hashes. It does **not** open/hash prediction arrays, participant-ID contents or validation arrays. The authorized execution performs their full integrity and content checks after consuming its attempt. An unresolved scope or preflight failure must be resolved independently before authorization, without fabricating evidence.

## 5. New authorization, then one execution

Use a fresh authorization and output outside every prior test/metrics output:

```sh
python3 -B threshold_sweep.py --authorize-local --config "$HOME/ResearchPrivate/dmvmat_threshold_sweep_20261107_run/thresholds.reviewed.json" --authorization "$HOME/ResearchPrivate/dmvmat_threshold_sweep_20261107_run/thresholds.authorization.json" --output "$HOME/ResearchPrivate/dmvmat_threshold_sweep_20261107_run/threshold_comparison_v1"
python3 -B threshold_sweep.py --execute-local --config "$HOME/ResearchPrivate/dmvmat_threshold_sweep_20261107_run/thresholds.reviewed.json" --authorization "$HOME/ResearchPrivate/dmvmat_threshold_sweep_20261107_run/thresholds.authorization.json" --output "$HOME/ResearchPrivate/dmvmat_threshold_sweep_20261107_run/threshold_comparison_v1"
```

Purpose: `retained_frozen_mhas_threshold_sweep_v1_20261107`. The byte-identical original runtime prompts the human personally, binds purpose/config/code/output and consumes the new attempt before score processing. Do not pipe names/phrases, manually construct authorization or reuse an old receipt. Failure/interruption retains private logs/receipt and permanently blocks that output; no automatic retry exists. Authorization success is not calculation success.

The generic successful execution acknowledgment is `REVIEW ISSUE=PRIVATE_OUTPUT_REQUIRES_DISCLOSURE_REVIEW`. Verify the private successful completion and result-integrity manifest locally before treating the threshold calculation as completed. A reconciliation failure means STOP; do not loosen tolerance, rescale/sigmoid probabilities or run inference to obtain a different result.

## 6. Review private outputs

- `SUPERVISOR_THRESHOLD_COMPARISON.private.md`: complete supervisor comparison and limitations.
- `threshold_metrics_per_draw.private.csv`: each model/draw/cutoff's integer counts and requested metrics.
- `threshold_metrics_summary.private.csv`: defined/undefined counts, descriptive mean/sample SD/range, including fractional mean counts labeled as means.
- `threshold_sweep.private.json`: complete full-precision aggregate data, unchanged ranking metrics, validation availability and selection origin.
- `confusion_matrices/<model>/`: separate integer2×2 SVGs for every draw/cutoff, and authentic validation-selected points if established.
- `summary_plots/`: model-specific and cross-method descriptive SVG/PNG plots; no test-optimal cutoff marker.
- `provenance.private.json`, `result_integrity.private.json`, original runtime start/completion/log files: immutable audit evidence.

Do not pool draws or interpret fractional mean counts as a single matrix. Do not choose a clinical/test cutoff from the displayed F1 peak and call it independently validated. Do not publish any cells, plots or private metadata without applicable disclosure review, including small-cell differencing across thresholds. No report file is automatically copied into the B.Tech thesis or GitHub.

## Optional authentic original validation

The public audit found no persisted original validation arrays in the reviewed runners. Default behavior is `ORIGINAL_VALIDATION_OPTIMAL_THRESHOLD_NOT_ESTABLISHED`. Do not rerun inference or use scores from new development models to replace them.

If genuine original retained scores and provenance are independently found, record their explicit descriptors and actual array keys in the **new** configuration's `original_validation` field; do not edit historical metadata:

```json
"original_validation": {
  "rule": "validation_f1_highest_threshold_tie",
  "payload": {"path": "/ABSOLUTE/AUTHENTIC/ORIGINAL_VALIDATION.npz", "sha256": "REVIEWED_ACTUAL_SHA256"},
  "provenance": {"path": "/ABSOLUTE/AUTHENTIC/ORIGINAL_VALIDATION_PROVENANCE.json", "sha256": "REVIEWED_ACTUAL_SHA256"},
  "ids_key": "ACTUAL_RECORDED_IDS_KEY",
  "labels_key": "ACTUAL_RECORDED_LABELS_KEY",
  "model_keys": {"calibrated_logical": "ACTUAL_RECORDED_SCORE_KEY"}
}
```

The provenance must already truthfully establish `role=target_validation`, `origin=retained_original_development_predictions`, payload SHA256, frozen registration SHA256 and a `checkpoints` mapping matching the selected frozen model/draw hashes. Do not fabricate that manifest. The tool verifies171 unique IDs/13 positives, disjointness from test IDs and same checkpoint inventory. Partial authentic availability is explicit per model; unlisted models remain not established. Unselected validation arrays are not read. Declared missing/corrupt/incompatible evidence causes a fail-closed operation, not silent test optimization or a substitute threshold. Add these descriptors before the fresh authorization; existing authorization cannot cover a changed config.

F1 selection uses only unique validation scores plus0/0.50/1, highest threshold on ties, before test probabilities are opened. It does not use the test grid to pick a cutoff. Even this post-hoc validation-only selection does not turn an already examined test into a fresh independent confirmation.
