# HRS → ELSA training fast-track — public engineering V1

**Synthetic training/evaluation is implemented. Real HRS→ELSA modeling remains BLOCKED.** The completed private status diagnostic has not been adopted as a resolution; no new valid cohort dataset or accepted count/precision evidence is presumed.

## One-command public demonstration

From repository root, using the existing environment and a new unused destination:

```sh
.venv/bin/python -B results/hrs_elsa_training_fasttrack_20261106/scripts/run_experiment.py --synthetic-demo --output /tmp/DMV_MAT_HRS_ELSA_SYNTHETIC_DEMO_NEW --device cpu
```

This generates invented longitudinal populations, removes invented prior/unknown-follow-up cases, freezes outcome-blind memberships, serializes/reloads separate development/test inputs, fits source preprocessing, trains seven methods, calibrates on a dedicated role, selects only on development data, freezes checkpoints/configuration and evaluates the separate invented test. It prints a synthetic-only acknowledgment. A used destination is refused; choose a new one rather than deleting evidence.

From a clean extracted ZIP, use `python3 -B scripts/run_experiment.py --synthetic-demo --output "/ABSOLUTE/NEW/SYNTHETIC_OUTPUT" --device cpu` with the documented dependencies. No external repository or private file is required.

## Implemented methods

Source-only L2 logistic, elastic-net logistic-loss SGD, histogram gradient boosting, source-only five-view MLP, head-only adaptation, full fine-tuning and calibrated-logical selective adaptation. The original public network, freezing helpers and selector mathematics are vendored unchanged. The new eight-role preprocessing produces18 model columns and8,017 neural parameters, rather than claiming the old8,033-parameter study was rerun.

The original HAALSI/MHAS checkpoints, AP/AUROC results and examined test are never loaded. No old participant assignments, HRS/ELSA clinical sources or protected outputs were accessed by this public task.

## Scientific status and minimum path

1. Independently review the **already completed** private status report; do not rerun it.
2. Establish a defensible source interpretation/correction or prospective amendment. No semantic fix is adopted here and no corrected count controller is invented.
3. Execute a fresh justified count release with fresh independent authority, then establish actual HRS/ELSA event, predictor, chronology, split and precision support.
4. Independently derive/validate canonical inputs under the adopted contract. No speculative raw-cohort extractor is supplied while those rules are unresolved.
5. Use separate metadata preflight, interactive development authorization and frozen held-out evaluation authorization in `INDEPENDENT_LOCAL_RUNBOOK.md`.

All real readiness-template gates are false. A record of an independently established scientific fact is not software-issued approval; toggling booleans or strings cannot establish legal scope or evidence. The current endpoint remains source-specific survey-report sensitivity, not strict harmonized clinical incidence. Neither a public software PASS nor favorable synthetic AP can make Phase2B GO.

## Files to read

- `CURRENT_BLOCKERS_AND_DECISIONS.md`, `ELSA_SCIENTIFIC_RESOLUTION.md`, `COUNT_CORRECTION_OR_AMENDMENT.md` — reused evidence and precise private-dependent blocker.
- `COUNT_FEASIBILITY_ACCEPTANCE.md` — prospective event/precision acceptance, not an empirical verdict.
- `OFFICIAL_VARIABLE_EVIDENCE.md`, `FEATURE_HARMONIZATION_MATRIX.csv`, `HRS_ELSA_FEATURE_CONTRACT.md` — exact roles and partial real-data readiness.
- `TRAINING_ARCHITECTURE.md`, `TRAINING_PROTOCOL.md`, `REAL_DATA_INPUT_CONTRACT.md` — runnable model, data, split, threshold and uncertainty design.
- `INDEPENDENT_LOCAL_RUNBOOK.md` — exact supported commands and separately authorized stages.
- `synthetic_results/` — actually executed invented-data aggregate results only.
- `VALIDATION_REPORT.md`, `PRESERVATION_AUDIT.md`, `RELEASE_MANIFEST.json` — actual checks, limits and source integrity.

Production dependency versions used by verification are in `requirements.txt`. Optional tests additionally require `requirements-test.txt`. Keep environments outside the fingerprinted tool tree. CPU execution is verified; MPS is explicitly requested only when available, with no silent backend substitution. Clinical results and all protected input/output artifacts must stay outside AI/indexer access and pending disclosure review.
