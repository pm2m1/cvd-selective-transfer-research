# ELSA participation/interview conflict investigation

Date: 6 November 2026. **Public failure mechanism confirmed; actual private trigger unresolved. No eligibility-changing software defect established.**

This is an AI-authored public code investigation with invented fixtures. It does not certify scientific acceptance, inspect the failed operation, or authorize another operation. The user reports `FAILED_NO_RETRY`, issue `ELIGIBILITY_PROCESSING_PARTICIPATION_INTERVIEW_CONFLICT`, an existing consumed marker/completion receipt, and no final count file. Those are supplied observations, not private artifacts independently inspected here.

## 1. Exact mechanism and call chain

All line locators below refer to the pinned **original** public release in `../hrs_elsa_final_count_feasibility_20261105/`.

1. `local_execution.py:51–74`: independent-local/authorization checks, output binding and exclusive output creation. `exclusive_output():27–39` creates the consumed start marker before processing; a raised `Rejected` preserves its stable code in `completion.private.json`, status `FAILED_NO_RETRY`. Existing output is refused at line 29.
2. `run_counts.py:20–28`: checks independent execution, verifies the public release and scientific configuration, loads the mapping/protocol, and calls `read_release.load_people()`. Reader `CountError`s receive the **different** `SOURCE_VALIDATION_` prefix.
3. `read_release.py:39–55`: selects source columns, enforces exact numeric ID linkage and unique person keys, and normalizes column case. `plain():21–27` turns pandas Stata tagged missings into strings such as `.a` and nonfinite floats into `None`. Required/forbidden whole-column checks are at lines 47–49.
4. `read_release.py:63–72,101–106`: reads Harmonized `inw1`–`inw9`; a person's Core visit is added only when that exact key exists in the corresponding Core table. The schema uses `participation[str(w)] = rawh.get('inw'+str(w))`, with `indoc`/`wWindout` and `askpx1`/`askpx` in each visit's raw fields. Optional feature derivation may occur before return. Lines 117–119 recheck all input file bindings before returning.
5. `run_counts.py:29` calls `analyze()`. `count_engine.py:258–259` calls `validate_people()` **before** either design's waterfall or endpoint calculations.
6. `count_engine.py:245–246` first requires exactly nine participation keys and codes restricted to `0`, `1` or missing. Each sorted, unique Core visit is decoded at lines 247–254.
7. **The actual rejecting predicate, `count_engine.py:255–256`:**

```python
if kind in ('personal','partial','proxy','institutional'):
    need(code(p['participation'][str(w)]) == 1,
         'PARTICIPATION_INTERVIEW_CONFLICT')
```

8. `need():11–12` raises `CountError('PARTICIPATION_INTERVIEW_CONFLICT')`. `run_counts.py:30–32` wraps it as `Rejected('ELIGIBILITY_PROCESSING_'+str(e))`. Therefore the reported full issue is exactly reproduced.
9. `run_counts.py:33–49` writes results only after `analyze()` returns. This branch cannot write `final_counts.private.json`. The outer runtime records the failed consumed attempt and prints only the generic public acknowledgment (`local_execution.py:85–87`).

The code strongly locates the failed **condition**, assuming the supplied receipt came from this bound release. It does not identify a person, wave, design, scalar, dtype or rejected decoder route. None of those are added to this exception or completion receipt. No claim is made that a nonexistent detailed trace can be recovered.

### Global scope matters

Validation scans every harmonized-universe person's supplied Core visits across Waves 1–9. It is not limited to age-eligible people, baseline Waves 4/6, or a selected design's follow-up. A conflict at Wave 8/9 can abort the combined operation before the Wave 4→7 waterfall, even though that later visit cannot contribute to that design's endpoint. A conflict in a person who would later be excluded for age also aborts. This is a global source-consistency gate, not a medical exclusion criterion or an accounting failure. Multiple conflicts stop at the first encountered person/ordered visit; the code is not an inventory of all discrepancies.

## 2. Exact decoder inputs and precedence

`count_engine.interview():43–52` uses **wave-specific dictionary validation** through `scalar():26–32`, then:

| Priority | Condition | Decoded kind |
|---|---|---|
|1 | outcome `11` AND proxy answer `2` in W1, `0` in W2–9 | personal |
|2 | outcome in `13,23,25,27` **OR proxy answer `1`** | proxy |
|3 | outcome in `21,26` | partial |
|4 | outcome `24` | institutional |
|5 | documented outcome label contains “died” | death_status |
|6 | otherwise | unknown |

These conditions run only after the actual wave's code-domain checks. For example W4 has no accepted `26`/`27` domain; copying those W3/W5 codes into W4 fails earlier with `CODE_OUTSIDE_OFFICIAL_DOMAIN`. A missing outcome with `askpx=1` still follows the proxy fallback. A known refusal/noncontact/death code plus `askpx=1` also follows that fallback before the later death check. Those combinations reproduce the target issue with `inwW=0`, but **their joint legitimacy is not established by independent scalar label dictionaries**. They could reflect routing, stale flags, genuine Core cross-field inconsistency or source-version disagreement. No actual such combination has been observed here.

