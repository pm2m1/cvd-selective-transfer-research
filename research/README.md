# Original research implementation and artifact archive

This directory and the linked `results/` packages contain actual implementation files and original invented-run outputs, not only descriptions or newly regenerated illustrations. Academic PDF/LaTeX/Overleaf/bibliography documents are **excluded by the author's explicit instruction**, regardless of permission status.

## Historical Phase 1 implementation

[phase1_implementation_snapshot/src/dmv_mat_cvd](phase1_implementation_snapshot/src/dmv_mat_cvd) preserves the original implementation tree, including clinical cohort construction, source/target baselines, selective adaptation, final statistics and recovery workers. 16 source files contain **explicit privacy projections** replacing private frozen bindings/paths with `WITHHELD_PRIVATE_*` literals. All other archived Python files retain their original bytes. No scientific calculations were changed. This is reference source, **not a runnable or authorized replacement for consumed historical clinical operations**. Binding placeholders intentionally cannot satisfy the original real-data gates. Existing production/frozen project files were never modified.

## Original packages

| Package under `results/` | Actual implementation |
|---|---|
| [haalsi_mhas_threshold_sweep_20261107](../results/haalsi_mhas_threshold_sweep_20261107) | Complete retained-score reader, reconciliation, grid analysis, original report/figure generator, provenance gates and tests |
| [label_efficiency_followup_20261105](../results/label_efficiency_followup_20261105) | Nested budgets, split accounting, training adapters, calibration, outer evaluation and prospective interface |
| [dmvmat_epoch_zero_followup_20261105](../results/dmvmat_epoch_zero_followup_20261105) | Paired original/epoch-zero/source-only arms and checkpoint tests |
| [dmvmat_root_cause_audit_20261105](../results/dmvmat_root_cause_audit_20261105) | Selector reference, mask/optimizer invariants and original invented diagnostics/results |
| [hrs_elsa_final_count_feasibility_20261105](../results/hrs_elsa_final_count_feasibility_20261105) | Original count engine, exact public variable mappings, reader and synthetic fixtures |
| [hrs_elsa_source_registration_20261105](../results/hrs_elsa_source_registration_20261105) | Original registration utility, configuration generation and tests; no registered private sources |
| [hrs_elsa_source_registration_plan_helper_20261105](../results/hrs_elsa_source_registration_plan_helper_20261105) | Original plan helper and readiness checker |
| [hrs_elsa_interview_conflict_investigation_20261106](../results/hrs_elsa_interview_conflict_investigation_20261106) | Original reproducer, reference decoder and observability-only proposal |
| [hrs_elsa_interview_status_diagnostic_20261106](../results/hrs_elsa_interview_status_diagnostic_20261106) | Original status-only diagnostic, minimal reader and independent-local runtime |
| [hrs_elsa_private_review_handoff_20261106](../results/hrs_elsa_private_review_handoff_20261106) | Original offline review implementation and unresolved decision templates; no completed private worksheet |
| [hrs_elsa_review_config_automation_20261106](../results/hrs_elsa_review_config_automation_20261106) | Original metadata-binding/preflight helper and tests |
| [hrs_elsa_training_fasttrack_20261106](../results/hrs_elsa_training_fasttrack_20261106) | Complete seven-method pipeline, strict canonical contracts, frozen evaluation and original synthetic aggregate results |
| [hrs_elsa_final_scientific_unblocking_20261106](../results/hrs_elsa_final_scientific_unblocking_20261106) | Original public evidence/mapping integration and gate regressions; no adopted eligibility correction |

Run each package's tests in a **separate Python process**, from that package directory: `python -B -m pytest -q -p no:cacheprovider tests`. Historical packages intentionally retain their own module names and versioned source pins. They are not all collected into the top-level namespace. The workflow runs 12 isolated suites without private data. The conflict-investigation suite additionally requires three original third-party public-documentation extracts that are not cleared for redistribution; it reports NOT_RUN_EXTERNAL_DOCUMENTATION_NOT_DISTRIBUTED in a clean checkout. Its original-source suite was separately run locally with those public documents and passed 166 tests. The missing documents are listed per file in the import registry. No source pin is bypassed.

## Original output collection actually included

[Original invented retained-score run](../results/haalsi_mhas_threshold_sweep_20261107_SYNTHETIC_RELEASE_CHECK) includes all **300 original invented confusion SVGs across the three retained development/final/release-check runs**, both original summary-plot figures in SVG and PNG for each run, the per-draw/summary metric CSVs and the original invented report/JSON. The original filenames, including `.private.` inherited from the report generator, are retained within this unmistakably synthetic directory. Those labels are not real MHAS data, and this collection is **not a substitute for the protected real confusion-matrix collection**. Simulated runtime receipts are excluded.

The [real threshold collection](../results/haalsi_mhas_real_threshold_analysis) is now separately released: 510 original empirical confusion SVGs, all six response families, cross-method plots and numerical outputs. This followed the researcher's explicit attestation of review/clearance and instruction to publish; no documentary record or independent legal certification is claimed. All 528 selected aggregate originals matched their recorded source-output hashes. No private operational records or individual predictions/IDs were released.

The [operator-only metadata inventory tool](../scripts/inventory_protected_filenames_local.py) can create an exact local file-by-file blocked list and counts without reading payloads, once applicable metadata-review permission is independently established. It refuses agent/CI invocation before input traversal and does not create authorization or upload anything. It was tested only on invented directories. Example independent Terminal invocation, with a new protected destination:

```sh
python3 scripts/inventory_protected_filenames_local.py --root "$HOME/ResearchPrivate/dmvmat_threshold_sweep_20261107_run/threshold_comparison_v1" --output "$HOME/ResearchPrivate/dmvmat_unpublished_filename_inventory_20261108"
```

The reviewed real-result directory has now been inventoried under the subsequent user-attested aggregate-inspection scope: 536 files, 528 original integrity-bound aggregates plus one separately verified post-run dashboard released, and seven excluded. The generic human-only tool remains for unrelated private collections; its guard was not bypassed or invoked for publication. Protected originals stay in place. An exact public file list, SHA256, source role and byte-preservation status is in [IMPORTED_PUBLIC_ARTIFACTS.json](IMPORTED_PUBLIC_ARTIFACTS.json); every imported public file has a direct branch URL derived from its recorded repository path. The remote tree/content check is recorded separately after pushing.

The earlier [original synthetic development run](../results/haalsi_mhas_threshold_sweep_20261107_SYNTHETIC_DEMO) and [original synthetic final run](../results/haalsi_mhas_threshold_sweep_20261107_SYNTHETIC_FINAL) are retained alongside the release-check run. These are original files, not new scores or regenerated substitutes. Three runs do not represent three clinical experiments.

[Legacy implementation snapshot](legacy_implementation_snapshot) adds the distinct original feasibility/reassessment readers, supplementary metrics/export/training tools and seven-candidate orchestration source. Byte-identical cloned sources are mapped through `source_aliases` in the import registry to the already published original file rather than silently discarded. Legacy references with withheld private bindings are reference-only, not a substitute authorization or a new runnable clinical release. No generated clinical outputs were traversed for this source-only import.
