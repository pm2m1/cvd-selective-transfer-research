# Prospective event-count and scientific acceptance plan

**No actual new-design event counts were inspected or computed here.** The initial two-design count failed before a final report. Prior Phase2 aggregates, broad harmonized screens and different endpoint/population audits cannot be substituted for this failed operation's proposed cohort. Synthetic fixtures are not empirical support.

Primary design remains **W6→W9**; comparator remains **W4→W7**. A comparator with more favorable support cannot silently become the primary after viewing results. The estimand is first qualifying personal survey diagnosis report after verified baseline MI/stroke absence, not adjudicated clinical onset or a population incidence rate.

## Stage 1 — scientific/source correctness before arithmetic

The independent local assessment must establish the adopted participation-resolution policy, exact source/mapping/protocol/runtime bindings, completed exclusive count status, no incompatible source domains, unique exact person linkage and unchanged endpoint rules. Check all ordered waterfall and component/joint/union invariants. Evaluate both windows separately; shared participants cannot become independent replications.

Require separate counts for: baseline participants; previous MI and stroke exclusions; unknown/disputed history; verified baseline-free population; personal/nonpersonal response; qualifying incident MI; qualifying stroke; their unique union; observed nonevents; unknown/disputed/censored outcomes; closing-window coverage; death/attrition; feature completeness and chronology losses. Report unknowns explicitly. MI+stroke marginals overlap and must not be summed as the composite.

## Stage 2 — ascertainment and feature ceilings

Count known outcomes before deleting missing predictor cells. Predictor imputation can retain already known outcomes under a justified missing-data strategy; it cannot create new observed events, establish a missing interview, backdate a nurse examination or repair endpoint eligibility. Ten registered history sources do not themselves establish SBP/DBP/BMI measurement availability. With no registered nurse input or reviewed equivalent feature evidence, the existing counter reports feature/partition support as **NOT_COMPUTED**, not zero and not adequate.

Compare complete-case, measurement-eligible before predictor deletion and any separately prespecified imputation-compatible population. Distinguish absence of a measurement/instrument from cell-level predictor missingness. No future-wave predictor, retrospective revised diabetes zero or uncertain chronology may be imported as baseline certainty.

## Stage 3 — disjoint source/target capacity

The counter's fixed 50/15/15/20 hash scenario is an outcome-blind **capacity scenario**, not an existing test lock or a modeling dataset. Inspect actual positive/nonevent support in adaptation, stopping, calibration and evaluation roles only after feature/timing eligibility. Independent-test support additionally requires explicit prior-use evidence; unknown use is not untouched. All labels used for fitting, stopping, calibration or model selection count toward target label consumption.

Retain the project's default **200 observed untouched target-test event aim**, alongside the historical 100-nonevent screening aim; neither is a universal minimum or proof of precision. If the proposed confirmatory design cannot meet its prespecified aim plus development reserves, it fails that design rather than lowering its aim post hoc. A different exploratory or zero-shot question needs an explicit new design, not a relabelled PASS.

The existing public redesign candidate lists positive-adaptation capacities 10/25/50 and a candidate development-validation reserve of50 positives. These are planning assumptions, not proof of sufficient training/calibration or instructions to enrich a primary random-label sample. Preserve a natural-prevalence target evaluation. The largest adaptation budget plus all separately required reserves must fit simultaneously; overlapping draws/resamples do not create independent events.

HRS source-training support requires its own validated cohort and sample-size assessment. This ELSA counter does not compute it. Strict directly observed-negative HRS MI remains disabled without supporting original Core route evidence; screening-assumed negatives stay sensitivity-labelled. Source-specific label asymmetry cannot be turned into strict harmonized incidence by a successful training run.

## Stage 4 — precision requirements, prospectively specified

Reuse the existing pure `../hrs_elsa_final_count_feasibility_20261105/precision.py` inside the separately permitted private assessment, rather than create another validator. Its assumptions are explicit:

- At assumed sensitivity0.80, approximate 95% half-width `1.959964*sqrt(0.8*0.2/E)` needs62 test events for ±0.10 and246 for ±0.05. At200 it is about0.055. These are conventional planning approximations, not observed sensitivity or exact guarantees.
- At assumed specificity0.90, approximately139 nonevents target ±0.05. Small-sample interval behavior still needs proper evaluation.
- AUROC planning at assumed0.70 uses the documented Hanley–McNeil approximation; no score or model performance is observed by this arithmetic.
- AP, paired AP-difference and calibration-slope precision **cannot be identified from event counts alone**. A reviewed score-distribution/joint-dependence/anticipated-miscalibration plan or appropriate prior evidence is required. Favorable hypothetical simulation cannot certify empirical feasibility.
- Random test both-class probability is `1−C(N0,n)/C(E+N0,n)−C(E,n)/C(E+N0,n)`; bootstrap no-case probability is `(N0/(E+N0))^(E+N0)`. Report degeneracy/unavailable resamples rather than optimistic estimates.

Source/model development must account for complexity, anticipated fit and overfitting control, not just eight input roles or a simplistic events-per-variable rule. A roughly eight-thousand-parameter network is not an eight-parameter logistic model. Study-specific formal precision and comparison requirements take precedence over count screens. Survey clustering, selection, censoring and measurement error remain additional assumptions beyond independent-subject arithmetic.

Primary methodological references already used by the project: [Riley etal., development sample size](https://www.bmj.com/content/368/bmj.m441); [Riley etal., external validation planning](https://onlinelibrary.wiley.com/doi/full/10.1002/sim.9025); [Hanley and McNeil AUROC planning](https://doi.org/10.1148/radiology.143.1.7063747). These support planning principles, not a clinical GO claim for unseen counts.

## Stage 5 — private disposition and handoff

| Result | Correct disposition |
|---|---|
| Scientific inconsistency unresolved, inputs incompatible, failed accounting or chronology | BLOCKED; no training/export |
| Endpoint valid but predictor/source/test-use/precision evidence missing | EVIDENCE_INSUFFICIENT; finish that exact dependency privately |
| Confirmatory untouched-test aim/development reserves unsupported | NO_GO for that confirmatory design; evaluate a separately justified narrower objective |
| All scientific, capacity, formal precision, feature and independent-use criteria supported | Eligible for **separate** analysis-dataset/partition authorization and modeling review; not automatically authorized |

All empirical counts and data-conditioned verdicts remain private pending disclosure review. A public software PASS is never a scientific acceptance. This plan does not manufacture a human sign-off or change any formal NO_GO flag.
