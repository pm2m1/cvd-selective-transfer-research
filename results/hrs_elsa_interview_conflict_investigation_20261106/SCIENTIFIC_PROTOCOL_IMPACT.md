# Scientific protocol and implementation impact

## Proposed change prepared here

`proposal/count_engine_observability_v1.py` is an isolated copy of the pure public engine with exactly one predicate rewritten into three statements:

```python
flag = code(p['participation'][str(w)])
need(flag is not None, 'PARTICIPATION_INTERVIEW_STATUS_UNRESOLVED')
need(flag == 1, 'PARTICIPATION_INTERVIEW_CONFLICT')
```

Its unified diff is `proposal/OBSERVABILITY_ONLY.patch`. **Do not apply that diff to the frozen or installed software.** It is an independently reviewable source proposal, not a replacement release, a registered correction, a recovery controller or a permission to retry.

### Classification

| Dimension | Impact |
|---|---|
| Scientific endpoint definition | None |
| Eligible/accepted population | None; same accepted and rejected input set |
| Disease-free history and interval reference | None |
| Missing, disputed, proxy, Exit/death/attrition handling | None |
| Feature timing / leakage / partitions / accounting | None |
| Source-product interpretation | None |
| Failure observability | **Changes:** missing participation gets an explicit unresolved-evidence code; known zero keeps the existing conflict code |
| Source/runtime/error-contract fingerprints | **Change:** a new release would need new bindings and error-contract documentation |
| Existing attempt / authorization | No reuse or modification permitted |

The proposal does **not require a change to the scientific estimand or eligibility protocol**. It does require a versioned technical/error-contract amendment if adopted and exact new release/runtime bindings. It preserves fail-closed behavior and does not solve the unknown actual source inconsistency. No failed real attempt is retroactively reclassified.

No SHARE/ADAPT model, HAALSI/MHAS experiment, source descriptor, registration manifest, reviewed count configuration, authorization, private output or frozen count file is changed by this public proposal.

## Changes not justified or adopted

1. **Core-over-harmonized precedence:** admitting Core-personal records despite zero/missing participation changes the source-evidence hierarchy. It also affects earlier-wave lifetime anchors and `reference()` choices, not merely baseline filtering. It needs release-specific documentary support and a prospective source-interpretation/protocol amendment.
2. **Unknown-state quarantine/exclusion:** replacing a global source-quality abort with per-person exclusion could be defensible under a prespecified selection policy, but changes the accepted input universe and accounting. Wave-only deletion may turn an unresolved interval into a false history absence. Preserve known positives/disputes and unverified gaps; do not infer negatives.
3. **Decoder precedence changes:** changing the `proxy==1` fallback or prioritizing explicit nonresponse/death outcomes requires a supported joint-field interpretation. Per-variable domains alone do not prove which conflicting field is authoritative. No such semantic patch is included.
4. **Restricting validation to a selected design or post-age cohort:** changes the global source-quality rule. It must not be adopted merely because the failed record might otherwise be excluded.

These would be protocol/source-interpretation decisions, not cosmetic fixes. They require evidence and synthetic impact tests before a new actual count operation could be justified. No unknown interview may become personal, no missing outcome may become negative, and a different source edition cannot be silently substituted.

## Scientific disposition

The current global consistency gate is defensible for known disagreement given the H manual's response definition. Applying it to missing participation is deliberately strict; the frozen protocol does not authorize automatic substitution. Its shared issue code overstates what is known about the data, which justifies clearer observability. There is **no demonstrated endpoint/eligibility-changing coding bug** and no basis for a larger event-count or modeling-feasibility claim.

Real counting remains blocked pending cause-specific source interpretation and a justified new release/operation. Phase 2B training remains outside scope and unauthorized by this audit.
