# ELSA interview/participation status-only diagnostic V1

**PUBLIC_IMPLEMENTATION_READY_FOR_SEPARATE_INDEPENDENT_AUTHORIZATION — NOT EXECUTED ON REAL DATA.**

This self-contained package diagnoses registered Harmonized ELSA H/Core Waves 1–9 status combinations. It does not count MI/stroke events, construct cohorts, change eligibility, train models or recover a discarded historical exception. The old failed count remains permanently consumed.

Read `STATUS_CLASSIFICATION_CONTRACT.md`, `SCIENTIFIC_INTERPRETATION_GUIDE.md`, and `INDEPENDENT_LOCAL_EXECUTION.md`. The protocol is AI-authored public engineering, not provider, institutional or independent-human approval.

## Contents

- `diagnostic_engine.py`: pure aggregate status matrices; zero, missing and proxy fallback remain distinct.
- `status_reader.py`: only linkage and response/interview columns, no health/predictor/date columns.
- `frozen_decoder.py`: six exact pure functions extracted from the pinned public count engine. No `analyze`, history, follow-up or model functions exist here.
- `run_status_diagnostic.py`: new-purpose independent-human entry point.
- `local_execution.py`: byte-identical inherited authorization/exclusive-output runtime. No authorization or AI/CI guard is relaxed.
- `verify_public.py`: public-only integrity verification, exclusive installation and creation of a new unresolved config template.
- `references/`: public frozen mapping and provenance fingerprints; no datasets or private registration records.
- `tests/`: invented Stata fixtures only. Tests mock the local boundary solely for those fixtures.

## Public verification

```sh
python3 -B verify_public.py
python3 -B -m pytest -q -p no:cacheprovider tests
```

Verified environment: Python 3.12.14, pandas 3.0.6, NumPy 2.5.3, pytest 9.1.1. Production requirements and optional test requirements are supplied. Other runtime combinations are not claimed verified; actual versions are recorded privately.

## Independent operation

The only protected-data entry point is the **separately authorized** local workflow documented in `INDEPENDENT_LOCAL_EXECUTION.md`. No source/config path is discovered automatically. A new private configuration must name the registered source manifest and the ten exact registered loose Stata descriptors. Its source-use review starts unresolved. Registration/count authorizations are not valid for this purpose.

The tool refuses agent/CI/non-TTY execution before private config/source access. These checks and private permissions do not themselves establish isolation or data-use rights; the operator must independently establish them. Do not run this clinical operation through Codex. Do not send populated configs, private outputs, hashes, paths, small cells or logs to AI services.

Successful console acknowledgment is static: `REVIEW ISSUE=PRIVATE_OUTPUT_REQUIRES_DISCLOSURE_REVIEW`. It does not disclose which combinations occurred. `operational_summary.json` is identical across successful findings and contains no counts or empirical verdict. Detailed reports remain private until applicable disclosure review. Failure summaries may exist inside a consumed failed output; never retry or overwrite it.

The diagnostic preserves the original source-status interpretation. It can establish a recorded zero-versus-response disagreement, unavailable evidence or a decoder fallback. It cannot by itself establish why revisions/routes disagree or justify admitting a participant. Those questions remain scientific/source review decisions.
