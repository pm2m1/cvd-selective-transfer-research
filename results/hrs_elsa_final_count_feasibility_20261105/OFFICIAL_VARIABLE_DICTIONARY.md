# Exact official field mappings and release limits

All inspected files are publicly available documentation. The [UKDS dictionary ZIP](https://doc.ukdataservice.ac.uk/doc/5050/mrdoc/ukda_data_dictionaries.zip) was retrieved on5 November2026, SHA256 `32161c5b497f5ae3df03cc81169b018548967e429eaaf0299bfd6b0f1c1082ae`, matching the previously recorded public documentation digest. No microdata were downloaded. `official_variable_map.json` contains exact variable names, label domains, dictionary positions, member/section hashes, checked absences and SPSS missing-range metadata. `VARIABLE_DICTIONARY.csv` is its tabular rendering.

## Registered products

| Wave | Named product dictionary / required data basename | Original interview/proxy fields |
|---|---|---|
|1 | `wave_1_core_data_v3` | `indoc`, `askpx1`; **proxy no=2**, not0 |
|2 | `wave_2_core_data_v4` | `w2indout`, `askpx1`; proxy no=0 |
|3 | `wave_3_elsa_data_v4` | `w3indout`, `askpx` |
|**4** | **`wave_4_elsa_data_eul`** | **`w4indout`, `askpx`** |
|5 | `wave_5_elsa_data_eul` | `w5indout`, `askpx` |
|**6** | **`wave_6_elsa_data_eul`** | **`w6indout`, `askpx`** |
|**7** | **`wave_7_elsa_data_eul`** | **`w7indout`, `askpx`** |
|8 | `wave_8_elsa_data_eul_v2` | `w8indout`, `askpx` |
|**9** | **`wave_9_elsa_data_eul_v2`** | **`w9indout`, `askpx`** |

Data suffix is `.dta`; dictionary suffix is `_ukda_data_dictionary.rtf`. The adapter normalizes source column case only when no case collision exists. It does not substitute a similarly named v3/v4/other product. The older guide names `OUTINDW4`; the exact EUL dictionary inspected here instead names `w4indout`. This resolves the **named EUL product** mapping, not every historical Wave4 edition. The prior report/guide is preserved unchanged.

The [H manual, version H September2025](https://doc.ukdataservice.ac.uk/doc/5050/mrdoc/pdf/5050_gateway_harmonized_elsa_h_2002-2023.pdf) states underlying UKDS45th edition July2025. Its study-wide release metadata are not proof of the frozen local Core archive edition. The [current SN5050 notice](https://doc.ukdataservice.ac.uk/doc/5050/read5050.htm) describes a newer50th edition. Same-named dictionary/revision evidence is not independent authentication of local data bytes. The configuration requires independently registered source hashes; no old checksum is rewritten.

## Endpoint and branch fields

| Construct | W4 EUL | W6 EUL | W7 EUL | W9 EUL-v2 | Interpretation |
|---|---|---|---|---|---|
| Merged newly reported MI | `hedimmi` | same | same | same |1mentioned,0not mentioned;0 alone is not history absence |
| Merged stroke | `hedimst` | same | same | same |Separate from MI; no invented TIA code |
| None response | `hedim96` | same | same | same |One member of entire list; not required if another identified non-endpoint condition is selected |
| Prior diagnosis bundle | `hedawbp/an/mi/hf/hm/ar/di/st/ch/ot` | same | same |last slot `hedaw95` replaces `hedawot` |**Positional condition-code slots**, not a set of binary named disease indicators; scan all slots |
| MI confirmation | `hedacmi` | `hedacmi` | `hedacmi` |**absent** |1confirmed,2denied,3not read; missing/skip needs route proof |
| Stroke confirmation | `hedacst` | same | same |same |Historical confirmation is not an incident event |
| MI/stroke disputes | `hedanmi`, `hedanst` | same | same |same |1never,2no longer,3not previously but now,4misdiagnosed; all retained disputed in the primary proof |
| Prior-condition recheck | `hediax3`, `hediax8` where present | checked absence/presence in JSON | checked | checked |May block a negative; does not erase original positive history |
| Derived first-report wave | `hediagmi`, `hediagst` | not assumed present | not assumed present |not assumed present |Positive report-wave supports a prior-record warning;0never reported is not independently observed lifetime absence |
| Individual interview date | `iintdatm`, `iintdaty` | same |same |same |Month/year bounds, not diagnosis date |
| Baseline age/sex | `indager`, `indsex` | same | not baseline here | not baseline here |Use baseline source, not future backfill |

W1 merged condition mentions are `hedim01`–`hedim07`; W2 uses `hedim01`–`hedim08`. Codes3 and8 indicate MI and stroke,96none, with condition-specific other codes. W2 confirmation/dispute names include case variants `HeDiaC3/HeDiaN3`, `HeDiaC8/HeDiaN8`, and all `HeDiaW1`–`HeDiaW9` feed-forward slots. W3 onward use merged dummies. Code51/52 non-endpoint diagnoses do not become MI. Uncodeable/irrelevant/unspecified other cardiac responses are uncertainty, not a fabricated negative.

Most selected Core field dictionaries label −1inapplicable,−8DK,−9refusal. W4 branch fields may also label−2CAPI error. W2 documents−3/−4 feed-forward problems on specific fields. W8 attaches−2/−3/−4 missing/error labels; these never imply negative. W9's very broad SPSS user-missing range is metadata, not a Stata value-domain rule. Plain/tagged Stata missing values remain unavailable; unknown substantive codes reject. All exact per-variable labels are recorded in JSON, rather than a falsely universal missing-code list.

Completed personal is11, full proxy13, partial personal21, partial proxy23. Other documented administrative/institutional outcomes remain nonqualifying. W4 EUL's dictionary domain is narrower than W6/7/9; domain copying across waves is prohibited. Death-labelled administrative outcomes support a censored-status category, not an invented exact death date or cause.

## Questionnaire comparison and actual availability

- [W4 official questionnaire](https://doc.ukdataservice.ac.uk/doc/5050/mrdoc/pdf/5050_wave_4_documentation.pdf): Health HEDIAC/HEDIAN/HEDIAX/HEDIAA and interviewer instructions on first versus subsequent diagnoses; the PDF's dynamic textfills are incomplete in parts, so use the accompanying guide and exact variable labels together.
- [W6 v3 March2014](https://doc.ukdataservice.ac.uk/doc/5050/mrdoc/pdf/5050_elsa_wave_6_documentation.pdf), printed pp.57–62: confirmations, disputes, merged diagnosis list and conditional diagnosis timing.
- [W7 v0.1 July2015](https://doc.ukdataservice.ac.uk/doc/5050/mrdoc/pdf/5050_elsa_wave_7_questionnaires.pdf), printed pp.60–69: same core distinction and conditional MI/stroke timing/recurrent counts.
- [W9 interviewer questionnaire](https://doc.ukdataservice.ac.uk/doc/5050/mrdoc/pdf/5050_elsa_wave_9_interviewer_questionnaire.pdf), Health pp.54–59: a printed archive table lists `hedacmi`, but the named EUL-v2 dictionary omits it, consistent with H's MI dispute section (printed pp.236–240). **Questionnaire appearance does not establish released-variable presence.** The reader rejects an actual W9 header containing that incompatible field until its revision mapping is reviewed.

Questionnaires mention `heagbry`/`heagery` diagnosis year fields, but these are absent from the inspected W4/6/7/9 EUL dictionaries. Age-at-diagnosis fields are present in some waves and absent in others; neither age nor interview month becomes an exact diagnosis date. This engine does not construct clinical onset dates from those fields. Late old diagnoses and retrospective reporting remain limitations of the first-report endpoint.

The [NatCen Waves1–5 guide, Appendix7.1](https://ifs.org.uk/sites/default/files/output_url_files/waves_1_5_datasets_user_guide.pdf) explains first lifetime versus additional diagnoses, proxy differences and old diagnoses newly reported. The [Waves1–10 guide, Appendix7.1 and §§6.5–6.7](https://doc.ukdataservice.ac.uk/doc/8445/mrdoc/pdf/elsa_waves_1-10_interviewer_data_user_guide_v3.pdf) corroborates these distinctions. A derived INW response flag is not a complete-personal interview or a disease-negative response.

No unresolved definition is silently assigned a meaning. A completely missing essential source column or incompatible public code domain blocks execution; a present but unavailable individual response stays unknown. Exact clinical onset and access to a new source edition remain unresolved evidence, not code defects.
