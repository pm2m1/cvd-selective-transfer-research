# DMV-MAT epoch-zero follow-up v1

One prespecified development experiment, three paired arms: original full adaptation(A), epoch-zero-eligible full adaptation(B), and actual source-only reference(C). No selector redesign, new architecture, LR search or real-data execution was performed in preparing this package.

Start with SCIENTIFIC_PROTOCOL.md and EXPERIMENT_CONFIG.json. Installation/authorization commands are in INDEPENDENT_LOCAL_EXECUTION.md. PRIVATE_RESULT_SCHEMA.json describes restricted outputs. paired_report.py generates private comparisons within the run; it is not a separate command to inspect private results through AI.

The exact original fit and immutable data-provenance/runtime helpers are vendored and fingerprinted. ArmB's isolated implementation differs only in initial checkpoint eligibility; exact initialization, optimizer/update/RNG prefixes and common checkpoint scores are checked at runtime. Restored B epoch0 must exactly reproduce source-only raw probabilities.

Synthetic tests:

```sh
python3 -B -m unittest discover -s tests -v
```

One synthetic demo with a new unused output:

```sh
python3 -B epoch_zero.py --synthetic-demo --output /NEW_UNUSED_SYNTHETIC_OUTPUT
```

Demo output is exclusively invented and cannot establish clinical feasibility. Real mode uses a separate new local authorization purpose with existing agent/CI rejection; never execute it through Codex. All source and template paths are public/generic. No actual data locations or participant artifacts are included.

Repository prespecification is AI-authored; it does not claim external registry registration, institutional approval or an independent scientific sign-off. Results remain exploratory because development exposure already occurred. **INDEPENDENT_TEST_NOT_AVAILABLE**.
