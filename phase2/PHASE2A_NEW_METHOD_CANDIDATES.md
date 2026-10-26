# Phase 2A: three testable method hypotheses

These are **untrained proposals** for a new HRS→ELSA study, conditional on access, endpoint compatibility and sufficient events. They were motivated by development-stage failure analysis and established prior art; **the closed MHAS held-out result is not an optimization set**. Exact estimands, penalties, grids and feature tiers must be frozen before any new external test access.

## 1. Preferred: uncertainty-aware, view-specific source shrinkage in a small tabular model

Fit a regularized source logistic model on the common feature set. Adapt a target intercept and coefficients under penalties toward source coefficients, grouped by the medically defined views. Target-label evidence and its uncertainty determine whether each group remains close to source or is allowed to move; uncertain evidence triggers stronger shrinkage rather than a forced binary SHARE/ADAPT mask. A simple formulation is target logistic loss plus `sum_v lambda_v * ||beta_target,v - beta_source,v||²`, with the group penalties selected by a **prespecified, training-only** hierarchical/empirical-Bayes or bounded-validation rule. Unpenalized target intercept adaptation should be considered separately because target prevalence and case-enriched sampling differ. The exact rule is future work, not secretly fixed here.

**Hypothesis:** at 10–50 target positive labels, calibrated group shrinkage reduces negative transfer or improves AP/calibration over target-only elastic net, source-only, simple intercept/slope updating and a single global source-centred penalty, while avoiding the original selector's all-or-none abstention.

**Prior-art/novelty boundary:** source-centred regularization, multitask shrinkage and clinical model updating already exist ([L2-SP](https://proceedings.mlr.press/v80/li18a.html), [regularized multitask learning](https://aima.cs.berkeley.edu/~russell/classes/cs294/f05/papers/evgeniou%2Bpontil-2004.pdf), [updating review](https://pmc.ncbi.nlm.nih.gov/articles/PMC9742671/)). Group-specific uncertainty control is a *hypothesis to develop and test*, not claimed novel until a deeper prior-art search. The key ablation is global penalty versus group-specific penalty using the same labels and features.

**Failure condition:** the group penalties collapse to a global penalty, are unstable across target subsamples, or provide no credible gain over elastic net/boosting with adequate test precision. If so, report the null result.

## 2. Classical-first model updating and transportability benchmark

Compare source-only, target-only and pooled regularized logistic models; intercept-only and intercept-plus-slope recalibration; elastic-net coefficient updating; and an established boosted-tree model. Optionally add CORAL on **development-only unlabeled target covariates** with the same feature tier. This is a necessary baseline program, not presented as a new algorithm.

**Hypothesis:** a simple model update or regularized tabular model performs at least as well as a neural transfer model under sparse labels, with more stable probabilities and lower compute cost. This may overturn the rationale for a complex selector. Cross-country outcome/measurement differences could also make any source transfer harmful.

**Failure condition:** the simple models are consistently worse on independent target data under paired uncertainty, or calibration deteriorates despite discrimination; still retain them as controls.

## 3. Conditional neural extension: soft view adaptation without a hard mask

Only if Candidate 1 and strong baselines reveal a remaining nonlinear signal, test a **small, fixed** five-view architecture with continuous source-centred penalties or low-dimensional per-view gates. Do not use marginal MMD as an optimizer loss by default. No architecture search using a held-out test. Match label access, feature tier and preprocessing with head-only/full fine-tuning and L2-SP. Include an explicit no-source and globally penalized ablation.

**Hypothesis:** soft, uncertainty-constrained changes to view representations can exploit target-specific signal that linear transport cannot, without requiring a dubious 0/1 module decision.

**Prior-art/novelty boundary:** selective fine-tuning, adapters, L2-SP and gating are established ([surgical fine-tuning](https://openreview.net/forum?id=APuPRxjHvZ), [SpotTune](https://openaccess.thecvf.com/content_CVPR_2019/html/Guo_SpotTune_Transfer_Learning_Through_Adaptive_Fine-Tuning_CVPR_2019_paper.html)). Do not claim novelty from using these components together. This extension is deprioritized unless independent development data justify its additional degrees of freedom.

## Shared constraints

- Same independently acquired cohort, baseline landmark, endpoint policy, labeled target people and feature tier for every compared method.
- Source and target preprocessing fitted only on their permitted training partitions. No target external-test features used even for unsupervised alignment.
- Prespecify source-only, target-only, regularized logistic, boosted trees, head-only/full and global source-shrinkage controls as appropriate to each candidate.
- Record label counts **and** total labeled participants, naturally observed evaluation prevalence, target-label sampling fraction, calibration procedure, compute and trainable parameter count.
- Treat negative transfer and uncertainty of the **paired** performance difference as first-class outputs. Do not select a method merely because it wins an undersized validation set.
