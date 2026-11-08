# Status classification contract V1

## Frozen evidence and input scope

This new diagnostic reproduces the original `num`, `code`, `scalar` and `interview` functions exactly; `CountError` and `need` are also copied exactly. Whole original source and individual function fingerprints are recorded in `references/PUBLIC_EVIDENCE.json`. The public mapping is an exact copy of the original mapping, not a revised codebook. Source registration's qualified local, unauthenticated origin and unresolved edition remain unchanged.

Registered inputs are exactly Harmonized H and Core Waves 1–9. The manifest descriptor must bind the original `elsa-private-source-registration-v1` output and match the public registration code/protocol identities. Each source descriptor must equal its registered materialized-file descriptor, including actual member-content SHA256 and exact product basename. Optional nurse registrations may exist in that manifest but are neither requested nor read by this diagnostic.

The selected data columns are:

| Source | Columns |
|---|---|
| Harmonized H | `idauniq`, `inw1`–`inw9` |
| Core W1 | `idauniq`, `indoc`, `askpx1` |
| Core W2 | `idauniq`, `w2indout`, `askpx1` |
| Core W3–9 | `idauniq`, matching `wWindout`, `askpx` |

Stata metadata/variable names must be read to select columns. Whole file bytes are hashed before and after reading; that is a protected operation even though no unselected health column is decoded. No MI/stroke/history, predictor, nurse, interview-date, diagnosis-date or model column is requested. Exact numeric positive integral IDAUNIQ below `2**53` links records internally. Strings, invalid/missing IDs and duplicate keys are never fuzzy-matched, filled or silently used.

## Participation states

| Category | Meaning under the exact frozen normalizer |
|---|---|
| `PARTICIPATION_ONE` | Normalizes exactly to integer 1 |
| `PARTICIPATION_ZERO` | Normalizes exactly to integer 0 |
| `PARTICIPATION_MISSING` | Normalizes to unavailable: Python None, Stata plain/tagged missing or nonfinite numeric representation |
| `PARTICIPATION_OTHER_OR_INVALID` | Other numeric code, noninteger or invalid categorical representation |

The original normalizer treats booleans as unavailable; that behavior is preserved and separately flagged by a `BOOLEAN_REPRESENTATION` raw-state token, not silently recoded. Allowed numeric strings preserve their original accepted meaning and have a distinct raw-state token. Stata `.`, `.a`–`.z` remain distinguishable in private frequency summaries. Invalid arbitrary text is represented by a fixed token, never copied. Bounded numeric status-code tokens preserve values within ±999; larger numbers receive an out-of-range token to avoid accidentally emitting an identifier misfiled as a status.

Missing is never converted to zero or one. Domain-invalid statuses are summarized diagnostically, then cause the operation to fail after the protected diagnostic is retained. They cannot yield a successful compatibility conclusion.

## Core state and decoder basis

The frozen decoder requires outcome 11 plus explicit proxy-no for `personal`. It next tests explicit proxy outcomes **or** proxy=yes, then partial, institutional and death-labelled outcomes, otherwise unknown. Domain validation precedes decoding. Consequently a proxy=yes fallback can shadow an absent, nonresponse or death outcome.

| Output | Meaning |
|---|---|
| `CORE_PERSONAL_INTERVIEW` | Exact frozen personal predicate |
| `CORE_PARTIAL_INTERVIEW` | Frozen partial classification |
| `CORE_PROXY_INTERVIEW` | Explicit proxy outcome or original proxy-flag fallback; basis separately recorded |
| `CORE_INSTITUTIONAL_INTERVIEW` | Completed institutional in-person outcome 24 under frozen decoding |
| `CORE_DEATH_STATUS_NO_INTERVIEW_EVIDENCE` | Frozen death classification; no clinical death date inferred |
| `NO_CORE_INTERVIEW_EVIDENCE` | Known nonresponse/administrative outcome with no responding decoder route |
| `CORE_AMBIGUOUS` | Missing/uncertain outcome, unresolved personal evidence or incompatible domain |
| `NO_CORE_RECORD` | No exact linked Core row for that harmonized person-wave |

