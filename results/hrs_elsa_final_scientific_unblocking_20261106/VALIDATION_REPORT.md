# Validation report — final scientific unblocking

All execution below used public source files and invented fixtures only. No real count, protected diagnostic or clinical training was executed. No private findings were inspected. This is engineering verification, not scientific acceptance.

## Actual test results

| Check | Result |
|---|---|
| New focused public-gate/evidence/package tests | 27 passed, 0 failed (final run 0.03 s) |
| Frozen interview-conflict regression suite | 166 passed, 0 failed (0.23 s) |
| Existing fast-track focused integration tests | 28 passed, 0 failed, 1 MPS skip, 4 training/rerun tests deliberately deselected (4.28 s) |
| Total distinct checks in these suites | **221 passed, 0 failed, 1 skipped** |
| Complete unchanged synthetic CLI demonstration | **PASS**, one invocation in this review, RC=0, all seven methods in development and separate synthetic evaluation |
| Existing fast-track release verifier | PASS ISSUE=PUBLIC_FASTTRACK_RELEASE_VERIFIED |
| Baseline public preservation ledger | 67/67 byte-identical after work |
| Legacy conflict frozen reference ledger | 14/14 byte-identical |

The four deselections avoid additional optimization/demo cycles: synthetic_end_to_end_and_deterministic_rerun; test_overlap_and_artifact_mismatch_block; freezing_and_optimizer_membership; epoch_zero_restoration_with_tiny_update. Their historical results are not counted as new passes. The full CLI demonstration ran once instead; no tuning or repeated attempt was used. MPS hardware was unavailable; no MPS execution is claimed.

## Reproducible commands (source checkout)

```sh
.venv/bin/python -B -m pytest -q -p no:cacheprovider results/hrs_elsa_final_scientific_unblocking_20261106/tests
.venv/bin/python -B -m pytest -q -p no:cacheprovider results/hrs_elsa_interview_conflict_investigation_20261106/tests
.venv/bin/python -B -m pytest -q -p no:cacheprovider results/hrs_elsa_training_fasttrack_20261106/tests -k 'not synthetic_end_to_end_and_deterministic_rerun and not test_overlap_and_artifact_mismatch_block and not freezing_and_optimizer_membership and not epoch_zero_restoration_with_tiny_update'
.venv/bin/python -B results/hrs_elsa_training_fasttrack_20261106/scripts/verify_release.py
```

The actual demonstration command was:

```sh
.venv/bin/python -B results/hrs_elsa_training_fasttrack_20261106/scripts/run_experiment.py --synthetic-demo --output results/hrs_elsa_final_scientific_unblocking_20261106_SYNTHETIC_CHECK --device cpu
```

That output now exists; it must not be reused. Runtime: PyTorch 2.14.0, NumPy 2.5.3, scikit-learn 1.9.1, joblib 1.6.0. Complete wall-clock timing was not instrumented; none is invented. Source-only logistic/regularized/boosting/DMV-MAT and head/full/selective adaptation all completed. Development did not access its separate synthetic test; test thresholds and model selection were unchanged. The included aggregate JSON is expressly SYNTHETIC_ONLY and cannot establish clinical performance, event support or generalization.

## What was checked

- Frozen global conflict behavior for personal states with zero, missing and Stata missing participation; proxy fallback with missing/nonresponse outcomes; consistent personal states; exact wave domains; absent W9 MI confirmation.
- Exact public dictionary evidence copying and citations; sensitivity-only HRS MI designation; unchanged unadopted readiness template; no active new clinical counter.
- Canonical feature order, role/membership/unknown/future-feature rejection, source-only preprocessing, fixed-role assignments, threshold support and reporting, agent guards before config access, consumed-output/old-authorization rejection, protected-error sanitization, artifact verification before test payload reads, metadata-only preflight and unchanged model/runtime bytes in the retained fast-track tests.
- Package verifier rejects changed hashes, path traversal and unrelated unregistered files. It reads only its own public directory. It neither discovers clinical files nor replaces independent scientific review.

## Scientific verification limit

Public evidence supports the broad participation invariant but not a universal Core/harmonized/proxy precedence repair. No actual private combination or eligibility-changing defect is established. No count correction, amendment adoption, canonical clinical export or real training is claimed. The mapping is documentary/conditional; source authenticity, baseline timing and endpoint/event/precision sufficiency require independent evidence. Public result: **REQUIRES_PRIVATE_SCIENTIFIC_DECISION**.

## Package verification

The final public inventory and SHA256 values are in RELEASE_MANIFEST.json. The public ZIP is built from that explicit inventory, extracted into a new temporary directory, and verified using the extracted verifier. No participant arrays, predictions, IDs, checkpoints, clinical files, receipts, authorization files, private configurations or protected results enter the ZIP. The extracted review package is independently verifiable; its source-checkout regression tests deliberately reuse the named original public implementations rather than duplicating/replacing them. Packaging verification is recorded separately beside the ZIP.
