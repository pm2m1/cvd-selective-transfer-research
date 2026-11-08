# SHARE/ADAPT correctness

Scope and source aliases are defined in ROOT_CAUSE_REPORT.md. No private masks, values, parameter counts or results were read.

## Actual implementation

The original network maps five encoded views of dimensions 4,2,3,4,6 through separate Linear→ReLU→LayerNorm encoders of width 16. Concatenated width 80 enters fusion1 (80→64, ReLU, LayerNorm), fusion2 (64→32, ReLU, LayerNorm), then a 32→1 head. Seven blocks are selectable; the head is always target-trainable. Compact uses encoder width eight and fusion 40→32→16 with 17 head parameters, totaling 2,225. A logical mask never switches between these architectures.

The raw view roles are background(age, sex), haemodynamic(SBP, DBP), metabolic(BMI, total cholesterol, HDL), behaviour(smoking status), and comorbidity/medication(diabetes, antihypertensive treatment): S/public_project/src/dmv_mat_cvd/data/public_v2.py:21–27. Categorical unknown levels explain why ten raw predictors become19 encoded coordinates; the dimensions are not19 independently collected clinical measurements.

The transfer selector examines representations from the fitted source model, using source validation and **target fitting data only**. MMD and geometry are detached NumPy statistics; neither becomes an alignment-loss term. The domain test uses four Gaussian kernels (bandwidth .5/1/2/4), label-blind pooled RMS scaling, up to 128 observations per domain and 199 conditional permutations in the real protocol. P=(1+number of null statistics at least observed)/(B+1), with the implementation's 1e-12 comparison tolerance. Domain separation alone is insufficient for adaptation.

Let d_s and d_t be positive-minus-negative centroid vectors, a_s and a_t the mean of each class's mean Euclidean radius, and u_s=d_s/||d_s||. The implemented signed retention is

`R = [(d_t · u_s)/a_t] / [(d_s · u_s)/a_s]`.

Orientation reversal gives negative R even when unsigned discriminability is unchanged. Source and target geometry require at least five examples of each class, finite nondegenerate within-class scatter and source discriminability at least .1. Bootstrap mean contrasts use fixed fitted source direction and plug-in radii. At least 95% of bootstrap source standardized contrasts must exceed .02. This is conditional exploratory uncertainty, not an end-to-end scientific confidence guarantee. The .05 and .95 quantiles define a central **90%** interval; the upper endpoint is a one-sided 95% bound. No 95% two-sided claim is justified for those endpoints.

For valid geometry, logical chooses ADAPT precisely when

`upper < .75 OR (domain_status == valid AND domain_p <= .05 AND R < .8 AND upper < 1)`.

The first branch does not require a significant domain test. This is explicit code, not a missing `AND`. Strict inequalities matter at .75, .8 and 1; p=.05 is included. Invalid geometry yields SHARE with an ABSTAIN reason. Valid-but-nonfinite retention raises an error. The threshold-policy branch uses different rules and is not the `logical` candidate.

Randomness: module names sorted; module i's MMD seed is base+i and geometry seed base+1000+i. The target fit seed is repeat_seed+1000*fold+budget_n. Selector recomputes per condition from fit features/labels. No target-mask cache exists. Source models alone are cached; each target model is a deepcopy with a fresh optimizer. Tests show identical inputs and seed reproduce evidence and mask.

## Exact parameter accounting

| Block | Parameters |
|---|---:|
| Background encoder | 112 |
| Haemodynamic encoder | 80 |
| Metabolic encoder | 96 |
| Behaviour encoder | 112 |
| Comorbidity/medication encoder | 144 |
| Fusion1 | 5,312 |
| Fusion2 | 2,144 |
| Always-trainable head | 33 |
| Total | 8,033 |

Thus `N_updated = 33 + sum(N_block for every ADAPT block)`. All SHARE gives 33; all views ADAPT gives 577; fusion1 alone gives 5,345; fusion2 alone gives 2,177; both fusions give 7,489; all blocks gives 8,033. Large jumps are expected. Different masks can yield the same count because some view blocks have equal size. Count alone cannot recover a mask.

The follow-up records this after freezing/training at F/experiment.py:73–77. The old seven-candidate trainer records it at F/vendor/train_exploratory_candidates.py:129. Counts refer to a single cloned target model, not source+target combined. AdamW receives exactly parameters with `requires_grad=True` at line 49. Its weight decay is therefore not applied to excluded shared parameters. LayerNorm has no moving batch statistics and no dropout appears in these networks. Shared affine blocks can still output different activations when upstream adapted blocks change; frozen weights do not mean every shared activation is constant.

For the zero-target-label reference, reported trainable count zero means **no target updates**, not that all cached source parameter flags were reset to False. Inference uses eval/no_grad. It is an accounting convention, not a changed source architecture or discarded source-training cost.

## Suspected issues and verdicts

| Suspicion | Code location | Audit result |
|---|---|---|
| Mask variation causes count variation | calibration.py:156–179; experiment.py:50–77 | Expected; exact arithmetic demonstrated |
| Double-counting source and target parameters | experiment.py:47,76–77 | No: count only cloned target model |
| Incorrect flags / stale masks | adapt.py:13–28 | Every call first freezes all parameters, enables requested blocks and head |
| Optimizer mismatch | trainer.py:49 | No mismatch in tested masks; identity equality asserted |
| Architecture changes with mask | multiview_mlp.py:26–60 | No structural mutation; total constant 8,033 |
| Cross-fold target state leakage | experiment.py:23–35,47 | Source-only cache + deepcopy; independent-state tests pass |
| Count measured before freezing | experiment.py:58–77 | Recorded after freezing and fit |
| Invalid geometry triggers full network | calibration.py:164–167 | Opposite: invalid geometry abstains to SHARE |
| Full network can never be selected | calibration.py:168–179 | Incorrect expectation: all seven may legitimately satisfy ADAPT |
| Outer labels used for selection | experiment.py:48–57,63–67 | Fit-only selector; flipped outer/calibration outcomes leave weights, trace, mask and predictions identical in synthetic tests |

## Independent checks

`audit_core.logical_reference` implements the scalar logical rule independently; production agreed on 1,000 random (R,upper) pairs and 18 boundary pairs, each tested at three p values (3,054 decisions). NumPy signed-retention point estimates agree to 12 places on ordinary/reversed/degraded fixtures. An explicit pairwise-kernel and partition reference agrees on MMD and permutation p. These finite tests do not establish general statistical validity of the selector or absence of every numerical defect.

All 128 masks were tested for parameter arithmetic, disjoint source/clone parameter identities, optimizer membership and bitwise shared-module preservation after an AdamW update. Repeated adaptation with an intervening different mask reproduced predictions and left cached source state unchanged. Unknown module keys and non-boolean mask flags fail closed; incomplete masks intentionally default unspecified blocks to SHARE.

**No demonstrated specification violation or production patch.** The selector may still make scientifically unhelpful choices from noisy small samples. That question requires future authorized paired evidence, not changing the implementation merely because counts are surprising.
