# Validation — public training fast-track V1

## Actual execution and test results

- New focused suite: **32 passed,0 failed,1 skipped**. The skip is the real MPS forward/backward test because this session reports MPS built=True,available=False. Explicit unavailable-MPS rejection is tested; no MPS execution is claimed.
- Relevant frozen public count regression, run once by the count workstream: **96 passed,0 failed** (0.41s), plus `PASS PUBLIC_COUNT_PACKAGE_VERIFIED`. No original count code or scientific policy changed.
- The complete seven-method CPU synthetic demonstration actually completed with separate serialized/reloaded development/test inputs, source preprocessing, optimizer/backpropagation, selector/freezing checks, checkpoints, calibration/thresholding, development selection and separate frozen evaluation. It printed `SYNTHETIC_ONLY COMPLETE NO_REAL_COHORT_OR_CLINICAL_PERFORMANCE_CLAIM`.
- Same-seed CPU synthetic reruns produced identical evaluation dictionaries, including fixed/calibrated metrics and paired bootstrap output. Timing is not required to match. No cross-hardware or MPS bitwise guarantee is claimed.

Focused source command:

```sh
.venv/bin/python -B -m pytest -q -p no:cacheprovider results/hrs_elsa_training_fasttrack_20261106/tests
```

Published aggregate demonstration artifacts are under `synthetic_results/`. Complete generated arrays/model artifacts are in the separate, explicitly invented `results/hrs_elsa_training_fasttrack_20261106_SYNTHETIC_FINAL_RUN/`. No real dataset, old checkpoint, locked-test prediction, private scientific finding or consumed research receipt was accessed.

## Verified safeguards

- Exact24-array development and separate4-array test contract; unexpected test keys rejected **before payload access**.
- Ordered eight roles, endpoint sensitivity labels and explicit source/target windows; no silent strict-negative substitution.
- Exact Unicode private membership digests, no overlap, frozen outcome-blind partitions, stable role across windows/population changes.
- Source-only preprocessing fit, wholly missing source-feature rejection, explicit categorical domains and declared future/structural measurement rejection. Actual chronology still needs the reviewed export; numeric arrays cannot independently prove it.
- Unknown/missing outcomes are rejected rather than imputed negative.
- Optimizer parameter identities equal trainable tensors; SHARE tensors stay unchanged; actual epoch-zero restoration and forbidden stopping/fitting roles tested.
- Dedicated calibration and minimum support; unavailable thresholds/metrics represented honestly. All-negative prediction precision is undefined and recall zero when events exist.
- Held-out artifact/config/threshold/code/runtime and complete method registration checked before actual test-array loading. No test selection or threshold update occurs.
- Paired participant bootstrap uses common resamples, records single-class degeneracy and does not claim survey/training uncertainty coverage.
- Real private config templates stop before data access; metadata-only preflight is tested not to open participant array bytes.
- Agent preflight/authorization/execution guards reject before private config reads; old purpose rejected; interrupted output stays consumed; existing destinations and changed public bytes rejected.
- Explicit validator issue allowlist preserves owned stable issue codes without printing arbitrary library errors or sensitive scalar text.

## Runtime and scope limits

Verified environment: Python3.12.14, PyTorch2.14.0, NumPy2.5.3, pandas3.0.6, scikit-learn1.9.1, SciPy1.18.1, joblib1.6.0, pytest9.1.1. Dependency pins are supplied. No frozen environment was altered or dependency installed by this task.

The code is not a raw clinical cohort extractor. Exact input derivation remains dependent on the scientifically adopted eligibility/source policy and permitted source/feature evidence. Boolean timing/review declarations and hashes document independently established facts; software cannot create those facts or certify provider approval. Real stage gates remain unresolved in every distributed template.

Public HRS mapping: **PARTIAL**. Public ELSA mapping: **PARTIAL**. ELSA semantic conflict: **UNRESOLVED**. Current two-design accepted event counts: **NOT_AVAILABLE**. Current real modeling: **BLOCKED**. No empirical failure or success is inferred from inaccessible private diagnostic findings.

## Public source SHA256

| File | SHA256 |
|---|---|
| `src/fasttrack/contracts.py` | `476cabffdeacb78886b194e8d9f7a6d110c994ce93efe274f5654a3b08f8538d` |
| `src/fasttrack/preprocessing.py` | `751615f52960183676f7ca81ff3ea65c6211947e7da1517aef4042048f4baa95` |
| `src/fasttrack/models.py` | `c17fc07700baccaa19191fe53ef31ab6832c270684b99738a7f240d588498af1` |
| `src/fasttrack/metrics.py` | `bc2fb0169cc6900bb1a10cf6a44f57f9fa739987ceca6354dfb13cf1e6a187c4` |
| `src/fasttrack/pipeline.py` | `a62001bee8ca95296f0fd32970f8e46321b237e68b3e3ba967636f88e6647d2f` |
| `src/fasttrack/runtime.py` | `1b26a04191f7dee69426f96299453064431fde8e9e81c58e2368b4324726fac8` |
| `scripts/run_experiment.py` | `16d6da2d3bf4aee23de0608c894d63f069cf79d762ff4a834e907d210c71b803` |
| `configs/training_protocol.json` | `e6ad9c2adcdf6d8d9e8f067de5808b7292b725d55f90f4dc388eec66933cb7a0` |

`RELEASE_MANIFEST.json` pins all distributed public files except itself. The adjacent ZIP verification receipt records clean extraction, tests, public installation and the exact ZIP SHA256. That receipt is a public build record, not a clinical permission or authorization.

## Scientific disposition

**CONDITIONAL GO for this staged public-engineering path; no real-data GO.** First independently review/adopt the completed private status evidence, justify a new count release if possible, establish real source/target counts/features/precision, and derive a permitted canonical dataset with genuinely untouched evaluation membership. New independent authorizations are required for development and final evaluation. This task grants none and changes no formal historical NO_GO flag.
