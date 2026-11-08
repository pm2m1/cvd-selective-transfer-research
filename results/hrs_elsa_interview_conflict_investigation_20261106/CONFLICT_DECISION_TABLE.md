# Public conflict decision table

The table describes the exact frozen decoder and its validation consequence. `PASS` below means only “this target check does not reject”; other source/schema/date/history/eligibility checks can still reject or exclude. No row is a claim about actual private observations.

| Core row / decoded kind | Harmonized `inwW` | Frozen result | Is a negative endpoint established? | Proposed observability result |
|---|---|---|---|---|
| Completed personal, correct proxy-no |1|Pass this check|No; independent history/list/branch/timing proof still required|Same |
| Completed personal |0|`PARTICIPATION_INTERVIEW_CONFLICT`|No|Same |
| Completed personal |missing / tagged missing|Same conflict code|No|`PARTICIPATION_INTERVIEW_STATUS_UNRESOLVED`, still reject |
| Partial, explicit proxy, or completed institutional |1|Pass this check; nonpersonal baseline excluded|No personal negative proof|Same |
| Partial, proxy or institutional |0|Conflict|No|Same |
| Partial, proxy or institutional |missing|Original conflict|No|Unresolved code, still reject |
| No Core row for person-wave |0|No visit to test; documented missed wave can support a later interval reference|Never a fabricated missing-wave negative|Same |
| No Core row |1|No target conflict; missing Core / unverified history or follow-up handled downstream|No|Same |
| Core outcome missing, DK/refusal/inapplicable; proxy absent/non-yes |0/1/missing|Usually unknown; no target check|No|Same |
| Core outcome missing or nonresponse but proxy=yes |0|Proxy fallback, then conflict|No; joint source meaning unresolved|Same |
| Same proxy-fallback case |missing|Original conflict|No|Unresolved code, still reject |
| Known noncontact/refusal/ineligible outcome, no proxy=yes |0|Unknown; no target check|No|Same |
| Documented death outcome, no proxy=yes |0|Death status; no target check|Censored without earlier qualifying event, never event-free by default|Same |
| Documented death outcome, proxy=yes |0|Proxy fallback shadows death, then conflict|No; needs cross-field review|Same |
| Any otherwise responding kind |invalid `inwW` such as −1/−8/−9/2|Earlier `PARTICIPATION_CODE_INVALID`|No|Same earlier error |
| Invalid Core code for this wave |any|Earlier `CODE_OUTSIDE_OFFICIAL_DOMAIN`|No|Same |

Missing participation is an allowed **unavailable** representation in the normalized input schema. That does not establish that it is an expected joint value with a completed Core interview in this actual release. Likewise individually documented Core labels do not prove every combination with a proxy flag is legitimate. These distinctions prevent manufacturing a real-data cause from synthetic values.

## Wave-specific decision inputs

| Waves | Outcome | Proxy flag | Proxy-no code | Relevant limits |
|---|---|---|---|---|
|1|`indoc`|`askpx1`|2|Mapped outcome domain contains 11/13/21/23, not later administrative/institutional codes |
|2|`w2indout`|`askpx1`|0|Separate outcome domain; institutional nonresponse 71 is not completed institutional interview |
|3|`w3indout`|`askpx`|0|Institutional outcomes begin; this dictionary includes partial institutional codes 26/27 |
|4|`w4indout`|`askpx`|0|Selected EUL dictionary domain is narrower: 11/13/21/23/24/25 plus specified missing labels |
|5|`w5indout`|`askpx`|0|Its domain includes 26/27; not copied into W4 |
|6–7|`w6indout` / `w7indout`|`askpx`|0|Individual missing/nonresponse/institutional/death labels; no automatic personal certification |
|8|`w8indout`|`askpx`|0|Additional documented negative missing/error codes apply only within this dictionary |
|9|`w9indout`|`askpx`|0|Broad SPSS user-missing metadata is not a substitute for Stata code-domain interpretation |

Core dictionary code 24 means an institutional interview in person, not the protocol's completed non-institutional personal baseline; the frozen decoder deliberately keeps it separate. Status 25 maps to proxy. Status 71 and other unproductive institutional states are not status 24. No “Exit” record is converted to a personal interview.

## Remedy decision

| Finding from a future authorized status-only diagnostic | Minimum defensible response | What is not permitted |
|---|---|---|
| Known flag zero + clearly responding Core outcome | Establish whether revisions/source products genuinely disagree; keep fail closed pending evidence | Overwrite harmonized flag or choose whichever raises eligibility |
| Missing flag + responding Core outcome | Explicitly adjudicate whether documented Core evidence may replace that flag, including **all** history/reference implications | Change `==1` to `!=0` or assume missing means interviewed |
| Proxy fallback from unknown/nonresponse outcome | Establish documented joint-field precedence; preserve unresolved state until resolved | Assume all proxy flags represent completed interviews, or drop the flag silently |
| A proven public mapping/implementation specification violation | Minimal separately versioned correction and targeted regression | Patch the installed or consumed release |
| Genuine inconsistent person-wave | Retain global rejection, or prospectively amend a transparent exclusion/quarantine policy with private accounting | Delete the problematic visit and let its gap imply disease absence |

The present evidence supports only the error-code split. It does not select an empirical remedy from this table.
