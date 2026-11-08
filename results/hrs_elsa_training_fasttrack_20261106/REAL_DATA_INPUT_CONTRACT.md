# Real-data input contract — prospective canonical interface

This is an engineering interface for a future independently permitted export. **No validated HRS→ELSA training dataset currently exists.** The public package does not infer raw variable mappings, repair clinical histories, derive eligible participants, or extract rows from registered source files. Its real-data adapter accepts only a separately reviewed canonical input. A synthetically valid bundle is not a scientifically accepted bundle.

## Scientific identity required before an export

The intended source is HRS baseline 2012 with its documented later-wave report ascertainment. The primary target window is ELSA W6→W9; W4→W7 is a separately reported comparator, not additional independent participants. Retain the exact component histories, unknown/disputed states, interview rules, timing, exclusions and qualified source lineage from the adopted versioned endpoint contract.

The current HRS MI negative route is a **screening-assumed-negative sensitivity**. It must never be relabelled strict directly observed absence. The source/target report endpoints are not clinically identical. Any real use of this input contract must have an explicit independently reviewed, appropriately limited source-specific sensitivity research claim; the package does not adopt a strict cross-country incidence endpoint. The canonical metadata identifies:

- source endpoint: `HRS_SCREENING_ASSUMED_NEGATIVE_SENSITIVITY_ONLY`;
- target endpoint: `ELSA_PERSONAL_FIRST_QUALIFYING_SURVEY_REPORT`.

The unresolved ELSA interview/participation conflict, actual eligible-event support, baseline feature timing and HRS source sufficiency remain blockers. The completed private status diagnostic is evidence to review locally, not an adopted resolution. Merely changing an endpoint string or gate value cannot establish the needed scientific facts.

## Feature matrix

Each role's `__x` is an unencoded numeric matrix in exactly this order:

| Column | Role | Canonical meaning |
|---:|---|---|
|0|`age`|Baseline age in years under a documented topcoding policy |
|1|`sex`|The explicit source-to-target canonical category in the feature contract |
|2|`sbp`|Comparable, eligible baseline systolic blood pressure, mmHg |
|3|`dbp`|Comparable, eligible baseline diastolic blood pressure, mmHg |
|4|`bmi`|Comparable, eligible baseline BMI, kg/m² |
|5|`smoking`|Explicit canonical never/former/current coding, not raw country codes |
|6|`diabetes`|Baseline reported diabetes under a verified baseline history rule |
|7|`bp_treatment`|Documented comparable baseline blood-pressure treatment indicator |

Exact source variables, category codes, transformations, topcoding and remaining conditions are in `HRS_ELSA_FEATURE_CONTRACT.md` and `FEATURE_HARMONIZATION_MATRIX.csv`. Education, socioeconomic measures, alcohol, physical activity and laboratory measures are not implicitly added. A feature's raw availability does not establish comparable timing or measurement.

In particular, an ELSA age code denoting the 90-plus disclosure group is censored/topcoded information, not an exact age or automatically ordinary missingness. Do not replace it with 90 or NaN for routine imputation without an adopted cross-cohort age-topcoding policy. This is part of the feature/scientific gate, not a parser repair.

Use numeric NaN only for genuine predictor-cell missingness after its reason has been classified under the reviewed export. Do not pass raw Stata tags, −1/−8/−9 codes, object arrays, infinities or unknown categorical meanings as model values. No diagnosis outcome is imputed. Preprocessing statistics are fitted on source training only, then frozen; validation, calibration and test data cannot alter fills, scaling or feature definitions.

### Measurement eligibility is distinct from missing values

For every partition, `__availability` is a boolean `(N,8)` matrix attesting to the reviewed baseline construct/timing eligibility of each cell. All supplied cells must be eligible under this contract. A genuine missing response within an eligible measurement pathway can be NaN and treated by the prespecified predictor-missingness method. An absent examination, post-baseline measurement, unresolved chronological overlap, structurally unavailable construct or unverified history is **not** repaired by setting a flag or imputing a number. Such people/cells require an upstream documented decision and cannot silently enter the model input.

The boolean array is a bound export record, not self-validating proof. The independent reviewer must establish the underlying evidence. A new landmark, topcoding rule, feature substitution or eligibility population needs an explicit versioned scientific decision rather than a loader workaround.

