# Phase 1: research overview

[Repository home](../../README.md) · [Dataset and endpoint](dataset-and-endpoint.md) · [Architecture](model-architecture.md) · [Protocol](experimental-protocol.md) · [Results](baselines-and-results.md) · [Threshold analysis](threshold-analysis.md) · [Reproducibility](reproducibility.md) · [Limitations](limitations.md) · [Access and disclosure](data-access-and-disclosure.md)

Phase 1 asks whether a five-view neural network pretrained in HAALSI, South Africa, can adapt to MHAS, Mexico, using few labeled target participants while controlling which representations change. It is a closed, report-based cross-population prediction experiment. The prespecified method is `calibrated_logical`; its primary comparator is full fine-tuning.

The design is inspired by [Cui et al.'s EEG DMV-MAT study](https://doi.org/10.1109/TNNLS.2024.3350085). Clinical feature views, representations and selection statistics were re-engineered for tabular survey data. This is neither an exact EEG reproduction nor an established novel algorithm. Source/target MMD and class geometry select trainable modules; MMD is not added to the neural training loss.

The primary result is **inconclusive**: mean paired logical-minus-full AP difference +0.001819, descriptive 95% joint participant-bootstrap interval −0.024809 to +0.032340. Head-only tuning was competitive. Nine of ten primary logical masks adapted no internal module. These findings support an executable, auditable adaptation framework; they do not establish selective-adaptation superiority or clinical usefulness.

## Evidence and reading order

| Question | Evidence |
|---|---|
| What was actually studied? | [Frozen manuscript](../FINAL_SUBMISSION_MANUSCRIPT.md), sections 3–7 |
| What are all registered results? | [Frozen supplement](../SUPPLEMENTARY_AGGREGATE_RESULTS.md) and [aggregate JSON](../../results/aggregate_only_results.json) |
| What software can be reproduced publicly? | [Reproducibility boundary](reproducibility.md) |
| What do the threshold calculations mean? | [Threshold analysis](threshold-analysis.md) |
| What remains scientifically unresolved? | [Limitations](limitations.md) |

The original [method/reproducibility summary](../PHASE1_METHOD_AND_REPRODUCIBILITY.md), manuscript, supplement and seven aggregate figures remain accessible and unchanged. These pages organize their evidence rather than replace the frozen records. New threshold findings are subject to a separate disclosure boundary.
