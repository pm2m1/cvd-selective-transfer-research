# Public synthetic validation — 6 November 2026

**STATUS_ONLY_DIAGNOSTIC_SYNTHETICALLY_VERIFIED_NOT_EXECUTED_ON_CLINICAL_DATA**

## Actual results

Repository-root command:

```sh
.venv/bin/python -B -m pytest -q -p no:cacheprovider results/hrs_elsa_interview_status_diagnostic_20261106/tests
```

**81 passed, 0 failed, 0 skipped** in the last source-tree run (0.90 seconds). Runtime: Python 3.12.14, pandas 3.0.6, NumPy 2.5.3, pytest 9.1.1. All Stata tables, linkage keys, source registrations, authorization fixtures and outputs used in tests were invented temporary artifacts. No actual private configuration, dataset, registration, old failed output/receipt/log or authorization was read, hashed or modified.

## Coverage of requested cases

1. Fully consistent personal, proxy, partial and institutional states: direct pure tests and invented Stata roundtrips.
2. Explicit-zero, Stata-missing and invalid harmonized participation: preserved categories, exact local frozen predicate outcomes, no zero/one filling.
3. Proxy-flag fallback with one/zero/missing participation: separate unresolved ambiguity regardless of matching flag; no personal eligibility inference.
4. Missed wave/re-entry and absent Core record: invented linked Stata coverage and separate missing/unmatched matrices.
5. Invalid, missing, duplicated and similarly shaped linkage keys: no fuzzy matching or duplicate selection for a completed report; private input diagnostics precede consumed failure.
6. Wave-specific proxy coding, W4 versus W3 institutional domain differences and invalid Core values: mapping preserved; incompatible domains retain private evidence then fail.
7. Source bytes tampered, manifest/code identity mismatched or descriptors not exactly registered: blocked before status data read.
8. Missing/new-scope failures and reused/missing/changed purpose/config/code/output authorization: no processing callback. Agent authorization/execution rejects before config reads. Interactive authorization is mocked only with invented fixtures.
9. Existing destination, failure and interruption: permanent consumed receipts, exclusive outputs and no silent retry.
10. No data leakage: exact fixture IDs absent from report; unused health column not decoded/exported; arbitrary scalar and warning text sanitized; successful runtime console is a static acknowledgment. Operational summary bytes are identical for consistent and disagreeing source fixtures.
11. Unchanged eligibility: six extracted decoder functions match their source-segment SHA256s exactly; only normalizers/decoder exist in that module. Diagnostic input dictionaries and decoder decisions remain unchanged, and original source files are read-only. No clinical counting functions are packaged or called.
12. Installation/config preparation: manifest-enumerated public transfer only, no overwrite, changed public bytes rejected, new private config template remains unresolved and 0600. No real authorization is manufactured.

No earlier cohort operation, scientific assessment or historical broad regression suite was rerun.

## Historical preservation and provenance

All **9/9** original public code/protocol/registration-evidence fingerprints in `PRIOR_PUBLIC_BINDINGS.json` match after development. This verifies only those explicit public files; it does not claim inspection of private attempts. The inherited runtime copy is byte-identical to the original public runtime. The full count engine and source reader are not bundled/imported; exact selected decoder source segments plus the frozen public mapping make the distribution self-contained.

Input registration fingerprints preserve qualified local archive/member provenance, not independent publisher authentication or a fabricated edition. The config and runtime use a distinct purpose and new review scope. Old registration/count receipts cannot authorize this diagnostic.

## Public code hashes

| File | SHA256 |
|---|---|
| `run_status_diagnostic.py` | `54d15e1a62a6e41a22f4dfc96738532f2c6bcf9798442d5ce3bb407f0774fb02` |
| `diagnostic_engine.py` | `3308c5d4d411e81c6490c1955942cdbc82ae4ce1f001c77bad54a4432ee46cd5` |
| `status_reader.py` | `34534e4c022d47167a60381f50b514cf9786381a920dca38b00914acd5daae39` |
| `frozen_decoder.py` | `94294b26d7fdcf63fb2188f198b145b83594a9a96c1fc38bcb62b0f4996bf60e` |
| `local_execution.py` | `d1227f629eaaf727c3ca41195c7ab1dccd1da3a15040168752b1f2cbbc3b2e02` |
| `verify_public.py` | `a9b86d307f5b9d1664d36b8fe7c9ec804e018014e46af025d69b6223b40d9802` |
| `DIAGNOSTIC_PROTOCOL.json` | `7fd3c4abecc89280e93f092620c3a82d284d30418b540a2949b53508c3746c74` |
| `references/frozen_mapping.json` | `158822fb918835c34b79d7deae5050bcc9832eaadbfce570da91542372a40c61` |

`RELEASE_MANIFEST.json` fingerprints the whole public distribution except itself. The separate ZIP verification receipt records the exact final ZIP SHA256 and fresh extraction test results without a self-referential archive hash.

## Limitations

Synthetic validation does not identify the actual failed combination, validate real source rights or establish real clinical feasibility. A completed status report can establish recorded combinations; routing/revision/linkage causality may remain unresolved. No eligibility-changing correction or category C amendment is adopted. The first failed count stays consumed permanently. A new status-only operation requires separately established source-use permission, independent interactive authorization and new private output. Any later count operation needs its own justified release, scope, bindings and authorization.
