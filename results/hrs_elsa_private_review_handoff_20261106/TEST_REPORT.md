# Synthetic verification report

## Results actually executed

- New standalone review package: **104 passed, 0 failed**, latest source-tree run0.66s.
- Existing unchanged fast-track canonical-interface subset: **5 passed, 0 failed, 28 deselected**,2.40s. No model fitting or final-test inference occurred in these selected checks.
- Existing fast-track release verification: `PASS ISSUE=PUBLIC_FASTTRACK_RELEASE_VERIFIED`.
- **120/120** preserved public source/documentation files match the before-work ledger.
- Copied authorization/runtime bytes and the two test-only frozen classifier/decoder reference files are exactly unchanged from their original public releases.

This is109 distinct passing checks across the selected suites. Interim reruns are not counted as additional evidence. All private-looking records, authorizations, identifiers and paths created in tests are explicitly invented temporary fixtures. No protected report, real participant file, genuine authorization or clinical configuration was accessed.

## Reproduction

From the new review package root:

```sh
python3 -B verify_public.py
python3 -B -m pytest -q -p no:cacheprovider tests
```

The actual source-tree test invocation used the project virtual environment and `results/hrs_elsa_private_review_handoff_20261106/tests`. Python version: 3.12.14. The review program uses the standard library only; pytest is a synthetic-test dependency, not an operator runtime dependency.

The focused fast-track invocation was:

```sh
.venv/bin/python -B -m pytest -q -p no:cacheprovider results/hrs_elsa_training_fasttrack_20261106/tests -k 'valid_contract_and_outcome_blind_splits or real_config_templates_blocked_before_data or extra_test_array_rejected_before_any_payload_read or read_only_metadata_preflight_never_opens_participant_arrays or evaluation_artifacts_verified_before_test_payload'
```

These checks cover exact canonical roles/membership, endpoint/feature assumptions, unresolved real configuration blocking, rejection of injected test arrays before payload access, metadata-only preflight and registered-artifact verification before test loading. The previous complete seven-model synthetic demonstration is existing evidence and was not repeated or tuned for this metadata-only tool. No new CPU/MPS training claim is made.

## New package coverage

1. All nine waves × four participation categories, multiple direct, missing, fallback, partial, proxy and institutional/death scenarios are compared against the frozen public classifier. Valid code domains remain wave-specific. No inferred actual survey findings.
2. All ten explicit JSON evidence hashes are required. Rehashed but incompatible purposes, configuration/code/mapping/registration bindings, integrity output links and completion states fail. A genuinely mismatched history source cannot be rescued by rehashing its metadata.
3. Completed aggregate schema is exact; missing waves, bad totals, unknown cells/free text, invalid first-conflict evidence, domain errors and duplicate JSON keys fail. Missing versus zero, fallback versus direct, missing Core and unmatched Core remain distinct. A successful diagnostic cannot be reinterpreted as containing accepted invalid/duplicate linkage.
4. Private input/configuration permissions and no-symlink rules are enforced. Outputs require a new private consumed destination. The common private workspace may contain sibling public tools; metadata/output cannot be placed inside those tools or historical outputs. This legitimate sibling-installation case has a regression test.
5. No clinical descriptor is opened. Tests guard against calls to the invented raw-input locations. Production code imports no raw reader, cohort counter, pandas, NumPy, torch, network or telemetry client.
6. Original authorization prompts are delegated to the unchanged runtime; the one-command wrapper never supplies their answers. Mocked cancellation prevents execution. Missing/old authorization, existing output, agent/CI environment and malformed commands fail without private values on stdout/stderr.
7. Failed/interrupted attempts remain consumed. Existing output/install/configuration destinations are refused. Public tool tampering is detected. Synthetic private output modes are restrictive and all prior synthetic metadata bytes are preserved.
8. Every scientific acceptance/adoption/family field defaults to UNRESOLVED. Mechanical verification is separate from approval. All A/B/C paths return NO_EXECUTION; no defect patch is invented. The unadopted C prototype preserves invented prevalent MI/stroke, unknown, proxy/death, repeated-report and re-entry evidence without deriving binary outcomes.

## Evidence limits

The helper binds reviewed metadata snapshots, not cryptographically signed original operations or current raw source bytes. It cannot establish authentic distributor editions, legal permission, reviewer competence, scientific adoption or clinical validity. It cannot reconstruct joint raw status pairs from separate marginals. Those limitations remain explicit in every private worksheet.

No original diagnostic was rerun. No original failed count attempt was accessed or reset by Codex. No actual worksheet, source hash, finding or authorization was created from protected evidence. No new count release or real modeling authorization exists.

## Packaging

The final manifest enumerates the public-only files. The exact release ZIP is extracted into a fresh temporary directory and its independent public verifier and complete invented test suite are run there. An external packaging-verification JSON records the final ZIP SHA256, extracted inventory/hash verification and actual test outcome. The public ZIP includes no generated private worksheet/output or synthetic temporary directories.
