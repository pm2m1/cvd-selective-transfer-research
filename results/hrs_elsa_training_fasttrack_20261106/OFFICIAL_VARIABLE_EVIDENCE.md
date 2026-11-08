# Official variable evidence and public-source traceability

Public-documentation audit,6 November2026. No clinical files, private configurations, diagnostic reports, source registrations or authorization records were accessed. The feature identities below reuse public, frozen mappings; they do not re-certify a private release, authenticate publisher origin or demonstrate patient-level baseline availability.

## Source products and documentary hierarchy

| Source | Official documentation / exact use |
|---|---|
| RAND HRS Longitudinal2022 **V1 actually selected in the historical project** | [V1 manual](https://hrsdata.isr.umich.edu/sites/default/files/documentation/other/1758643082/randhrs1992_2022v1.pdf); public source contract names `r11agey_e`, `ragender`, `r11diabe`, `r11smokev`, `r11smoken`. The [current official product page](https://hrsdata.isr.umich.edu/data-products/rand-hrs-longitudinal-file-2022) describes V2, October2026. It must not silently replace the frozen V1 edition. |
| Gateway Harmonized HRS **D** | [Official product page](https://hrsdata.isr.umich.edu/data-products/gateway-harmonized-hrs) confirms D, August2023 and its supplementary relationship to RAND. [D manual](https://hrsdata.isr.umich.edu/sites/default/files/documentation/other/1694551378/Harmonized%20HRS%20D%201992-2021.pdf). Public project mappings identify `r11systo`, `r11diasto`, `r11mbmi`, `r11rxhibp`; physical timing evidence additionally uses `inw11pm`, `r11bpcomp`. |
| Harmonized ELSA **H** | [H manual](https://doc.ukdataservice.ac.uk/doc/5050/mrdoc/pdf/5050_gateway_harmonized_elsa_h_2002-2023.pdf), versionH September2025. Printed p30 response-indicator definition; pp293–294 medication construction; pp411–413 smoking; pp238–240 diagnosis/dispute revisions; pp915–916 BP; pp938–939 BMI. The actual selected UKDS container edition is not established merely from this manual. |
| Original ELSA Core4/6 and Nurse4/6 | [Official UKDS dictionary ZIP](https://doc.ukdataservice.ac.uk/doc/5050/mrdoc/ukda_data_dictionaries.zip), public documentation SHA256 `32161c5b497f5ae3df03cc81169b018548967e429eaaf0299bfd6b0f1c1082ae`. Exact public field/value dictionaries are preserved in `results/hrs_elsa_final_count_feasibility_20261105/official_variable_map.json`. |
| Original ELSA health routing | [W6 questionnaire](https://doc.ukdataservice.ac.uk/doc/5050/mrdoc/pdf/5050_elsa_wave_6_documentation.pdf), printed pp57–62; [W4 questionnaire](https://doc.ukdataservice.ac.uk/doc/5050/mrdoc/pdf/5050_wave_4_documentation.pdf), Health routing; [W7 questionnaire](https://doc.ukdataservice.ac.uk/doc/5050/mrdoc/pdf/5050_elsa_wave_7_questionnaires.pdf), pp60–69; [W9 questionnaire](https://doc.ukdataservice.ac.uk/doc/5050/mrdoc/pdf/5050_elsa_wave_9_interviewer_questionnaire.pdf), Health pp54–59. Questionnaire appearance alone does not prove released-variable presence. |

The two HRS product pages were newly accessible on6 November2026. Direct PDF parsing for the HRS D and RAND V1 manuals failed in this public audit; no false claim of a fresh complete PDF review is made. Their field evidence is reused from the existing public source specification and earlier documented review. No current-release replacement, account/login, download of microdata or protected metadata lookup occurred.

## Exact ELSA codebook details

The following are directly established from the existing frozen **public dictionary map**, not inferred from similarly named Harmonized variables:

| Product / variable | Position / label / relevant codes |
|---|---|
| Core4 `indager` | Position6518, definitive age collapsed at90+; −7 means age90+ collapsed, −1 inapplicable, −8 DK, −9 refusal. It is not permissible to manufacture exact age90. |
| Core6 `indager` | Position6029; same disclosure-collapse distinction. |
| Core4 `indsex` | Position6519, definitive reported sex;1male,2female,−1/−8/−9 unavailable. |
| Core6 `indsex` | Position6030, same documented category domain. |
| Nurse4 `sysval` / `diaval` | Positions35/36, valid mean systolic/diastolic BP. −1 indicates an invalid or incomplete set of readings. |
| Nurse6 `SYSVAL` / `DIAVAL` | Positions393/394, corresponding valid mean labels. Original case is retained in evidence; reader normalization must reject case collisions. |
| Nurse4 `bmival`; Nurse6 `BMIVAL` | Positions153/404, valid BMI including estimated>130kg; −1 inapplicable. |
| Nurse4 `vismon` / `visyear` | Positions7/8; actual nurse-visit month/year. |
| Nurse6 `vismon` / `visyear` | Positions415/416; month/year, not fabricated exact measurement day. |

For diabetes, the original Core merged-list and feed-forward fields are wave-specific. `hedimdi` alone does not certify lifetime absence. The final-count `history()`/`observation()` logic reconstructs prior personal evidence, confirms/disputes prior conditions and stops at baseline. Its evidence may remain unknown. The harmonized `rWdiabe` can reflect subsequent dispute handling and is deliberately not used by the newest automatic ELSA baseline-feature adapter. A disease-history uncertainty is not solved by feature imputation.

## Existing public implementation references

- `results/hrs_elsa_final_count_feasibility_20261105/baseline_features.py`: exact W4/W6 eight-role transformation, coherent smoking pairs, baseline-only Core diabetes proof, original Core age/sex and nurse measures/date bounds.
- `results/hrs_elsa_final_count_feasibility_20261105/BASELINE_PREDICTOR_CONTRACT.md`: measured-feature semantics, structural missingness, source timing and inability to infer complete-case/partition support from the ten history sources alone.
- `results/hrs_elsa_final_count_feasibility_20261105/official_variable_map.json`: field-specific dictionary domains, archived spellings, positions, section hashes, nurse products and missing metadata.
- `phase2/phase2a_6_wave_based_audit/stage_c_multifield_v3_config.template.json`: exact older HRS/ELSA proposed raw feature columns. It is a public template, not an activation approval or the newly resolved condition-specific count recipe.
- `phase2/phase2a_6_wave_based_audit/stage_c_v3_configuration.py`: prior field-validity and physical completion assembly. HRS `inw11pm` and `r11bpcomp` have distinct meanings; a BP completion flag does not establish every feature or exact time.
- `results/hrs_elsa_cvd_feasibility_20261105/downloaded_source_audit.py`: historical public column-selection contract only. It is not rerun. Its screened population and missingness operations are not cohort/endpoint validation.
- `phase2/phase2b_public/PHASE2B_REVISED_PROTOCOL_CANDIDATE_V1.md`: distinguishes predictor imputation, measurement landmarks, source-specific endpoints and independent evaluation prerequisites; real modeling remains unauthorized by that public candidate.

## Endpoint and inference limitations retained

HRS follow-up heart-attack zeros from `r12/r13/r14hrtatt` can include screening assumptions; the [HRS D health manual](https://hrsdata.isr.umich.edu/sites/default/files/documentation/other/1694551378/Harmonized%20HRS%20D%201992-2021.pdf), previously reviewed printed p224, is the public basis. Strict directly observed HRS MI negatives cannot be activated without supporting original/equivalent route evidence. Definite RAND interval stroke requires paired `rWstrok`/`rWstrokq`, adopted Q=2 rule; TIA/uncertain/disputed states stay separate. Exact HRS original-question locators include [2012 Core NC036/NC257/NC040/NC053](https://hrs.isr.umich.edu/sites/default/files/meta/2012/core/codebook/h12c_r.htm).

ELSA outcomes are first qualifying personal survey reports after verified baseline absence and documented follow-up, not adjudicated clinical onset. A valid numerical feature matrix cannot homogenize nonidentical ascertainment across countries. The completed private status diagnostic has not been read here; its successful execution is not a scientific resolution. No private event count, feasibility verdict or causal explanation is disclosed or invented.

## Readiness conclusion

Field identities and key ELSA labels are documented; **the real modeling feature contract remains PARTIAL in both cohorts**. Remaining dependencies are actual baseline availability/provenance, resolved interview-history interpretation, appropriately timed measured features, source-specific outcome evidence, event/precision sufficiency and independent authorized creation of validated inputs. Unsupported optional predictors are omitted instead of being filled from assumptions.
