# Supplementary threshold-analysis protocol — 7 November 2026

## Scope and estimands

The estimands are per-model/per-frozen-draw classification metrics on the **same original283-person MHAS test**, at the ten fixed cutoffs specified for this supplement. This is not an original preregistered threshold analysis, new inference, new training, a new test population or confirmation of an optimized cutoff. No clinical operating point or superiority claim is selected from these data.

The grid is exactly0.05 through0.50 in steps of0.05. Predicted positive iff the retained probability is greater than or equal to the cutoff. No sigmoid, calibration, ranking modification, probability averaging, participant resampling or draw pooling is performed. Unknown labels, duplicates, invalid/nonfinite probabilities, missing draws, unregistered models and unreconciled metrics stop the operation.

This release's copied cleared references certify the primary25+75 budget and original source-only vector. A secondary-budget checkpoint map cannot be relabeled as that primary score/reference comparison; the new wrapper explicitly rejects such a budget mismatch. No secondary threshold result is inferred from primary scores.

## Calculation order

1. Guard independent local operation, scope, public-source integrity and the new configuration. Reuse the recorded original metrics configuration from its completed provenance or an explicit original reviewed configuration. The sole relocation is an identical, hash-bound **public ranking-reference file** bundled here; private paths/keys are not substituted.
2. If authentic original validation descriptors are recorded, verify the original registration/payload/provenance/checkpoint relationship and171/13 membership disjoint from test IDs. Select each supported model/draw threshold from validation data **before opening test probabilities or labels**. Ignore unselected validation arrays without dereferencing them. If no original validation is recorded, every affected model has the explicit not-established status.
3. Use the unchanged frozen test reader: fixed registration/completed-manifest/reference hashes, complete frozen model/checkpoint/draw mapping, bound NPZ and ordered-ID files,283 unique nonempty string IDs and shared283-length binary labels with21/262 classes. Historical writer order and entire-file hashes bind alignment; counts alone do not.
4. Recompute per-draw AP/AUROC/Brier and their arithmetic means against the original full-precision references, tolerances atol=rtol=1e−8. Every requested model must pass before any threshold report is created. A disagreement stops; no tolerance relaxation, score transformation or replacement inference is allowed.
5. Calculate each grid point for each retained draw. TP/TN/FP/FN are integers. Accuracy=(TP+TN)/N; precision=TP/(TP+FP); recall=TP/(TP+FN); specificity=TN/(TN+FP); F1=2TP/(2TP+FP+FN); balanced accuracy=(recall+specificity)/2. The unchanged original implementation also supplies FPR/FNR/NPV/MCC in JSON. Undefined ratios remain null/N/A; zero recall with no predicted positives is retained honestly.
6. Summarize each metric across draws with number defined/undefined, mean, sample SD(ddof1), minimum and maximum. Means are of per-draw metrics, not metrics recomputed from a pooled or fractional mean matrix. Source-only has one row and no across-draw SD. The shared test population remains283, not ten times that.
7. Write private tables/figures/provenance/integrity and permanent completion status. Recheck all input fingerprints before reporting and after rendering. A failure may leave private partial outputs, but never a reusable successful attempt. Prior results remain untouched.

## Optional original-validation selection

The selection rule is inherited unchanged: maximize validation F1 over unique validation probabilities plus0,0.50 and1; break ties toward the highest cutoff. Partial authentic availability is explicit: only models named in the original-validation mapping receive a selected cutoff; other models remain not established. Missing or corrupt **declared** evidence causes a fail-closed operation rather than a silent fallback.

A source-only score model still consumes target-validation labels if its operating threshold is selected using those labels. It must not be described as a zero-target-label threshold-selection procedure.

The existing public audit establishes that the reviewed original development runners did not persist validation probability arrays. This package does not reconstruct them or run inference. Only independently found authentic original retained exports qualify. Shape, an origin literal or a newly created manifest alone does not authenticate retention; the operator must establish actual provenance. Never manufacture that evidence.

A selected numerical threshold is applied unchanged to the frozen test. No test threshold sweep, test F1 maximum, target-test model choice or threshold recalibration is used for selection. With13 validation positives, threshold selection is unstable; its own optimized validation F1 would be optimistic resubstitution. The test has already been examined historically, so this supplementary result cannot be presented as a newly confirmed independent evaluation.

## Interpretation and disclosure

The21 held-out positives limit sensitivity precision. Repeated adaptation fits share participants and are correlated. SD/ranges and plot bands describe fitted-draw variability, not independent-test standard errors or confidence intervals. High all-negative accuracy is not successful event detection. AP depends on prevalence and ranked scores; it is neither fixed-threshold precision nor trapezoidal PR area over these ten grid points. Threshold changes alone cannot change AP/AUROC/Brier.

All actual cells, rates, differences, plots, source fingerprints/paths and reports remain private pending applicable disclosure review, including joint small-cell and differencing risks. Console acknowledgment is operational only. Original ranking results and the inconclusive paired comparison remain frozen. No B.Tech manuscript, publication, checkpoint or original authorization is edited.
