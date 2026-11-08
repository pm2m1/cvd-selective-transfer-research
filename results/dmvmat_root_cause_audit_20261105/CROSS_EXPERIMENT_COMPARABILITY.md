# Why the two development experiments are not paired

Public sources: S/experiment_tools/train_exploratory_candidates.py:100–142; F/experiment.py:17–140; F/design.py; F/results_report.py:29–98; F/SCIENTIFIC_PROTOCOL.md. S and F are defined in ROOT_CAUSE_REPORT.md.

| Dimension | Seven-candidate development run | Retrospective label-budget follow-up |
|---|---|---|
| Evaluation participants | Previously designated target validation, 171/13 public contract | Target adaptation pool679/49, participant-held-out outer folds |
| Target fitting population | Ten frozen enriched draws from adaptation pool | Random nested prefixes from each outer-training membership |
| Labels for weight fitting | 100 per draw, exactly25 positive+75 negative | 27–273, not enriched; depends on budget |
| Full target-label conditioning cost | 100 plus all171 STOP labels; threshold selection reuses those171 | Prefix45/113/226/339/452–453 includes fit+stop+calibration; all679 evaluation labels/historical exposure counted separately |
| Target stopping | Same171-person validation population later scored | Dedicated inner STOP subset9–90 |
| Threshold selection | F1 selected and evaluated on same171, optimistic resubstitution | Dedicated inner CALIBRATION9–90; numerical threshold evaluated only on held-out outer fold |
| Source training | Original and compact independently trained on source1744/65, stopped on581/21 | Same algorithm/populations/configuration inherited by retained export |
| Source seeds | 20261025 | 20261025 |
| Target/selector seeds | 20261025+draw | repeat_seed+1000*fold+budget_n; repeats20261105–07 |
| Target LR/BCE/epochs | .001/20/BCE for shared four; extra .0001/.0003 variants among seven | .001/20/BCE for all shared four |
| Selector inputs | source validation + enriched100-person adaptation draw | source validation + FIT only, with potentially few positive events |
| Selector geometry | Real199 permutations/bootstrap; same thresholds/min-class rules | Same; mask recalculated each fold/budget/repeat |
| Architectures | original8033; compact2225; head33; target-only logistic | original8033 / compact2225; no logistic or LR variants |
| Normalization | Export source-training fitted for all seven | Same unchanged source-fitted arrays; no target refit |
| Epoch selection | Validation BCE, patience5 | Inner STOP BCE, patience5, smaller random support |
| Zero-target reference | Not a candidate in seven-run ranking | Actual original pretrained model; no target stopping/calibration |
| Aggregation | Mean ten correlated draw metrics on one171-person population | Per-repeat pooled OOF metrics over679, then mean three correlated repeats |
| Paired reporting | Across methods on same old validation | Same outer split, paired against matched_control; source-only paired inference not provided by current summary |
| Threshold availability | Both classes in old validation under public contract | Unsupported calibration folds explicitly unavailable; matched-support fixed comparison |
| Independence | Exploratory validation already used for selection | Architecture/population already exposed in earlier research; CV is not external validation |

## Plausible explanations for a ranking reversal

1. The evaluation population changes. Better compact performance on the old171 can be a population-specific or noisy development finding, not an ordering expected to repeat on another population.
2. The original100 includes25 positives; the random FIT subsets are not enriched and can have very few or zero events. Budget percent is not a count of positive cases. BCE sees different empirical priors and representation evidence.
3. The later STOP subsets can contain nine labels, compared with171 originally. The same patience and BCE rule therefore have different uncertainty; original validation labels also selected checkpoints before being scored, making those comparisons less protected from optimism.
4. Logical previously had25 fitting positives; later geometry may abstain for insufficient support, or select different high-dimensional blocks when evidence changes. Neither abstention nor a larger mask implies a code bug.
5. Four methods retained .001 LR; the later experiment does not demonstrate whether either lower-LR candidate would be better under the new split design.
6. Each compact model has its own source representation, not a smaller target-only copy of the original network. Architecture and source initialization differences cannot be attributed solely to a target adaptation mask.
7. Pooled OOF compares scores from fold-specific adapted models with a shared source reference. Cross-fold score offsets can affect pooled AP independently of each fold's ranking.
8. Repeated adaptation draws and repeated outer seeds share participants. A change in a descriptive mean is not an independently replicated superiority/reversal claim.

No numerical scores from the two completed private development outputs were read or compared. No cause was assigned from their rank ordering alone.

## Controlled future comparisons

Keep a fixed public protocol's participant roles, outcome definitions, source-preprocessing state, source initialization, fit/stop/calibration budgets, optimizer and seeds. Change one factor at a time; measure paired AP/AUROC/Brier on identical outer participants. Always include original source-only predictions and each architecture's own source-only counterpart when interpreting adaptation effects. Report within-fold differences alongside the registered pooled-OOF estimand. Do not silently replace a historical primary aggregate with whichever is favorable.

To isolate population effects, score fixed models on different eligible populations without retuning only under a separately authorized prespecified comparison, and do not describe the already examined cohorts as new independent tests. To isolate enrichment, compare prespecified random vs enriched training designs with complete positive-label discovery costs and separate evaluation; do not cherry-pick event-rich subsets. To isolate stopping size, retain disjoint labeled budgets and explicitly account for labels moved out of fitting. These are alternative prospective questions, not instructions to rerun the old operations.

The one recommended next experiment is narrowly specified in FUTURE_EXPERIMENT_PROPOSAL.md: identical full adaptation, differing only in epoch-zero checkpoint eligibility. Other comparisons remain future alternatives.
