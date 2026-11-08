# Final evidence review

AI-authored public methodological assessment; no independent scientific approval is claimed. Current real training is BLOCKED. Protected diagnostic execution is acknowledged from the operator's account, not inspected or independently verified here.

## What the frozen implementation actually checks

In the original `results/hrs_elsa_final_count_feasibility_20261105/count_engine.py`, `interview()` lines 43–52 decodes outcome and proxy fields. `validate_people()` lines 238–256 validates every linked historical visit before `analyze()` builds either cohort. At lines 255–256, a decoded personal, partial, proxy or institutional interview requires `code(participation[wave]) == 1`. Both zero and missing participation violate this condition. Invalid participation codes fail an earlier invariant. `run_counts.py` prefixes the error with `ELIGIBILITY_PROCESSING_`.

The proxy branch accepts outcomes 13/23/25/27 **or** proxy flag 1. It precedes partial, institutional and death-label branches. Thus an invented missing/nonresponse outcome paired with `askpx=1` can decode as proxy and trigger the conflict. Valid marginal codes do not prove that their joint combination is a legitimate survey response. This reproduction does not identify the real failing record.

## Documentary conclusion

The [Harmonized ELSA H manual](https://doc.ukdataservice.ac.uk/doc/5050/mrdoc/pdf/5050_gateway_harmonized_elsa_h_2002-2023.pdf), printed pp30–32, defines participation across full/partial personal/proxy/institutional responses. Earlier waves may use Index outcomes; W6–10 use Core outcomes. Nursing and self-completion flags are separate. Institutions enter from W3. Therefore a personal-only interpretation of `inwW` would be wrong; the existing broad responding-state check itself is defensible.

The named [Core dictionaries](https://doc.ukdataservice.ac.uk/doc/5050/mrdoc/ukda_data_dictionaries.zip) establish wave-specific outcome and proxy domains. W1 proxy-no is 2, later proxy-no is 0; some institutional/partial codes exist only in particular waves. An institution-related nonresponse code is not necessarily a completed institutional interview. Household proxy-routing instructions in the [W7 questionnaire](https://doc.ukdataservice.ac.uk/doc/5050/mrdoc/pdf/5050_elsa_wave_7_questionnaires.pdf), household interview checks, establish routing, not a universal completion override.

No official joint rule found in this review establishes that `askpx=1` must override a contradictory completion outcome. Nor does the H manual guarantee equality between separately released, potentially revised Core and harmonized files linked locally. The selected dictionary names authenticate public documentation identity only, not the original distributor's private archive edition.

## Decision table

| Evidence | Established now | Smallest defensible consequence |
|---|---|---|
| Completed-interview Core code with participation 1 | Documented consistency; reproduced synthetically | Preserve existing decoding and eligibility rules |
| Completed-interview Core code with participation 0 | Recorded disagreement would be real if this combination is in the protected diagnostic | Review linkage, edition and derivation; no automatic precedence |
| Completed-interview Core code with participation missing | Insufficient participation evidence, distinguishable from explicit zero | Keep uncertainty; distinguishing issue codes is observability only |
| Proxy inferred solely from `askpx` with ambiguous/nonresponse outcome | Public branch is reproducible | Joint semantics and actual prevalence remain private review questions |
| Invalid linkage, duplicate keys, wrong release | Cannot be inferred from the issue code | Preserve source/uniqueness checks; repair inputs only if independently demonstrated |
| Unknown/death/missed wave with no proxy evidence | Not automatically a responding interview | Never turn it into a disease nonevent or delete a follow-up interval |

## What is not resolved

The protected diagnostic must establish which branches actually occurred, in which waves and matched source products, and whether a documented cause explains **all** combinations. A global validation failure can arise outside the eventual baseline/follow-up subset, because all histories are validated first. Restricting validation to a favorable window would itself need justification.

The prior investigation already supplies an observability-only patch separating missing from zero issue codes. It leaves the acceptance set unchanged and cannot recover counts. Recreating it or rerunning the diagnostic would add no scientific evidence.

No eligibility-changing bug is demonstrated. No active corrected-count release is justified yet. HRS strict MI-negative support also remains unresolved; the available source-specific construction is sensitivity-only. These are separate blockers from event sufficiency and real-input timing, which software tests cannot settle.
