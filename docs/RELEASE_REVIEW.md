# Private research-repository release review

This directory was built from an **explicit file allowlist**, not a recursive copy of the completed research workspace. The source project remains the authoritative frozen study. This copy contains original generic/synthetic Python modules, a release-only README and link-sanitized manuscript/supplement copies, seven aggregate SVG figures, an aggregate-only JSON result, synthetic benchmark aggregates and Phase-2A documentation. **No license is granted.** Public visibility requires a separate review and express author approval.

## What was checked

- **Scientific text:** the release manuscript and supplement have the same 423 and 301 non-link numeric tokens, respectively, as their untouched source-package counterparts. Only unavailable internal links and explanatory link text were changed. The primary finding remains inconclusive.
- **Source identity:** all 50 selected source and synthetic-test Python files are byte-identical to the completed project. Real-data lock, development, final-evaluation and recovery executors are excluded.
- **Synthetic-only verification:** 142 selected tests passed. A bounded CPU smoke run using invented data completed for source-only, head-only, full and calibrated-logical methods. Its generated output under `results/runs/` is ignored and is **not** a clinical result.
- **Packaging:** Python compilation, package imports and a PEP 517 wheel build succeeded under a Python 3.12 toolchain. The build artifact under ignored `dist/` is not part of the release.
- **Link and format audit:** relative Markdown links resolved; seven SVGs parsed; their only non-fragment image references were embedded `data:image/png` rasters, not external network references. No candidate file exceeded 2 MB. The only reviewed CSVs are three synthetic, per-scenario/per-seed aggregate tables. No participant-level table is included.
- **Path and secret scan:** reviewed files contained no local absolute home path, email address, credential value, token or private evaluation/lock path. Mentions of `private_locks/` and `private_evaluations/` appear only as protective ignore patterns. A text scan is not a substitute for source and data-rights review.
- **Tested environment:** Python 3.12.14; NumPy 2.5.3; pandas 3.0.6; scikit-learn 1.9.1; PyTorch 2.14.0; pytest 9.1.1. The project dependency manifest specifies supported minimum versions; exact cross-platform numerical equality is not promised.

## Intentional exclusions

No raw HAALSI/MHAS/HRS/ELSA/CHARLS data, respondent IDs, release-specific mapping configurations, private lock or assignment, adaptation-draw IDs, participant-level predictions, fitted real-data preprocessors, saved real-data checkpoints, authorization manifests, credentials, virtual environment, generated smoke outputs, or third-party downloaded PDFs/codebooks were selected. Detailed original cohort audit and test-execution reports remain internal because they can contain local paths or private operational details. Seven safe SVG figures are included; duplicate PNG renderings are omitted. There was no Phase-2A-1 report in the source workspace at this review.

The five Phase-2A documents are planning artifacts. They report **NO-GO for immediate Phase-2 model training** pending independent data acquisition, field-level endpoint reconciliation and event-count/precision checks.

## Author-controlled items before any public release

Approve a code license and exact public file allowlist; confirm all authors agree with the manuscript and its disclosures; complete MHAS product-specific citation metadata and research-product notification status; verify applicable institutional and dataset-use wording; and repeat the privacy/data-rights scan. Private GitHub hosting does **not** authorize storing controlled participant records.
