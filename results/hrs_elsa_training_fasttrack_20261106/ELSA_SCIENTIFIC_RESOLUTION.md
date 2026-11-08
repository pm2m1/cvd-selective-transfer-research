# ELSA scientific-processing resolution: public decision

**Decision: UNRESOLVED for real count/training execution. No eligibility-changing correction is justified by currently public evidence.** This is an AI-authored methodological decision under researcher delegation, not a claim of independent scientific approval. The user reports successful private status-diagnostic execution; neither its findings nor its scientific adoption were disclosed or inspected here.

## Established evidence

| Question | Public documentary/code evidence | Synthetic evidence | Private-dependent finding / permitted decision |
|---|---|---|---|
| What does `inwW` mean? | Harmonized ELSA H manual, Section A, **Wave Status: Response Indicator, printed p.30**: response includes full/partial personal, proxy and institutional interviewing. It is not a personal-only or disease-negative flag. | Consistent completed, partial, proxy and institutional states with `inwW=1` pass the source-consistency predicate. | Which types actually disagree in the registered sources remains private. Do not redefine INW because a subgroup is inconvenient. |
| Do waves differ? | Same manual pp.30–33: W6–10 indicators use wave-specific Core outcomes; W1–5 can use index outcomes. Institutional interviewing begins W3. W1 proxy-no is2; W2 onward uses0. Selected W4 EUL domain is narrower than W3/W5. | Frozen mapping rejects W1 proxy-no0 and W4 outcome26 rather than importing another wave's domain. | Index/Core revision differences are possible explanations, not established causes. Registered bytes do not establish semantic consistency. |
| What raises the issue? | Frozen `count_engine.py:255–256`: responding decoded kind implies `code(inwW)==1`. `run_counts.py:30–32` adds `ELIGIBILITY_PROCESSING_`. | Known zero and missing `.a` both produce the old conflict. Global validation precedes every waterfall. | Actual zero-versus-missing, wave, decoder route and number affected require the completed protected diagnostic's review. |
| What does `askpx` do? | `interview():43–52` uses explicit proxy outcomes **or** proxy=yes before partial/institutional/death branches. | A missing/nonresponse/death outcome with proxy=yes follows the proxy fallback. Separate scalar validity does not prove the joint combination legitimate. | Do not infer that fallback proves an eligible interview. Joint-field semantics and revision context need review. |
| Could missingness legitimately explain it? | Frozen normalizer preserves missing/tagged-missing participation as unavailable; dictionary labels distinguish inapplicable, refusal and DK from a response. | Missing INW plus responding Core triggers the same old issue; missing Core rows do not enter that predicate. | Missing evidence is not a known contradictory zero, but the existing protocol does not authorize replacing it with one. |
| Is linkage proven wrong? | Original reader uses exact positive integral numeric IDAUNIQ, rejects duplicates and selects Core visits by exact key. | Status diagnostic tests invalid/duplicated/unmatched linkage and does no fuzzy matching. | A mismatch matrix alone does not establish mislinkage; exact source identity and recorded key coverage must be assessed locally. |
| Is a coding bug established? | No public specification violation admitting/rejecting a demonstrably legitimate joint source state has been established. The core implication agrees with the manual's broad response definition. | The error code is ambiguous, and proxy precedence is a reproducible diagnostic lead. Neither proves the privately rejected combination is valid. | Preserve the blocker. Category A observability is supported; category B/C is conditional on evidence. |

Primary documentation already inspected in the public project: [H manual, version H September2025](https://doc.ukdataservice.ac.uk/doc/5050/mrdoc/pdf/5050_gateway_harmonized_elsa_h_2002-2023.pdf), [official UKDS dictionary archive](https://doc.ukdataservice.ac.uk/doc/5050/mrdoc/ukda_data_dictionaries.zip). Exact public field domains and section fingerprints are retained in `hrs_elsa_final_count_feasibility_20261105/official_variable_map.json`; the new status package copies the frozen mapping and exact decoder functions. No new product edition is inferred.

## Remedy adjudication

| Remedy | Category | Present disposition |
|---|---|---|
| Preserve global rejection | Existing source-quality policy | Retain until the conflict has a documented resolution. It is stricter than medical eligibility, but changing it is substantive. |
| Separate missing participation from known zero in error identifiers | A — observability only | Supported. An isolated proposal already exists; it changes no acceptance/eligibility decision and cannot make the failed run succeed. Do not duplicate or install it here. |
| Correct a demonstrated mapping/implementation error | B | Conditional. Requires an exact public-code/official-definition violation plus regression case and private source equivalence. No such correction is adopted. |
| Quarantine entire unresolved participants with explicit accounting | C | Possible prospective proposal, not adopted. It changes the accepted input universe and selection. It cannot be justified merely to obtain counts. |
| Remove an unresolved wave and retain the rest of history | C | Not allowed without an evidence-backed history/reference amendment; deleting a wave can make an unobserved interval appear event-free. |
| Prefer Core over harmonized flags, or prefer nonresponse/death over a proxy fallback | C unless an objective implementation specification violation is demonstrated | Needs a documented, wave-specific joint-field hierarchy. It affects earlier lifetime anchors, interval reference, death and follow-up, not just one baseline filter. |

## Minimum remaining scientific determination

An independently permitted reviewer must use the **existing completed diagnostic**, not launch another one merely for a new acknowledgment. Establish: (1) zero/missing/invalid/fallback composition; (2) joint field legitimacy under the exact registered release; (3) source/linkage equivalence; (4) a fixed remedy classified A/B/C; and (5) its effects on baseline absence, reference intervals, missingness, attrition and accounting. Keep detailed empirical conclusions private unless disclosure cleared. Then freeze a separate resolution/correction/amendment and its evidence before a fresh count operation. The old attempt stays permanently consumed.

Training engineering can proceed synthetically while this gate remains unresolved. Neither synthetic training success nor successful private diagnostic artifact creation resolves scientific eligibility.
