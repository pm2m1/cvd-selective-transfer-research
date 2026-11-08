# Fixed experimental protocol

[Phase 1 index](overview.md) · [Frozen manuscript, sections 6–7](../FINAL_SUBMISSION_MANUSCRIPT.md)

## Partitions and target-label use

One deterministic target lock used seed `20261025`. Source train, validation and held-out roles were fixed. Target adaptation, validation and test roles were fixed. Ten **overlapping paired adaptation draws** used 25 positive plus 75 negative labeled participants; the secondary 10-positive/30-negative draws were nested. Every adapted comparator used the same corresponding draw. This was **not conventional three-fold, five-fold or ten-fold cross-validation**.

The 171 target-validation participants, including 13 positive reports, were additional to the adaptation-label budget. They governed permitted early stopping and development reporting, not adaptation gradient fitting or selector scoring. Accordingly, “100 adaptation labels” does not mean only 100 target labels influenced the entire development process. Both budgets were enriched to 25% positives; neither is an outcome-blind random-labeling design.

Transfer models began from the relevant frozen source checkpoint. Source-only controls did not use target adaptation labels. Target-only models fitted their own preprocessing and models using their draw. Transfer preprocessing was fitted on source training only. Neural settings were AdamW, learning rate 0.001, weight decay 0.0001, batch size 64, maximum 30 source/20 target epochs, patience 5. The released training function uses validation BCE and minimum improvement 1e−5; the first candidate follows an optimizer epoch, not an evaluated epoch-zero candidate. Generic CLI defaults, including patience, need not equal the historical overrides.

The architecture, masks, checkpoint inventory, preprocessing and statistical rules were frozen before the registered evaluation. No test-informed model choice, recalibration or threshold tuning was part of that original comparison. A separate later descriptive threshold supplement must not be represented as preregistered.

## Primary estimand and uncertainty

Let $AP_{m,d}$ denote AP for method $m$ and draw $d$ on the same test participants. The primary estimate is $10^{-1}\sum_d(AP_{logical,d}-AP_{full,d})$. It is not AP computed after averaging probabilities or concatenating ten copies of participants.

The registered bootstrap sampled **test participants jointly across every method and draw**, 2,000 replicates with seed `20261026`. It recomputed per-draw statistics and their arithmetic means, preserving pairing and shared membership. The 2.5th/97.5th percentile interval is descriptive. It does not estimate variation across independent countries or independent training populations. No formal superiority/equivalence test was registered; no registered AP, AUROC or Brier replicates were discarded.

## Test-execution history

The first authorized attempt accessed test rows and failed before predictions or metrics during a native runtime stall. Its authorization was consumed. A separately authorized, process-isolated recovery evaluated the **same frozen test**, keeping the scientific specification unchanged. See the preserved [incident summary](../PHASE1_METHOD_AND_REPRODUCIBILITY.md) and [audit timeline](../../figures/07_audit_timeline.svg). This release provides no original-test inference command.

## Design limits

Thirteen validation positives make stopping and rankings noisy. Reporting on the same validation labels used for stopping is not independent assessment. Twenty-one test positives limit sensitivity precision. Ten correlated draws do not create ten external validations. The [threshold supplement](threshold-analysis.md) preserves these limits and does not reopen model selection.
