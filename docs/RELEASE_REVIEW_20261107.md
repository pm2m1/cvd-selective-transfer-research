# Public repository update review — 7 November 2026

Base commit: `79bd96c078e517824638a893919153f497978b44`. Work was performed in a separate clean clone on `docs/phase1-threshold-analysis-20261107`. The original research workspace and historical GitHub source artifacts were not edited.

## Public scope

The update adds a nine-page Phase 1 documentation set, a dated Phase 2 status update, portable threshold arithmetic, an invented-data-only example and illustration, synthetic regression tests, public-only CI and explicit tracked-file controls. The original manuscript, supplement, approved aggregate JSON, seven original SVGs, five historical Phase-2A documents and all 50 existing Python source/test files remain byte-identical. Their 75 public-file fingerprints are recorded in [frozen bindings](phase1/frozen-public-bindings.json). These are fingerprints of already tracked public files, not restricted datasets, source lineage or checkpoints.

The [explicit file allowlist](../.public-files.json) contains every tracked file. The [checker](../scripts/check_public_release.py) verifies it, preserved files, relative documentation paths, SVG dependencies, prohibited formats, absolute home paths and recognizable credential patterns. This automated audit does not establish legal permission or disclosure acceptance.

## Threshold integration decision

The original public threshold package was inspected and its 41 synthetic tests passed (6.01 seconds). Its protected-operation loader and execution bindings were deliberately not copied into GitHub. The new portable module preserves the relevant count formulas, undefined-value conventions, full-precision ranking reconciliation and per-draw descriptive aggregation. It has no clinical input-file or inference command and does not replace original provenance/permission checks. Its synthetic fixture has 80 invented observations, not the original study population.

The operator reports private empirical calculation completion and integrity verification. Neither the private files nor their actual results were accessed for this upgrade. No new empirical confusion cells, threshold rates, private figures, source/checkpoint fingerprints, source paths, authorizations or results archives are published. Original validation-optimal threshold remains not established. A distinct independently disclosure-reviewed results PR is required for publication; integrity verification is not disclosure clearance.

## Verification

- Before changes: **142 passed, 0 failed** (4.61 seconds).
- After changes: **180 passed, 0 failed** (4.80 seconds), including 38 new portable-threshold, documentation-evidence and public-boundary checks. Separate parity check: 200 invented float32/float64 cases, 2,800 shared metric values exactly matching the original supplementary calculator.
- Offline PEP 517 wheel build (`uv build --wheel --offline`): passed; ignored wheel not published. Separate-checkout package import: passed.
- Existing four-method CPU invented-cohort smoke: completed; frozen-parameter checks passed. Generated outputs remain ignored.
- Ten-draw, ten-threshold invented demonstration: completed; aggregate JSON and one labeled integer confusion SVG produced. Only that explicitly synthetic SVG is tracked.
- Ruff lint and formatting checks on new code: passed. Historical source is not reformatted.
- Runtime: Python 3.12.14, NumPy 2.5.3, pandas 3.0.6, scikit-learn 1.9.1, PyTorch 2.14.0, pytest 9.1.1, Ruff 0.17.4. Ruff was installed in a separate disposable tools environment; the historical environment was not changed.
- CI is configured for Python 3.10 and 3.12 on CPU. Actual remote outcomes are reported in the PR checks, not inferred from local success. Minimum dependencies remain supported declarations rather than a full environment lock.

Relative links and SVG XML/reference checks are automated; external link uptime and GitHub math/Mermaid rendering are not guaranteed by these checks. Fixed seeds support repeatability within compatible runtimes, not bitwise agreement across all hardware and dependency versions.

## Outstanding author-controlled items

No license is added. Exact MHAS product citations, retrieval metadata and research-product notification status, author/manuscript approval and applicable institutional wording remain unresolved. No later threshold disclosure approval, HRS/ELSA eligibility decision, real incident-event count or real Phase-2 model result is inferred. Private operational status is attributed to the operator. The feature branch is intended for review and is not automatically merged.

## Final public-boundary checks

The reviewed inventory has 100 tracked public files; all 75 frozen bindings match. All 130 relative Markdown targets and eight SVG assets pass the automated checks. A scan of all 76 historical public Git blobs found zero recognizable credential or absolute-home-path matches; the largest blob was 817,841 bytes. No Git history was rewritten. The full staged diff was reviewed against the explicit allowlist and frozen result values; generated synthetic runs, build artifacts and the disposable tools environment are ignored. Public source scans cannot authenticate publisher provenance or establish disclosure rights.
