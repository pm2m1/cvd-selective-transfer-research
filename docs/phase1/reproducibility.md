# Reproducibility: what this release can establish

[Phase 1 index](overview.md) · [Original boundary and recovery disclosure](../PHASE1_METHOD_AND_REPRODUCIBILITY.md)

## Public environment and tests

Python 3.10+ is declared; CI exercises Python 3.10 and 3.12 on CPU. Use a fresh environment:

```sh
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e . -r requirements-dev.txt
python -m pytest -q
python -m ruff check scripts examples/threshold_demo.py src/dmv_mat_cvd/thresholds.py tests/test_thresholds.py tests/test_public_checks.py tests/test_public_results.py tests/test_selector_json.py
python scripts/check_public_release.py
```

Minimum dependency versions are in [pyproject.toml](../../pyproject.toml). The checked runtime versions and actual validation results are in [the update review](../RELEASE_REVIEW_20261107.md). A minimum-version declaration is not a lockfile or proof of every dependency combination. CPU/GPU kernels, BLAS, PyTorch and platform versions can change floating-point outputs even with fixed seeds; bitwise cross-platform equality is not promised. XGBoost is optional and unnecessary for these smoke tests.

## Synthetic demonstrations

From the repository root, with the package installed:

```sh
python -m dmv_mat_cvd.experiment --config configs/synthetic_smoke.json --source-n 320 --target-n 160 --device cpu
python examples/threshold_demo.py --output results/runs/threshold-demo-UNUSED
```

The first exercises source-only, head-only, full and logical transfer using invented cohorts. The second generates invented probabilities internally, computes all ten cutoffs over ten score vectors, and writes an aggregate synthetic JSON and one labeled integer confusion SVG. It accepts no data-file arguments. Output must be new; choose a fresh name if already present. Do not remove historical or consumed real outputs to reuse destinations.

The threshold module ports the formula/aggregation subset of the previously tested standalone supplement, without its controlled-data loader or checkpoint/source bindings. Focused tests cover orientation, equality at threshold, undefined precision, formulas, reconciliation rejection, unchanged ranking metrics and correlated repeated-draw summaries. The separate original package's 41 synthetic tests were also run during this update. Original model, training, metric and selector computations and all historical tests remain unchanged. A separately tested, output-only correction lets the synthetic selector report serialize NumPy scalars on older supported pandas releases; see [the update review](../RELEASE_REVIEW_20261107.md).

## Historical empirical reproduction limits

The 13-method frozen ranking results are inspectable in the approved JSON, supplement and seven original figures. This release cannot reconstruct real analytic cohorts, original draw membership, fitted preprocessing, saved weights or participant-level predictions. Those require separately permitted data and retained private evidence. It offers no original locked-test inference or clinical threshold-execution CLI. The synthetic CLI does not regenerate the historical cohort study.

The operator reports that the private threshold calculation and its integrity review completed. Its new empirical metrics remain undisclosed. Public reproducibility therefore covers software behavior and already approved ranking summaries; it does not include regeneration of protected threshold results.

## Release checks and CI

The explicit [public file allowlist](../../.public-files.json) bounds tracked files. The [release checker](../../scripts/check_public_release.py) checks that allowlist, frozen SHA256 bindings, relative documentation links, SVG references, prohibited artifacts, absolute home paths and recognizable credentials. CI runs those checks, targeted lint, imports, all public tests and both synthetic smoke commands, without clinical inputs or credentials.

Automated scanning is defense in depth, not proof of disclosure clearance or an absence of all secrets. Adding future empirical outputs still requires the independent review described in [data access and disclosure](data-access-and-disclosure.md). Existing historical Git objects are not rewritten by this update.

## Replot approved paired AP contrasts

The [paired-contrast renderer](../../examples/plot_primary_paired_ap.py) reads only the repository's existing approved aggregate JSON. It creates a new SVG and refuses overwrite; it does not read clinical files, refit models or rerun bootstrap inference.

```sh
python -m pip install -r requirements-figures.txt
python examples/plot_primary_paired_ap.py --output results/runs/paired-ap-UNUSED.svg
```

The [tracked figure](../../figures/08_primary_paired_ap_contrasts.svg) uses the stored primary-budget logical-minus-comparator estimates and descriptive joint participant-bootstrap intervals. The full-fine-tuning contrast is primary; the other three are secondary. All include zero. An aggregate visualization is reproducible here; original bootstrap recomputation is not. See the [supervisor implementation map](../PHASE1_REPORT_TO_CODE_MAP.md) for the exact boundary and [academic-report status](../../reports/nitw-btech-phase1/README.md) for why no report PDF/LaTeX is distributed.

## Complete approved comparison figures and consistency checks

The additional two comparisons visualize existing public aggregate records, not private test inference or a new bootstrap. Install the optional figure requirements, then use fresh outputs:

```sh
python -m pip install -r requirements-figures.txt
python examples/plot_public_comparisons.py --kind auroc --output results/runs/public-auroc-UNUSED.svg
python examples/plot_public_comparisons.py --kind budgets --output results/runs/public-budgets-UNUSED.svg
python scripts/check_result_consistency.py
```

The checker reconciles all 13 methods at both budgets (78 metric summaries), 26 frozen supplement rows, 13 manuscript rows, README/guide/gallery summaries and 21 new figure points. It checks stored per-draw means, source/adaptation draw counts and bootstrap accounting, not the missing historical bootstrap executor. Actual academic PDF/LaTeX and protected threshold outputs remain outside this public check. [Artifact inventory](../PHASE1_COMPLETE_ARTIFACT_INVENTORY.md) records those limits.