## Development NPZ — exactly six roles

The development bundle contains only these roles:

| Role | Permitted use |
|---|---|
|`source_train`|Fit source preprocessing, source models and source representation statistics |
|`source_stop`|Source checkpoint stopping only |
|`target_fit`|Target adaptation/module selection; outcome-blind prespecified label subsets |
|`target_stop`|Target early stopping only |
|`target_calibration`|Training-side probability/threshold calibration, when support is sufficient |
|`target_validation`|Development model comparison/selection; no optimizer updates |

For each role, exactly four arrays are required:

| Suffix | Shape/type | Rule |
|---|---|---|
|`__x`|`(N,8)`, numeric|Fixed feature order; finite observed cells or approved NaN predictor missingness |
|`__y`|`(N,)`, binary 0/1|Only adequately ascertained outcomes; unknown/disputed/censored states do not become zero |
|`__ids`|`(N,)`, Unicode string array|Unique internal `HRS_`/`ELSA_`-namespaced pseudonyms; never predictors or public output |
|`__availability`|`(N,8)`, boolean|Verified construct/timing eligibility; unsupported cells reject |

Example key: `target_fit__x`. There are 24 expected development arrays. Unexpected roles/fields, especially any `target_test` array, must reject. Loading must use `allow_pickle=False`. Empty partitions, incompatible feature order, duplicate memberships, invalid labels and mismatched shapes cannot be silently repaired. The exact code validation is authoritative; do not rename fields to bypass it.

## Held-out test — physically separate

The test is a separate bundle with `target_test__x`, `target_test__y`, `target_test__ids`, and `target_test__availability`. It is not a member of the development NPZ and is not opened or hashed during development. The independent export/partition review must establish disjoint membership before any modeling. The final evaluation operation checks its own bound input against the frozen model's permitted-use history.

Previously examined observations, old target-validation participants, overlapping baseline windows, repeated waves and earlier examined MHAS participants cannot become an untouched HRS/ELSA test by renaming the role. Source/target identities must be namespaced so equal numeric IDs from different studies do not cause accidental collisions. No participant may cross fitting, stopping, calibration, selection or evaluation roles. Dates or later-wave information must not leak through predictors or membership decisions.

## Private manifest and readiness evidence

The private input manifest has schema `hrs-elsa-canonical-baseline-v1`, `synthetic_only: false`, the exact bundle `data_sha256`, `partition_method: FROZEN_OUTCOME_BLIND_HASH`, the exact `feature_names` list, `source_endpoint`, `target_endpoint`, and a `roles` mapping containing exactly the roles in its bundle. Every role records `n`, `positive`, and `membership_sha256`. The membership digest is SHA256 of the sorted Unicode ID tokens joined with a single newline, without a trailing newline, encoded as UTF-8. These digests are private and must not be pasted into AI. The configuration separately binds the bundle/manifest and reviewed export evidence. Membership fingerprints document exact assignments; aggregate row counts alone do not prove the right people. The upstream exporter must preserve an immutable source snapshot and outcome-blind partition policy. It must not redraw splits until sufficient events appear or enrich the held-out test to inflate AP.

The real execution configuration also references a private reviewed readiness record and its required integrity evidence. These must establish, rather than merely assert:

1. adopted ELSA conflict resolution and compatible versioned count/source rules;
2. completed, scientifically accepted count/feature/feasibility evidence for the chosen window;
3. HRS source endpoint and source-training sufficiency, with sensitivity limits explicit;
4. verified feature harmonization, topcoding, missingness and temporal eligibility;
5. independent participant membership and prior-use/nonoverlap review;
6. independently applicable provider/institutional permission for a distinct export and modeling operation.

### Exact readiness record

The record schema is `hrs-elsa-independent-readiness-v1`; use `configs/readiness.UNADOPTED.template.json`. Its source/target endpoint strings must match the constants above, and `approved_manifest_sha256` must equal the particular execution config's `manifest.sha256`. Evaluation therefore needs readiness bound to its separate test manifest; development readiness is not silently reused for a different export.

All eight gates must have genuinely established supporting evidence before they are recorded true:

