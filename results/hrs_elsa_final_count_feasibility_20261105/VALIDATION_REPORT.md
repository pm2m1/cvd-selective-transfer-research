# Public synthetic validation and release record

Date:5 November2026. **96 targeted synthetic tests passed, zero failures.** The release receipt `RELEASE_VALIDATION.json` alongside the ZIP records the exact extraction/retest results and final ZIP SHA256. No clinical operation has been run; test totals are software evidence only.

## Executed synthetic coverage

Command from the repository:

```sh
.venv/bin/python -B -m pytest -q -p no:cacheprovider results/hrs_elsa_final_count_feasibility_20261105/tests
```

The independent package command is the same pytest invocation with `tests` as its relative target. Tested runtime:Python3.12.14, pandas3.0.6, NumPy2.5.3, pytest9.1.1.

| Area | Actual invented-fixture checks |
|---|---|
| Earlier and continuing histories | Lifetime anchors at Waves1/3/4/6, interval linking, missed-wave coverage versus undocumented gaps, no reset after positive/disputed history |
| Exact mapping | W1 proxy no=2, W4 EUL `w4indout`, W9 absent `hedacmi`, positional feed-forward diagnosis in another slot, wave-specific domains |
| Disease absence | Hypertension/diabetes/identified non-endpoint diagnoses allowed; screening/derived zeros never supply a negative; missing, tagged missing and contradictory none/positive lists do not qualify |
| Outcomes | MI/stroke separated, repeated-report deduplication, union rather than sum, prior component exclusions, proxy/death/attrition, uncertain history, known early report before later missing/death |
| Timing | Approximately-six-year closing window versus strict calendar target, report straddling target, absent/outside-horizon dates, no later-wave outcome in the earlier design, unrecognized policy rejected |
| Features | Units, missing/invalid BP, later-wave and post-baseline nurse rejection, raw baseline diabetes rather than future harmonized revisions, smoking contradiction, non-endpoint diabetes retained |
| Accounting | Unique exact IDs, no duplicate person/wave, complete baseline/outcome partitions, zero-eligible case, feature loss distinguished from outcome missingness, unavailable partition support not mislabeled observed zero |
| Reader end-to-end | **Twelve completely invented Stata tables**:H-like response history, nine Core-like files and two nurse-like files. Selected-column loading, source hashes, both design counts and automatic feature availability tested. No clinical input used |
| Security/provenance | Agent guard before config/data access, config/package readiness before authorization prompt, public help without input access, exact product identity, changed source/map hashes, missing whole field, incompatible W9 header, old-purpose authorization rejection, safe errors |
| One attempt/privacy | Exclusive output,0700/0600 permissions, permanent interruption record, no output reuse, no IDs in aggregates, no unreviewed exposure treated unused |
| Public package | Hash verification, exclusive new installation, refusal to overwrite, changed installed mapping rejected, manifest path traversal rejected |
| Statistical planning | Single-class unavailability, assumed sensitivity/specificity requirements, AUROC approximation, finite-population both-class probability; no actual model performance claim |

## Documentation and integrity checks

The exact official dictionary ZIP SHA256 matches the prior public fingerprint; its entries were checked for absence of participant-data formats. Four requested questionnaires (W4/6/7/9) and Harmonized H manual were downloaded from official public URLs and text-extracted. Public documentary hashes are in `PUBLIC_DOCUMENTATION_MANIFEST.json`; there are22 cached documentation files. No clinical archive was downloaded.

`VARIABLE_DICTIONARY.csv` has460 rows:441 present variable sections plus19 specifically recorded checked-absence entries. Names, codes and section hashes were cross-checked against `official_variable_map.json`. Config template hashes match the final protocol/map, while scope and clinical descriptors remain deliberately unset. Python AST/JSON parsing and public CSV consistency passed.

All **9/9** explicitly fingerprinted prior public evidence/source files in `PRIOR_PUBLIC_BINDINGS.json` remained byte-identical. No old audit, protocol, source hash, attempt, receipt, model or frozen report was modified. This is a scoped preservation check, not a claim to have inspected every repository artifact. No restricted output or authorization receipt was opened. The reused independent runtime remains SHA256 `d1227f629eaaf727c3ca41195c7ab1dccd1da3a15040168752b1f2cbbc3b2e02`.

The synthetic CLI demo ran with invented observations and no external config/authorization. It emitted labeled invented aggregates; no IDs appeared. Reusing its invented output destination rejected. The public release contains only curated source, documentation/mappings, templates and tests, not the documentation cache, any `.dta`/`.sav`/prediction/checkpoint data, a populated clinical config or actual authorization. The exact release ZIP is independently extracted and its manifest/tests/demo checked; the final machine receipt records outcomes.

## Scientific and access limitations

These tests cannot establish real eligibility, case counts, provider/institutional permission, source-country comparability or independent evaluation precision. Public documentary identity does not authenticate the clinical archive distributor/edition. Actual clinical field presence and registered source-file hashes have not been verified through Codex. Unknown participant histories remain unknown; no claim that every unknown person is ineligible in truth is made.

The first qualifying survey-report endpoint is not exact clinical onset. Several questionnaire date fields are absent from named release dictionaries; no Wave9 field was manufactured. No source/target model was trained, no historical cohort procedure/private reviewer was rerun and no formal modeling NO_GO flag changed. The future local operation must have fresh scope, authorization and outputs, with full private disclosure review.

**Public decision: CONDITIONAL GO for a separately authorized count-only feasibility assessment. Actual event adequacy remains unestablished.**
