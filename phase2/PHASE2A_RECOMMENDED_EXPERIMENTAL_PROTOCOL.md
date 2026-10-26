# Phase 2A recommended protocol for a *new* study (proposal, not locked)

## Preferred direction and independence

**Candidate source:** HRS 2012 respondent cohort. **Candidate sparse-label target and genuinely new external evaluation population:** ELSA Wave 6 (2012/13) respondents followed at Waves 7–9. These are independent of the closed HAALSI/MHAS pair. CHARLS or SHARE may later become a second external population only after endpoint crosswalk and access checks; neither is a valid extra heart-attack/stroke test by assumption. **No original MHAS target participant, prediction or frozen checkpoint will be used in Phase 2.** Original published aggregate results explain the research question but must not tune a new rule.

## Stage 0 — authorize and verify datasets before modeling

Register individually and accept the official HRS/UKDS terms; obtain any HRS Sensitive Health or ELSA Special Licence access **only through the relevant formal route** if required for the chosen measurements. Record product versions, licences, checksums, codebooks, IDs and join rules. Do not redistribute row-level records. The first analysis is an aggregate-only cross-wave audit of field definitions, baseline timing, prevalent heart attack/stroke, incident reports, death, proxies, noninterview, missing predictors and observed follow-up. Verify exact HRS/ELSA questionnaire routing and whether a common `doctor-reported heart attack OR stroke` policy is supportable. A wave-based endpoint should not be relabelled as an adjudicated or precisely dated first event.

## Stage 1 — lock a feature and endpoint contract

Prepare *common* and *lipid-extended* feature tiers as outlined in [dataset comparison](PHASE2A_DATASET_COMPARISON.md). Use the exact same rows, fields, encodings and observation rule in every within-tier model comparison. If the lipid tier uses a selected health-visit subcohort, report how it differs from the common tier before interpreting any performance difference. Establish a baseline landmark **after** all baseline predictors used in a tier were measured; if exact dates are unavailable, use an explicitly wave-based policy and document potential interval cases. Record source/target unit and assay differences. Do not coerce unknown outcome or death without a qualifying report to negative. Decide whether survey weights apply to descriptive or predictive estimands before fitting.

## Stage 2 — sample-size and label-budget gate

Do **not** copy the original 21-event test design. The older [100-event/100-nonevent recommendation](https://pubmed.ncbi.nlm.nih.gov/15845334/) is a **minimum screening rule**, not a sufficient-power result. Plan for **at least 200 observed target events in a wholly independent test partition** as a conservative design target, with an adequate nonevent count; require a formal [Riley-style precision calculation](https://doi.org/10.1002/sim.9025) for AUROC, calibration intercept/slope and overall accuracy, plus a prespecified paired bootstrap/simulation check for AP and the primary AP difference. Set desired interval widths and plausible event prevalence before any test lock. If the resulting target need exceeds 200 events, use the larger number. If a lower number is scientifically proposed, justify it from the explicit precision analysis and narrow the claims; under 100 test events, **NO-GO for a confirmatory small-difference comparison**.

The target also needs separate positive events for training/adaptation and model selection. Candidate label budgets are **10, 25 and 50 positives**, each with a prespecified total labeled sample and nonevent ratio, only where the development pool can support them. Count every target label used by method fitting, source-relative calibration, selector scoring, hyperparameter search and early stopping. A 10-positive budget is exploratory, with coarse uncertainty. Do not claim an available 50-positive budget until the eligibility audit proves it. New candidate source-training and target event counts are currently **unknown**; whole-wave sizes do not fill this gap. Use one prespecified split seed, no favorable seed search, and a single immutable external test after the cohort/sample-size gate passes.

## Stage 3 — train/development protocol, only after a new authorization

Freeze endpoint, feature tiers, source/target population and baseline handling before fitting. Within target development, construct identical nested target-label draws for all methods at each budget; any repeated draws share the same validation people and must not be treated as independent test cohorts. Fit preprocessing on source training for source-pretrained transfer models and on target adaptation training for target-only models. Use development validation exclusively for the prespecified limited tuning/early stopping and any calibration; a calibration fit consumes labeled validation information and should not be reused to claim unbiased development performance.

Mandatory comparators: source-only and target-only elastic-net logistic, intercept/slope model updating, pooled model with an explicitly defined population weighting, boosted trees, source-only neural, head-only and full fine-tuning, global source-centred shrinkage, and (if lawful unlabeled target development covariates exist) CORAL. Only then test view-specific soft shrinkage; neural soft adaptation is conditional. Hyperparameter-search budgets must be comparable and documented. If simple models win, report that rather than increasing method complexity.

## Stage 4 — independent evaluation plan to freeze before opening a new test

Primary metric: target **average precision**, always accompanied by target event prevalence. Primary contrast: proposed view-specific shrinkage minus the strongest **predeclared** conventional baseline, chosen by a rule fixed on development data before test access (for example, select between elastic-net and XGBoost on development validation; retain both in the final table). Secondary AUROC, Brier, calibration intercept/slope and negative-transfer relative to source-only. Evaluate common-tier and lipid-tier contrasts separately. Jointly resample **participants** for paired test intervals across all methods and adaptation draws; preserve shared test-person correlation and report failed resamples. Predefine the number of draws, seeds, CI method, calibration procedure and analysis multiplicity. Do not claim superiority from a small positive point estimate or a wide interval spanning zero. Report observed-case conditioning, attrition, possible diagnosis error and between-country measurement differences.

## Go/no-go dependencies before Phase 2B *model training*

1. Legitimate HRS and ELSA access for the exact products and lawful processing/redistribution policy.
2. Field-level endpoint and feature crosswalk, baseline landmark and death/nonresponse accounting.
3. Aggregate-only source/target eligibility and **incident event counts**, with a target pool large enough for separate adaptation, development validation and the planned independent test.
4. External validation precision calculation demonstrating the registered AP/AUROC/calibration contrasts can be informative; ≥200 test events is a design target, not a guarantee.
5. Pre-registered common-vs-extended feature comparison, all comparator tuning budgets, and a new untouched test lock independent of the old MHAS lock.

Until these are met, Phase 2B may perform access, codebook reconciliation and aggregate feasibility screening under the relevant permissions, but it should **not begin model development or create a new final test lock**. No training or participant-level Phase-2 data handling occurred in Phase 2A.
