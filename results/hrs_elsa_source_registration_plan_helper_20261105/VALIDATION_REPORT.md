# Public validation report — 6 November 2026

## Result

**IMPLEMENTED AND SYNTHETIC-TESTED. ACTUAL PRIVATE PLAN NOT INSPECTED OR UPDATED BY CODEX.**

Command from repository root:

```sh
.venv/bin/python -B -m pytest -q -p no:cacheprovider results/hrs_elsa_source_registration_plan_helper_20261105/tests
```

**56 passed, 0 failed.** All fixtures are newly invented files in temporary directories. No actual Downloads, ResearchPrivate, clinical data, archive bytes, prior assignments, authorization receipts or participant outputs were accessed. No real registration, count, export or model training was invoked. The requested dated output directory is retained; this implementation was completed on 6 November 2026.

## Verified behavior

- The sole JSON data-value change is the first archive path. All other settings, source-review fields, null archive pin, unresolved edition, measurement setting and extra scientific bindings remain unchanged.
- Exact-byte exclusive backup and updated plan use permissions 0600; private run directory required. Same-path repetition is byte-preserving; different non-placeholder paths stop.
- Regular existing V1 archive metadata required; missing, wrong-name, duplicate-download-suffix, directory, relative and symlink paths reject. A unique explicit local pattern works; ambiguous/no matches reject.
- Source review remains unresolved. Changed source/authorization settings and count-tool mismatches reject instead of being repaired silently.
- Existing authorizations, outputs, known markers, unknown siblings, existing backups and stale locks refuse modification. The same checks also protect already configured plans.
- Atomic replacement occurs only after a durable original-byte backup and complete private temporary file. Simulated replace failure leaves the original unchanged. An authorization appearing during preparation prevents commit.
- Duplicate keys and invalid JSON reject. Missing plans/tools reject. Archive bytes and authorization contents are never opened. Readiness is read-only and distinguishes unresolved review, recorded artifact presence and known consumption markers.
- Agent/CI/non-TTY guards remain active. CLI boundary is mocked only for invented tests. Unknown argument/error details never print private paths or unrestricted exception messages.

## Preservation

Only this new public helper directory was written. The original public registration package passed its existing `verify_package.py` integrity check after implementation. Neither installed private tool tree nor any private plan was accessed. No historical experiment, authorization mechanism, protocol binding or frozen result was changed.

## Remaining limits

The one-command operation is documented in README.md and has **not** been run against the actual plan. The complete real archive basename is not in the public record; the operator command supplies a bounded local `5050stata_*_V1.zip` pattern and requires exactly one match rather than inventing a basename. The human can independently use the exact-path option instead.

The helper validates metadata and plan values, not archive identity, legal access, source provenance or complete count-tool fingerprints. It checks only the explicit run directory and default/explicit operation destinations. It cannot search all private storage, prove an authorization valid, or coordinate atomically with the unchanged registrar. Use only while that workflow is idle. Unexpected siblings block instead of being treated as harmless.

The expected post-update readiness remains INCOMPLETE because source-use review and its scope remain unresolved. Actual independent review and a distinct original operator authorization are still prerequisites. No authorization command is automated or executed.

## Public SHA256 values

| File | SHA256 |
|---|---|
| `prepare_plan.py` | `e693224b6277454b346a949088a542be76435073887a3abdb3d400dea903f5f5` |
| `check_readiness.py` | `0a9fa653b23a927c3bf1ae2d577df600abac1ea5a75cd32a246fcb40cd241317` |
| `tests/test_helper.py` | `3ad40b0aa16ba904e1b178d12a963eb9226655e689718f7d4a6690780edfe283` |
| `README.md` | `a3727c268d2cdff7b54d986b08f7d075b17504094bafdbb2f505cc5a33c69807` |
