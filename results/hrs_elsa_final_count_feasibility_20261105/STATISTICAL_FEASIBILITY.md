# Count-based statistical assessment

Actual event counts for the two revised designs are **PENDING_NEW_AUTHORIZED_LOCAL_EXECUTION**. No design is empirically ranked. More cases can improve information but cannot guarantee greater AP, AUROC, calibration or clinical utility.

`precision.py` computes planning quantities within the private operation from actual qualified counts. They are explicitly assumptions, not observed performance or an automatic GO gate.

## Fixed-threshold sensitivity and specificity

At assumed sensitivity0.80, normal-approximation 95% half-width is `1.959964*sqrt(.8*.2/E)`. For hypothetical test-case counts10,50,100,200 it is approximately0.248,0.111,0.078,0.055 respectively. The approximation requires **62 observed test cases** for an assumed ±0.10 and246 for ±0.05. At assumed specificity0.90, approximately139 test nonevents target ±0.05. These illustrate precision requirements, not universal minima or actual sensitivities. Small-sample intervals require better binomial treatment; the code also supplies Wilson intervals for the observed report fraction among ascertained people, conditional on that selected sample.

Precision/F1 additionally depend on threshold-specific false positives and negatives. Without scores, thresholds or predictions, no actual accuracy, recall, F1 or specificity is calculable. Counts cannot establish that an operating point is useful. A future threshold must be selected entirely on training-side data and evaluated without readjustment on held-out participants.

## Discrimination and paired comparisons

For an explicitly assumed AUROC A=0.70, the implemented independent-subject approximation uses

`SE² = [A(1-A)+(E-1)(Q1-A²)+(N0-1)(Q2-A²)]/(E*N0)`,
`Q1=A/(2-A), Q2=2A²/(1+A)`.

It is a rough planning approximation, not an observed AUROC, a distribution-free guarantee or a paired comparison interval. See [Hanley and McNeil, Radiology1982;143:29–36](https://doi.org/10.1148/radiology.143.1.7063747). Single-class samples return unavailable, not favorable discrimination.

AP and paired AP-difference precision are **not identifiable from event counts alone**: they require justified score distributions and, for comparisons, joint score dependence. A model-based simulation could be prespecified later but would remain hypothetical. Calibration intercept/slope precision requires score spread and anticipated miscalibration; it cannot be certified by200 events or eight input variables. The report does not invent these assumptions to obtain a PASS.

## Reserves and independent evaluation

The50/15/15/20% hash scenario is outcome-blind and produces actual disjoint role-support counts after feature/timing eligibility. The10/25/50-positive adaptation checks are mathematical label-availability ceilings, not instructions to enrich the primary sample or sufficient stability criteria. Stopping and calibration require both classes; counts of one positive do not make them stable. Event/nonevent support is shown separately for every role. The untouched-test count additionally requires a reviewed prior-use history; unknown exposure stays unverified.

For a random test size n drawn without replacement from E cases and N0 nonevents, probability of both classes is

`1 - C(N0,n)/C(E+N0,n) - C(E,n)/C(E+N0,n)`.

For an IID bootstrap of an evaluation population, probability of drawing no cases is `(N0/(E+N0))^(E+N0)`. These quantify degeneracy under stated sampling assumptions, not confidence in model comparison. Repeated splits or bootstrap draws do not create new independent events. Two baseline windows containing the same people do not constitute independent tests.

## Scientific sample-size planning still required

[Riley et al., BMJ2020;368:m441](https://www.bmj.com/content/368/bmj.m441) bases development planning on complexity, outcome risk, anticipated fit and overfitting control. A neural network's adaptation complexity is not simply eight predictors. [Riley et al., Statistics in Medicine2021;40:4230–4251](https://onlinelibrary.wiley.com/doi/full/10.1002/sim.9025) plans external-validation precision for calibration, discrimination and decision utility. Setting-specific inputs matter beyond an event-count rule. These frameworks do not supply a sample-size guarantee for the current unpublished counts.

All simple calculations here assume independent people and unweighted observations. Household clustering, survey sampling, differential attrition, mortality and ascertainment error require additional assumptions; Wilson report-fraction intervals are not population incidence intervals. Current binary ascertainment may select survivors/responders. No survival-adjusted rate is estimated. More observed reports cannot repair nonidentical HRS/ELSA ascertainment.

HRS source-training support is **not recomputed** by this ELSA counter. The selected HRS strict observed-negative MI route remains unresolved; screening-assumed negatives cannot be promoted. A future model comparison needs defensible source/target definitions, predictor chronology, reserved natural-prevalence evaluation, bounded tuning and a formal precision plan before any training authorization. No empirical or clinical GO is issued here.
