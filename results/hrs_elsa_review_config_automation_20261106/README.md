# Offline review configuration automation

**READY_FOR_INDEPENDENT_LOCAL_METADATA_BINDING**

`prepare_offline_review_config.py` is a standalone, standard-library helper for the **existing** unresolved review configuration. It requires the already installed, byte-verified original review tool. It does not reinstall that tool, recreate its template, execute its review, issue authorization or change scope declarations.

The helper fills only `private_root` and the ten evidence descriptors. It preserves the public contract pin, prohibitions and unresolved `source_use_review`, `isolation_review` and `reviewed_scope`. Its atomic update creates an exclusive0600 original-byte backup and staging file, fsyncs them, replaces only the new review configuration, then creates a private binding record. Historical records remain read-only. Partial artifacts remain preserved and block retries.

Two modes:

- `--bind`: requires a pristine original template and otherwise empty new review-run directory. Select either controlled known-layout discovery or an explicit, privately reviewed evidence map.
- `--check`: read-only verification of the binding, backup, metadata hashes and unchanged configuration core. It accepts unresolved declarations or the exact declarations independently recorded later by the operator. It never writes either form.

Controlled discovery uses shallow listings of the two named historical operation directories. It considers bounded authorization/configuration JSON filename families, then establishes roles using original purposes, schemas, config hashes and output bindings. Multiple authorization candidates stop the operation. Output filenames are derived from the recorded output binding; registration comes from the diagnostic's original registered-manifest descriptor. It never searches recursively or opens clinical source files.

The frozen metadata-binding validator is reused in place, without calling its execution or scientific worksheet functions. A structurally bound configuration **still fails original preflight while permission/isolation declarations remain unresolved**. This is intentional. The synthetic compatibility test separately represents a human establishing those facts; the helper never does so.

Use `INDEPENDENT_OPERATOR_COMMANDS.md`. Transfer the new helper into a separate isolated helper directory, not the original tool tree or review-run directory. No pip installation or ML-pipeline rebuild is required. The public frozen-review copy under `tests/frozen_review_tools` is an unchanged synthetic compatibility fixture, not a replacement private installation.

No actual private configuration, report, authorization or dataset was accessed by Codex. No private binding, review, count or training operation is claimed successful. Public release verification and invented tests are recorded in `VALIDATION_REPORT.md`.
