# Frozen predicate review

`results/hrs_elsa_final_count_feasibility_20261105/count_engine.py`, `interview()` lines43–52:

```python
if value == 11 and proxy == (2 if w == 1 else 0): return 'personal'
if value in (13,23,25,27) or proxy == 1: return 'proxy'
if value in (21,26): return 'partial'
if value == 24: return 'institutional'
```

Then the death-label and unknown branches apply. Each scalar is first checked against the exact wave dictionary. Thus a wave-inappropriate code is rejected before these branches. Proxy fallback precedes partial/institutional/death interpretation. A direct proxy outcome with a proxy-no flag still decodes proxy but is explicitly ambiguous in the status diagnostic.

`validate_people()`, lines238–256, validates all historical visits, not merely W4/W6 baselines and W7/W9 closings. At255–256:

```python
if kind in ('personal','partial','proxy','institutional'):
    need(code(p['participation'][str(w)]) == 1,
         'PARTICIPATION_INTERVIEW_CONFLICT')
```

`run_counts.py` wraps this as `ELIGIBILITY_PROCESSING_PARTICIPATION_INTERVIEW_CONFLICT`. Both explicit0 and missing fail equality to1. Invalid participation normally fails the earlier domain check. `askpx=1` can make an otherwise ambiguous/nonresponse outcome enter the proxy branch; valid marginal codes do not prove their joint legitimacy.

The public response specification supports inclusion of full/partial personal/proxy/institutional interviews in `inwW`. No public evidence establishes that all fallback cases should be treated as completed interviews, or that a contradictory/missing harmonized flag should be overridden. **No eligibility-changing defect is demonstrated.** The earlier observability-only proposal separates missing from zero issue codes without accepting new records. It is not a recovered counter.

`review_logic.classify_cell()` is a reference to the **existing diagnostic categories**, tested against unchanged copies of its public pure classifier/decoder in `tests/reference/`. It does not decode clinical rows, change the frozen predicate, or infer causes. The review tool consumes only existing aggregate classifications. Unknown unsupported aggregate keys, totals, waves or linkage validation fail closed.

Historical source and public-code fingerprints are preserved in `references/PUBLIC_CONTRACT.json`; they are not rewritten to accept an installed mismatch. A different genuine historical release needs a separately supported review, not a manually substituted expected hash.