This precedence is a public, reproducible diagnostic lead, not proof of a real-record coding bug. A broader decoder correction would need a documented cross-field hierarchy and impact analysis, including history references and death handling; it is not silently implemented here.

## 3. What documentation establishes

The cached [Harmonized ELSA H manual](https://doc.ukdataservice.ac.uk/doc/5050/mrdoc/pdf/5050_gateway_harmonized_elsa_h_2002-2023.pdf), version H September 2025, **Section A, “Wave Status: Response Indicator”, printed p.30** (local text lines 1261–1316), defines `inwW` as response to that wave. Its construction includes full and partial personal, proxy and institutional interviews. It does **not** define `inwW` as personal-only, complete-only, disease-negative, or equivalent to `inwWsc`/`inwWn`.

The same page says W6–10 indicators use wave-specific Core outcomes because the index does not contain those waves. Earlier indicators may use index outcomes. Institutions were not surveyed in W1/W2; institutional interviewing begins W3. **Printed p.32**, “Original ELSA Variables Used”, identifies W6–9 outcome fields; earlier index names such as `outindw4` are not proof that the selected W4 EUL file should contain that name. **Printed p.33**, “Interview Status”, distinguishes `rWiwstat` response/mortality status and warns about later-wave index/mortality coverage. This reader uses `inwW`, not `rWiwstat`, nurse flags, self-completion flags or an Exit interview as personal data.

The exact inspected [UKDS public dictionaries](https://doc.ukdataservice.ac.uk/doc/5050/mrdoc/ukda_data_dictionaries.zip), fingerprinted in the existing mapping, establish `indoc` for W1, `wWindout` thereafter, `askpx1` for W1–2 and `askpx` thereafter. W1 proxy-no is `2`; later waves use `0`. The mapping records distinct W4 and W6/7/9 code domains. W6/7/9 institutional code `71` is not a completed institutional interview `24`; it decodes unknown with no proxy fallback. Noncontact/refusal, inapplicability and death must not become disease negatives.

The manual supports the implication “a genuinely responding Core interview should have response indicator one.” It does not prove exact acquired-release consistency or that any missing-indicator/ambiguous-proxy combination is expected in these frozen products. A source hash validates bytes, not measurement agreement. No new provenance search or participant inspection was performed.

## 4. Known versus possible causes

**Proven public facts:**

- Both known zero and missing participation produce the same original code when the decoder reports one of the four responding kinds.
- `num()/code():14–24` accepts `None`, `.`, `.a`–`.z` and nonfinite numeric values as unavailable. Numeric representations of `1` decode one. Harmonized `-1/-8/-9`, `2`, etc. fail earlier at `PARTICIPATION_CODE_INVALID`; they cannot directly produce this particular issue under the normal path.
- Missing whole columns, absent Core person-waves and missing individual scalar responses are different cases. Missing whole essential columns fail source validation; an absent visit never enters this check. A missing Core outcome/proxy with no proxy=yes fallback decodes unknown and does not trigger this condition.
- The test is one-way, not a biconditional. `inwW=1` plus absent Core can reach the baseline missing-Core exclusion or an unresolved history/follow-up, not this issue.
- Consistent proxy/partial/institutional states pass source validation but cannot certify personal disease-free or event-free status.

**Not established about the failed attempt:** whether its flag was zero or missing; whether the route was explicit respondent outcome or proxy fallback; which wave or person; how many conflicts; whether releases disagree; whether the data contain a genuine contradiction; or whether any larger valid cohort exists.

## 5. Minimal invented reproduction

Using `synthetic_fixture.person(mapping)` creates an invented completed-personal record at every wave. Set `p['participation']['6']=0`, leave `w6indout=11` and `askpx=0`, and call `validate_people([p],mapping)`: it raises the exact short conflict. Set the participation flag to `.a` instead: the **same original** short issue is raised, despite this being unresolved evidence rather than an observed zero. Use the no-input `reproduce_conflict.py` to see both cases clearly marked synthetic.

These invented examples demonstrate the failure mechanism, not the privately rejected scalar.

## 6. Resolution supported now

**No population-changing repair is justified from the receipt alone.** Retain the strict rejection. The isolated `proposal/OBSERVABILITY_ONLY.patch` splits unavailable participation into `PARTICIPATION_INTERVIEW_STATUS_UNRESOLVED` and preserves `PARTICIPATION_INTERVIEW_CONFLICT` for known zero. Every previously accepted/rejected record remains accepted/rejected respectively; no missingness becomes negative and no endpoint rule changes. This is an observability improvement, not a fix that makes this consumed attempt succeed.

The candidate is not installed, is not an active controller, has no clinical-data loader, and must not replace the frozen release. See `SCIENTIFIC_PROTOCOL_IMPACT.md` and `INDEPENDENT_LOCAL_NEXT_STEPS.md`. The smallest additional empirical step, if independently justified, is an explicit source-status metadata diagnostic, **not another full count run**.