`decoder_basis` explicitly records `ASKPX_FALLBACK`, `EXPLICIT_PROXY_FLAG_DISAGREEMENT`, `OUTCOME_BASED`, domain error or absent row. Fallback means proxy=yes without an explicit proxy outcome (13/23/25/27). Explicit proxy outcome with an explicit proxy-no answer is separately ambiguous. Neither condition proves a completed eligible personal interview.

Per-wave domains are not interchangeable. W1 uses proxy-no=2; W2 onward uses 0. W4's selected EUL outcome domain does not admit W3/W5 codes 26/27. Institutional nonresponse 71 is not interview code 24. The [H manual, Section A “Wave Status: Response Indicator”, printed p.30](https://doc.ukdataservice.ac.uk/doc/5050/mrdoc/pdf/5050_gateway_harmonized_elsa_h_2002-2023.pdf) includes full/partial, personal/proxy/institutional responses in `inwW`. It states W6–10 use Core outcomes; W1–5 may use index outcomes. Printed pp.32–33 describe source variables and separate interview/mortality status. The [UKDS dictionaries](https://doc.ukdataservice.ac.uk/doc/5050/mrdoc/ukda_data_dictionaries.zip) provide the exact wave domains already pinned in the frozen mapping.

## Combination interpretation

| Evidence | Label | Limits |
|---|---|---|
| Explicit responding kind + participation one | `CONSISTENT` | Participation consistency only; no disease-free, event-free or baseline eligibility conclusion |
| Explicit responding kind + participation zero | `KNOWN_DISAGREEMENT` | Recorded evidence disagrees; this does not prove which source or mechanism is wrong |
| Responding kind + missing/invalid participation | `INSUFFICIENT_EVIDENCE` | Do not fill the flag or assume eligibility |
| Proxy fallback, or explicit proxy outcome versus proxy-no | `UNRESOLVED_DECODER_AMBIGUITY` | Unless invalid participation dominates as insufficient evidence; fallback basis always retained |
| No Core row + zero participation | `CONSISTENT` | Consistent with no response; does not supply a negative disease report |
| No Core row + one/missing participation | `INSUFFICIENT_EVIDENCE` | Missing evidence/linkage, not proof of nonresponse |
| Known nonresponse/death outcome + zero participation | `CONSISTENT` | No clinical nonevent or exact death date is assigned |
| Known nonresponse/death outcome + participation one | `UNRESOLVED_DECODER_AMBIGUITY` | Revision/mortality/routing interpretation requires review |
| Missing/unknown Core status without fallback | `INSUFFICIENT_EVIDENCE` | Never interpreted as an interview or disease absence |

The separate `frozen_target_check` records whether the original *local predicate* would reject known zero or missing participation, pass this check, or fail earlier domain validation. That is not a replay of overall clinical eligibility. The diagnostic evaluates all combinations without stopping at the first target conflict; the frozen count engine fails fast.

## Linkage and failure behavior

Missing, invalid and duplicate linkage counts are private per source. If any occur, `input_validation.private.json` is retained and the operation fails before a joined matrix is produced. No invalid/duplicate key is used for a completed diagnostic. Missing Core rows and valid Core keys outside the H universe are counted separately; unmatched Core subjects are not added to the original universe. These describe coverage, not automatic linkage causality.

Missing required columns, case collisions, corrupt/unsupported files and source/parser warnings fail with static issue identifiers. Unknown code domains produce a protected status report followed by `STATUS_DOMAIN_INCOMPATIBILITY_DIAGNOSTIC_PRESERVED`; the attempt is failed and consumed, not a successful scientific assessment.

`first_detected_target_conflict` stores only wave and categories. Scan order is H file row order then ascending wave. It writes no row number, ID or key and is not proof of the discarded historical first error. The old validator checks all participation domains before each person's visits and additional schema/death invariants; those can change which error appears first. Actual historical-input equivalence must be established independently, not inferred from this output.

## Unit of the diagnostic matrix

Each linked harmonized person-wave contributes once to its wave matrix. Totals across waves repeat people and must not be presented as independent participants, clinical event counts or independent validation samples. Core-only unmatched records remain separate linkage summaries.
