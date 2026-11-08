# Count flow and private output interpretation

Every window has the same ordered baseline construction. Counts are unique persons. All source and result fingerprints are retained privately. No real counts appear in this preparation package.

| Stage / loss | Exact condition | Scientific purpose |
|---|---|---|
| Input population | Harmonized H unique numeric IDAUNIQ keys, exact linkage to registered Core histories | Declared release universe; unmatched Core keys reported privately |
| Baseline participants | `inw4` or `inw6`=1 | Actual selected-wave response, not lifetime disease absence |
| Missing Core | No linked baseline Core row | Original baseline evidence unavailable |
| Unknown age | Core `indager` missing/negative | Cannot verify population definition |
| Under50 | Known age<50 | Prespecified population exclusion |
| Nonpersonal baseline | Outcome/proxy not qualifying completed personal | Retain separate proxy/partial/institutional/unknown categories |
| Prior MI first | Personal MI report or valid historical confirmation through baseline, no unresolved dispute | First-component incident question; not clinically adjudicated absence/presence |
| Prior stroke after MI | Stroke-positive among those not already removed for MI | Ordered attribution; marginal MI/stroke counts also provided because overlap exists |
| Unknown/disputed history | Either component not verified absent | Missing life anchor, reference gap, list/branch uncertainty, disputed/unconfirmed prior record or proxy-only evidence |
| Verified baseline-free | Both personal history proofs verified | Only this group enters composite follow-up |

The identity `baseline participants = missing Core + unknown age + under50 + nonpersonal + prior MI first + prior stroke after MI + unknown history + verified baseline-free` is checked. Marginal prior MI/stroke and history-state joint cells must not be added as disjoint exclusions.

Within each baseline-free population and each timing policy:

- MI and stroke have separate observed report, observed nonevent, disputed, history/timing-unknown, proxy/gap/horizon-unknown and censored-death states.
- Composite positive is the union of qualifying component reports, counted once even if both occur. Composite nonevent requires both components observed negative. One qualifying component can establish a composite positive while the other's follow-up is uncertain; the baseline history of both must already qualify.
- Known reports before later death/attrition are retained according to the prespecified time proof. Death-status codes do not supply exact death dates. Withdrawal versus other absence remains unknown without additional source evidence; no inferred withdrawal count is manufactured.
- `ascertained_binary_outcomes = unique composite incident reports + observed composite nonevents`. The remainder stays unknown/disputed/censored. Both-component completeness is also reported separately from a classifiable composite.
- Observability diagnostic marginals show date, nonpersonal, list/branch, historical-first-appearance and reference/gap limitations among unresolved component outcomes. They overlap and are not independent added losses.
- Eight-role feature missingness/timing and complete/timely binary-outcome counts are kept separate from endpoint ascertainment. Missing inputs produce NOT_COMPUTED or partial-evidence status, not a fabricated observed zero.
- Outcome-blind role scenarios count events/nonevents in disjoint adaptation/stopping/calibration/evaluation groups. Same person has the same role across windows; two windows are correlated. Untouched-evaluation counts include only independently reviewed prior-use=no and are lower bounds on documented support, not proof of external validation.

## New private files after authorized execution

1. `final_counts.private.json`: two windows, ordered flows, component/history marginals and joint tables, timing-policy outcomes, predictor availability, partition scenarios and source bindings.
2. `precision_assessment.private.json`: explicit assumption-based planning calculations; no fitted model scores.
3. `scientific_status.private.json`: counts written, scientific/disclosure assessment still required; training and independent-test flags remain false.
4. `runtime_bindings.private.json`: exact Python/pandas/NumPy versions and new code/protocol/map hashes.
5. `result_integrity.private.json`: SHA256 of completed count/planning/status/runtime files.
6. The unchanged local runtime's consumed start record, completion receipt and private log.

`private_aggregate_output.schema.json` describes the count artifact. Read a missing sparse diagnostic cell as zero only within an explicitly computed count map. A null or NOT_COMPUTED field is unavailable, never zero. Detailed histories, raw values, tokens, IDs and person assignments are not written. Counts and data-conditioned conclusions remain protected until disclosure review, including risks from differences of totals and small joint cells. A static completion acknowledgment means files were created, not that a feasible study was established.
