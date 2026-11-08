# Baseline predictor availability contract

The automatic adapter counts eight-role availability; it never exports modeling rows or trains a model. `measurement_sources` must supply the two exact nurse products, in addition to original Core history and Harmonized H. With neither those sources nor reviewed feature metadata, availability/partition results remain NOT_COMPUTED. Unknown features do not invalidate an already known outcome; count outcome and feature losses separately.

| Role | Automatic source and transformation | Timing / limitation |
|---|---|---|
| Age | Original Core4/6 `indager`, years | At baseline; age topcoding retained, not an invented birth date |
| Sex | Core4/6 `indsex`:1→0,2→1 | Recorded binary survey coding; does not use cross-wave `ragender` backfill |
| SBP | Nurse4/6 `sysval` (case-normalized), mmHg | Published valid mean; actual `visyear/vismon` bounds required |
| DBP | Nurse4/6 `diaval`, mmHg | Same examination timing requirement |
| BMI | Nurse4/6 `bmival`, kg/m² | Published valid derived BMI includes estimated weights above130kg; do not claim all are directly measured |
| Smoking | H `r4/r6smokev` and `r4/r6smoken`:0/0→never0,1/0→former1,1/1→current2 | Ever-history fed forward from earlier answers; a missing response is not zero.0/1 contradiction stays missing with private QC count |
| Diabetes | Original personal-history reconstruction through baseline; verified absent→0, prior personal positive/confirmation→1, otherwise missing | Does not use harmonized `rWdiabe` values revised by later disputes. Diabetes is a predictor, not an MI/stroke exclusion |
| BP treatment | H `r4/r6rxhibp`,0/1, missing unavailable | Harmonized medication phenotype includes treatment/prevention and screened zeros; not a directly observed disease-negative endpoint |

The official H manual explains smoking construction at printed pp.411–413; medication construction at pp.293–294 says reports remain as reported after later diagnosis disputes; diagnosis variables may be retrospectively revised (pp.238–240). Physical-measure definitions and estimated weight are discussed at pp.938–939. See [Harmonized ELSA H](https://doc.ukdataservice.ac.uk/doc/5050/mrdoc/pdf/5050_gateway_harmonized_elsa_h_2002-2023.pdf). Exact nurse labels and source-member fingerprints are in `official_variable_map.json`; the official nurse dictionary names are `wave_4_nurse_data` and `wave_6_elsa_nurse_data_v2`.

Age, sex, reported diabetes and questionnaire-derived smoking/medication are considered computable by the end of the baseline Core interview. Examination values require the latest possible measurement/availability date to precede the earliest possible baseline date. Same-month uncertainty is not silently accepted. Missing nurse attendance, invalid values, uncertain timing and later visits are separately nonqualifying. This may materially limit measured-feature cohorts even if disease-history eligibility expands; no event count has been computed to assess that effect.

An optional `elsa-baseline-feature-evidence-v1` JSON may supply an independently reviewed alternative reconstruction, source hashes and derivation-code fingerprint. It cannot silently alter the eight roles, units, categorical domains or temporal checks. Actual later-wave measurements are rejected. A new nurse-based landmark requires new eligibility and an amended protocol, not a permission checkbox. Publication should distinguish this prospective availability recipe from the previous frozen cohort's feature construction; equivalence is not inferred from matching role names.

Each feature object has exactly `value`, `unit`, `source_wave`, `context`, `measured_lower`, `measured_upper`, `available_upper`. Context is `same_core_interview` for questionnaire roles or `dated_examination` for measurements. Units are years/category/mmHg/kg/m2 as defined in code. The reviewed evidence file has top-level schema, `baseline_only_reviewed`, `mapping_sha256`, `source_bindings`, `derivation_source_sha256`, and `people`. Each person has `idauniq`, `features` keyed by baseline4/6, and `prior_model_use` (`no`, `yes`, `unknown`). These are protected records, created/reviewed only in the independently permitted environment, never uploaded or populated here. Never default `prior_model_use` to no.