- `elsa_conflict_resolution_adopted`;
- `fresh_count_acceptance`;
- `hrs_source_event_support_accepted`;
- `source_specific_sensitivity_claim_adopted`;
- `feature_harmonization_and_timing_accepted`;
- `precision_and_untouched_test_design_accepted`;
- `independent_export_scope_established`;
- `provider_and_institutional_scope_confirmed`.

The exact `evidence` keys are `elsa_resolution`, `fresh_counts`, `hrs_endpoint_and_support`, `statistical_feasibility`, `harmonization_and_export`, and `independent_membership`. Each is an explicit private `{path, sha256}` descriptor of the actual independently reviewed record. The preflight verifies these metadata bindings; it does not perform the scientific judgment or issue approval. All gates in the distributed template are false and the approved-manifest pin is unset.

### Exact operation configuration

Use `configs/development.template.json` or `configs/evaluation.template.json`, both schema `hrs-elsa-fasttrack-local-operation-v1`, mode `independent_local_only`. The common fields are `schema`, `mode`, `phase`, `source_use_review`, `protocol_sha256`, `data`, `manifest`, `readiness`, and `device`; evaluation additionally requires `artifact` and `freeze`. Every file descriptor is an explicit `{path, sha256}` binding. Preserve the template's protocol fingerprint. The phase is a JSON field, not a CLI `--phase` flag.

Only after independently applicable scope for the distinct operation is established may `source_use_review` record `INDEPENDENTLY_ESTABLISHED_FOR_THIS_NEW_OPERATION`. This is not software-issued permission. No accepted readiness evidence or populated clinical manifest is created by this public task. Hashes bind existing records; they do not grant permission, prove external provenance, or manufacture scientific acceptance. Do not copy an old authorization into a new purpose or invent a new approved record merely to satisfy a parser.

## Encoded views and target-label use

Raw input remains eight roles. The source-training preprocessor derives 18 numeric model columns in five views with dimensions `(4,4,2,4,4)`: source-standardized continuous roles, three-column smoking encoding, retained binary roles, and eight missingness indicators. This is not the historical model's original feature width or claimed parameter count. No target role fits preprocessing.

The active target-fitting budget is 100 outcome-blind selected fitting labels. Target stopping, calibration and model-selection labels are separately consumed and reported; they are not free additions to a claim of “100 total target labels.” Budgets 40/100/200 are prospective registered fitting capacities, not completed real learning curves. Source maximum epochs are 30 and target maximum epochs 20 with BCE stopping; target epoch-zero checkpoints are eligible in this new implementation, while source epoch zero is not. The small synthetic demonstration uses its own reduced 5/4-epoch configuration and does not establish the longer real protocol's empirical behavior.

Probability calibration uses the dedicated target-calibration role only and requires at least ten observations in each class for positive-slope Platt fitting. F1 threshold selection requires at least five per class; unsupported calibration or thresholding is explicitly unavailable. Fixed 0.50 metrics remain reported. These are prospective engineering rules, not a guarantee of useful clinical sensitivity. Model selection uses raw development AP. Held-out evaluation reports all seven preregistered methods with the primary raw-AP contrast selective minus full fine-tuning; it cannot select a winner or threshold from test outcomes.

## Output and handoff boundary

All actual NPZ arrays, IDs, manifests, fingerprints, checkpoints, model objects, predictions, labels, learning curves and detailed reports stay in the independently controlled private environment. Public discussion uses only applicable disclosure-cleared aggregates or static operational acknowledgments. Do not upload a bundle, manifest, checkpoint or private error context to Codex, ChatGPT, GitHub or an external cloud service.

No raw-source extraction operation is provided while the scientific/source rules remain unresolved. Once the upstream decisions and export are legitimately established, the configuration-driven training adapter can validate and consume the canonical files under a new independent authorization. Creating this interface does not itself authorize or demonstrate real HRS→ELSA training.

## Exact window and integrity-reading notes

Manifests also require `source_design: HRS_2012_2018_SOURCE_SPECIFIC_REPORT` and `target_design: W6_W9` or `W4_W7`. The frozen model window must match its test manifest. Hash-threshold role allocation is stable for a shared person across windows; do not switch a person between test and fitting roles in a comparator. Matrix integrity validation reads labels for the supplied fitting pool before selecting the outcome-blind fitting subset. Reports separately list those integrity-read rows and labels actually used in fitting/stopping/calibration/selection; there is no claim of zero label access outside the selected fitting subset.
