# Final two-design ELSA count feasibility package

**CONDITIONAL GO for count-only feasibility preparation. Actual new counts are unavailable; no model training is authorized.**

Read `SCIENTIFIC_PROTOCOL.md`, `OFFICIAL_VARIABLE_DICTIONARY.md`, `BASELINE_PREDICTOR_CONTRACT.md`, `ELIGIBILITY_FLOW_AND_OUTPUTS.md`, `STATISTICAL_FEASIBILITY.md` and `FEASIBILITY_DECISION.md`. `official_variable_map.json` and `VARIABLE_DICTIONARY.csv` give the factual release-specific mappings. All required public source is in this directory; older experiments are not runtime dependencies.

The code reads only registered ELSA inputs during a **new separately authorized independent-local operation**. `count_engine.py` and `baseline_features.py` are pure logic; `read_release.py` is the guarded selected-column adapter; `run_counts.py` uses the unchanged one-attempt independent-operator runtime. `precision.py` is assumption-based planning, not model scoring. No cohort engine or model training is called.

Normal installation/execution is in `ACCESS_AND_LOCAL_EXECUTION.md`. The public ZIP excludes downloaded documentation caches, clinical files, populated configs and authorization records. `verify_public.py` verifies/installs only enumerated public bytes. The shipped config is deliberately unpopulated/unapproved. No real input or private artifact has been accessed here.

Synthetic verification:

```sh
python3 -B -m pytest -q -p no:cacheprovider tests
python3 -B run_counts.py --synthetic-demo --output /ABSOLUTE/NEW/INVENTED_DEMO_OUTPUT
```

Synthetic demo rejects an external config/authorization and writes invented aggregates only. A public completion/testing result is not clinical evidence. All new real counts and data-conditioned verdicts must remain private pending disclosure review. See `VALIDATION_REPORT.md` for actual test results and artifact hashes.
