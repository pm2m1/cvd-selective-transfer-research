# Historical ELSA source contract audit — 5 November 2026

## Definitive finding

**The original public historical records are insufficient to authenticate the required clinical input sources.** They contain no historical clinical ZIP-container or Stata-member fingerprints. No actual source registration has been performed by this task.

This is a public engineering assessment authored by AI. It is not institutional, provider, publisher or independent-human scientific approval. Existing protocols, source snapshots and count code remain unchanged.

## What the two strings identify

`../hrs_elsa_cvd_feasibility_20261105/EXECUTED_SCREEN_SOURCE_HASHES.json` keys the strings by **Python source filename**:

| Public code identity | Recorded SHA256 | Present public-file comparison |
|---|---|---|
| `downloaded_source_audit.py` | `9cd147b4ab14d9e5dd50c91b9c12f46b9893d4e0b20515cc5bcec08d1a3b8f95` | Does not match present source |
| `target_ceiling.py` | `c9adb0866bb65ad63478a9487b24a13bdf75eec7708879d0bf1a067ec97ad034` | Matches present source |

Present `downloaded_source_audit.py` hashes to `ec6798ccbfc83f181d4977721b7159106e1ebaa351658daf46c204de1214d0af`, also recorded in that directory's public `SHA256_MANIFEST.json`. That manifest has 30 public code/documentation artifact entries and explicitly excludes participant source bytes/IDs. The differing executed-source hash cannot establish the exact implementation that ran; its reason is not established here. Both old records are preserved. Neither historical string can be relabelled as a ZIP pin, a `.dta` pin, or independent authentication. The new registrar explicitly rejects their use as archive pins.

## Original public reader contract

In the present `downloaded_source_audit.py`, `read_member()` (line 18 onward) matches the exact basename of a ZIP member and requires one match. `run()` (line 61 onward) selects exactly one local basename starting `5050stata_` and ending `.zip`. It does not preserve the full ELSA ZIP filename, container hash, member hash or download/acquisition record. `target_ceiling.py` uses the same selector and reader. These statements reconstruct the available public code, not a byte-exact reconstruction of the differently hashed historical execution.

The reader also names `randhrs1992_2022v1_STATA.zip` and `H_HRS_d_stata.zip` for HRS. Those HRS products are outside this ELSA registrar; no new HRS access is implemented.

The ELSA reader selected `gh_elsa_h.dta` and Core Waves 6–9 listed below. Its existence is evidence of the earlier selection contract, not a new inspection of archives. Core Waves 1–5 and nurse products were not selected by that reader. The old code does not establish their presence in the original download. Full ZIP member paths are unknown until independently registered.

## Exact expected products and documentary basis

The unchanged final-count `config.template.json` and `official_variable_map.json`, together with `OFFICIAL_VARIABLE_DICTIONARY.md` §Registered products, establish these exact expected basenames. They are not new observations of private files.

| Role | Required basename | Earlier reader selected it? |
|---|---|---|
| harmonized | `gh_elsa_h.dta` | Yes |
| core1 | `wave_1_core_data_v3.dta` | No |
| core2 | `wave_2_core_data_v4.dta` | No |
| core3 | `wave_3_elsa_data_v4.dta` | No |
| core4 | `wave_4_elsa_data_eul.dta` | No |
| core5 | `wave_5_elsa_data_eul.dta` | No |
| core6 | `wave_6_elsa_data_eul.dta` | Yes |
| core7 | `wave_7_elsa_data_eul.dta` | Yes |
| core8 | `wave_8_elsa_data_eul_v2.dta` | Yes |
| core9 | `wave_9_elsa_data_eul_v2.dta` | Yes |

Optional, explicitly selected together: `wave_4_nurse_data.dta`, `wave_6_elsa_nurse_data_v2.dta`. Their absence blocks requested nurse registration; it does not silently downgrade that request. Without nurses, the candidate explicitly uses `measurement_sources: null`; complete-case predictor/partition availability remains uncomputed under the existing contract.

Evidence already recorded in the public final-count documentation:

- [Official UKDS dictionary ZIP](https://doc.ukdataservice.ac.uk/doc/5050/mrdoc/ukda_data_dictionaries.zip), publicly recorded documentation SHA256 `32161c5b497f5ae3df03cc81169b018548967e429eaaf0299bfd6b0f1c1082ae`. Core dictionary names are the corresponding basename stems followed by `_ukda_data_dictionary.rtf`. This is a documentation-container fingerprint, never a clinical-data pin.
- [Harmonized ELSA H manual](https://doc.ukdataservice.ac.uk/doc/5050/mrdoc/pdf/5050_gateway_harmonized_elsa_h_2002-2023.pdf), version H, September 2025; its underlying UKDS 45th edition July 2025 does **not** prove the acquired ZIP edition.
- The public historical `DATASET_ACCESS_AUDIT.md` explicitly leaves the acquired Core edition unauthenticated. A current catalogue's 50th-edition description does not repair that gap.

These documentary findings are reused from the existing public audit; no repeated microdata search or acquisition occurred. Product H, Core `_v2`/`_v3`/`_v4` revisions, Stata file-format releases 114/118/119, and UKDS collection editions are separate concepts. The registrar accepts only `UNRESOLVED` for acquired collection edition in this version; unsupported affirmative claims stop. A future evidenced edition claim requires a separately reviewed contract extension.

## Compatibility with the frozen count engine

`read_release.py:60–72` requires the ten exact role/basename descriptors and SHA256-verified loose files. It records `claimed_archive_edition` using a default `UNRESOLVED`; it does not demand fabricated edition numbers. `read_release.py:75` permits absent measurement sources. `run_counts.py:14–16` separately binds the scientific protocol/mapping and requires its own operation-specific source-use review.

Consequently an honestly unresolved-edition, locally registered **source-complete candidate** is compatible. It is not an execution-approved configuration, a guarantee of header/field compatibility, or evidence of publisher authenticity. The new generator preserves the original `source_use_review: UNRESOLVED_NOT_AUTHORIZED`, protocol, mapping, `no_models`, and all scientific settings. It never invokes the count engine.
