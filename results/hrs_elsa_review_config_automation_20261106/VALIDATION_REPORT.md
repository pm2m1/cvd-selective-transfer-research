# Validation report — configuration automation

## Actual final source-tree results

**56 synthetic tests passed, 0 failed**, in0.82s, using Python3.12.14 and the existing project virtual environment. No real private configuration, record, authorization, receipt, diagnostic matrix or clinical source was accessed. No actual binding/review/count/training operation ran.

The original review public release remains byte-identical:28/28 files, including its manifest, match the before-work ledger. The120 earlier public bindings in that release's preservation ledger also match. The reference copy in tests is unchanged public source only. The original installed private tool tree was not accessed by Codex and no reinstall occurred.

## Original preflight compatibility: PASS, with the intended permission gate

The synthetic test binds the actual frozen schema, leaving all three declarations unresolved. Its original `offline_scientific_review.py --preflight` returns `NO_EXECUTION`, exit2, as required. The test then separately simulates an explicit human recording the exact original scope/isolation declarations; original preflight returns the same message with exit0. The helper itself never makes that change. No changes to the original tool were needed.

An initial test-harness import-context issue was corrected in the new tests to match ordinary script-directory imports. The frozen program, schema, public contract, guards and scientific logic were preserved.

## Coverage

- Ten valid descriptors through both controlled discovery and explicit paths; exact original-schema integration; original configuration's unchanged public pin/prohibitions/unresolved declarations.
- Every missing evidence file; wrong/swapped/duplicate roles; duplicate JSON keys; missing/extra roles; multiple authorization candidates; actual purpose/config-hash/schema resolution; generic uppercase naming used in public runbooks.
- Incorrect file/directory permissions, owner mismatch, symlinked metadata/parents, outside-root records, non-JSON paths, invalid JSON/SHA256 and wrong public manifest/configuration.
- Modified or partially prepared existing configurations; old historical destinations; existing authorization/output/marker/backup/staging/record/unrelated files; no silent overwrite or cleanup.
- Exact-byte0600 backup, exclusive/fsynced0600 staging, atomic replacement and post-commit binding record; concurrent edits, interrupted staging, failed replacement and interrupted post-replacement recording remain preserved and block retries.
- Read-only checks detect byte-changed evidence and modified bound configuration. Explicit later scope declarations are permitted only as a whole original documented triple; they are never written by the helper.
- Frozen tool bytes/imports remain unchanged; bytecode output is suppressed. CLI and direct documented entrypoints reject agent execution before private access. Terminal output contains static statuses only; source/clinical descriptor paths are never opened.

Synthetic source-location strings refer to nonexistent invented files. Fake historical authorizations are explicitly labeled invented and generated only in temporary directories. They are not genuine permissions and are not packaged as records.

## Reproduce

From this package root, using the existing suitable Python environment:

```sh
python3 -B verify_release.py
python3 -B -m pytest -q -p no:cacheprovider
```

`pytest.ini` selects only the new configuration tests. It excludes the frozen-reference historical tests, so this does not rerun an old diagnostic or model suite. No external dependencies are needed by the operator helper; pytest is needed only for tests. The public source-test copy makes compatibility verification reproducible after clean ZIP extraction.

## Packaging and scientific limits

The release is built from its explicit manifest, extracted into a fresh temporary directory, verified independently and synthetic-tested there. The external packaging-verification JSON records the exact final ZIP SHA256 and extracted test result. Only public code/documentation/templates and invented-test generators are included; no generated private configurations, reports, authorizations or temporary test outputs enter the ZIP.

Metadata hashes verify recorded bytes, not publisher provenance, current clinical source bytes, legal entitlement or scientific compatibility. Real binding success remains unobserved. The next milestone is READY_FOR_INDEPENDENT_LOCAL_METADATA_BINDING. Independent metadata-access permission is required before binding. Actual review scope/isolation, the original interactive authorization, substantive scientific determination and any later count/training prerequisites remain unresolved until genuinely established locally.
