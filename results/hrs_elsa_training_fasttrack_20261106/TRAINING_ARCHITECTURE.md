# Implemented training architecture

The new implementation reuses byte-identical public `MultiViewRiskNet`, module freezing/snapshots, representation types, MMD/class-geometry calibration and logical mask rules. `PRESERVATION_BINDINGS.json` identifies their original source bytes. No original real-data loader, checkpoint, prediction or locked-test executor is imported.

## Data path

Separate canonical development NPZ → exact key/membership/endpoint/window validation → source-training median/mode fills and scaling → five views → source models → target fitting/stopping → dedicated calibration → development AP selection → frozen artifact → separately authorized test NPZ → fixed evaluation.

The NPZ key list is checked before any array is dereferenced. An unexpected target-test key in a development file rejects without reading its payload. The optimizer receives only source train/stop and target fit/stop arrays; calibration and model-selection arrays are not passed to the model-training adapter. The test file is absent from development configuration. Real preflight opens only bound evidence/manifest metadata and checks locations; array bytes are hashed/read only after a separately authorized attempt is consumed.

## Encoders and dimensions

Eight raw roles become 18 encoded columns: source-standardized age/SBP/DBP/BMI, binary sex/diabetes/BP treatment, three smoking indicators, and eight predictor-missingness indicators. Views are background4, haemodynamic4, metabolic2, behaviour4, comorbidity/medication4. No missing clinical outcome, structural absence or unresolved measurement timing is imputed.

Each view encoder is Linear(input,16) → ReLU → LayerNorm16. Concatenated 80 features pass Linear(80,64) → ReLU → LayerNorm64, then Linear(64,32) → ReLU → LayerNorm32, then Linear(32,1). Sigmoid converts logits to probabilities. This configuration has **8,017 parameters**, including33 head parameters; it is not the historical19-input/8,033-parameter HAALSI/MHAS model. Parameter counts are calculated in every run.

## Seven methods

| Identifier | Actual implementation | Target weight updates |
|---|---|---|
|`source_logistic`|L2 logistic regression, C1, maximum2000 iterations|None |
|`source_regularized`|Elastic-net logistic-loss SGD, alpha0.001, l1_ratio0.15, maximum2000 iterations|None |
|`source_boosting`|Histogram gradient boosting, learning rate0.05, seven leaves, L2=1,100 iterations|None |
|`source_dmvmat`|Five-view network pretrained on HRS-role inputs|None |
|`head`|Exact source-network clone; internal modules shared/frozen|Head only |
|`full`|Exact source-network clone|All weights |
|`selective`|Exact source-network clone; frozen calibrated-logical selector|Head plus selected modules |

Classical models use the same transformed columns and source training rows. They do not receive target-fitting labels. Their secondary target-calibrated operating point does consume target calibration labels and must not be described as a zero-target-label clinical decision rule.

## SHARE/ADAPT

Seven selectable modules are the five encoders and two fusion blocks. Selector evidence uses source stopping representations and target fitting representations/labels only. MMD is a detached selection statistic, not an optimizer alignment loss. The preserved logical rules require valid class geometry; invalid/weak/uncertain geometry abstains to SHARE. Source-anchored signed retention,199 domain permutations and199 geometry bootstraps are used in the prospective real plan. The tiny demonstration uses9/19 to check execution, not statistical power. A source/target class shortage never silently triggers full adaptation.

`requires_grad` is set explicitly; the optimizer parameter identities must equal the trainable tensor identities. Frozen-module tensors are compared byte-exactly after fitting. Every adaptation starts from the same preserved source checkpoint, whose hash is checked unchanged. The selected mask determines the reported trainable count; variable counts across conditions are expected.

## Checkpoint and runtime behavior

AdamW learning rate0.001, weight decay0.0001, batch64, BCE and patience5 are fixed; there is no invented scheduler. Source maximum30 epochs, target maximum20. Source selection begins after an update. Target selection includes epoch zero using the same stopping BCE and actual initial weights. This isolated prospective choice follows the earlier audit; its benefit on real cohorts is unproven. No test outcome chooses an epoch.

CPU is the default with deterministic PyTorch algorithms, one Torch thread and fixed seeds. Explicit MPS requests fail when unavailable; CPU is not silently substituted. No MPS empirical equivalence is claimed without execution. Runtime/algorithm bindings are frozen and checked again before any test bundle is read.

Artifacts are private in real operation: source/adapted weights, trusted digest-bound joblib models/preprocessor/operating points, curves, development predictions and a freeze registration. No model is uploaded. Joblib must never load an arbitrary untrusted external artifact.
