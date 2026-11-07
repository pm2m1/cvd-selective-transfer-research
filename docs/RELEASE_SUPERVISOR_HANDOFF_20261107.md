# Supervisor handoff: public scope and review decision — 7 November 2026

[Supervisor guide](SUPERVISOR_PHASE1_GUIDE.md) · [Report-to-code map](PHASE1_REPORT_TO_CODE_MAP.md) · [Figure inventory](PHASE1_FIGURE_INVENTORY.md) · [Academic-report status](../reports/nitw-btech-phase1/README.md)

## Starting state, independently checked

The public repository default was `main` at `79bd96c078e517824638a893919153f497978b44`. PR #1 was open, unmerged, non-draft and conflict-free at `8e6b8b9f2d05640006f3547015311f0025a1240f`. There were no submitted reviews. Both push and pull-request CI runs passed on that head; earlier failures on the preceding commit remain visible, with the output-only NumPy scalar serialization correction preserved. The local checkout was clean and matched the remote, so no separate worktree or history rewrite was necessary.

Before this handoff change, the public suite passed **188 tests, 0 failures**. No private data directory, clinical output, threshold CSV/SVG, academic local-review threshold report or old authorization was opened for this repository update.

## What this addition publishes

- A supervisor reading guide, exact implementation/evidence map and research figure inventory.
- An SVG renderer and paired AP contrast figure using **only the already published aggregate JSON**, with the primary full-fine-tuning contrast and secondary comparisons distinguished. No bootstrap or clinical inference is rerun.
- README entry points, optional public-figure dependencies and a public-only CI rendering step.
- Focused tests for the documented 8,033/33 parameter counts, published contrast values, actual mapped code symbols and the academic-report publication boundary.
- A status README under the academic-report directory. The release guard permits only that README there until separate public distribution is genuinely reviewed; its global private-format bans and frozen-file checks remain intact.

No model, training, selector, preprocessing, statistical computation or frozen empirical artifact changes. The original seven SVGs, manuscript, supplement, aggregate JSON and historical Phase-2A documents remain byte-identical. The 75-file original-public binding ledger and its single prior output-only compatibility exception are unchanged. The [earlier release review](RELEASE_REVIEW_20261107.md) remains a historical record rather than being rewritten to describe this later addition.

## Academic report decision

The 30-page public-results report was checked against its actual source and approved figures. Three singular expressions in its two-author declaration were genuine editorial defects; only those were corrected in a new local academic copy. The abstract was checked and did not contain the suspected grammar defect. Student names/registration numbers, institute/supervisor, unsigned forms, original figures, scientific results and bibliography were retained. The original report archive was not overwritten.

**PDF/LaTeX publication is not authorized by this update.** Permission for public GitHub distribution of the exact academic document, identities, registration numbers, institutional artwork/forms and any signatures has not been established. No academic PDF/LaTeX/ZIP, identity values, logo, signature or review record is committed. The complete package is staged outside Git for an independently approved supervisor channel. A public edition, if required, must be explicitly reviewed; fields are not silently removed from the official copy.

The restricted threshold-expanded report is not a candidate public release. Neither a newer filename, arithmetic correctness nor a prior result-integrity check clears those results. No new empirical threshold cells, real confusion matrices, ten-draw response plot, private source fingerprints, paths, predictions, IDs or authorizations enter this PR.

## Scientific and reproducibility findings

The primary AP difference remains **+0.001819**, descriptive 95% joint participant-bootstrap interval **[−0.024809,+0.032340]**. Superiority was not established. Ten paired enriched adaptation draws reuse one held-out population; they are not cross-validation folds or independent external validations. Head-only competitiveness, sparse/all-SHARE logical behavior and the weakly distinct random control remain explicit. All 13 methods and the secondary budget remain accessible.

The implementation map distinguishes public model/selector mechanisms and synthetic checks from approved frozen aggregates, restricted inputs and work not performed. In particular, the original clinical runner, exact real mappings/memberships/checkpoints, test probabilities and joint test-bootstrap executor are not public. Stored results and synthetic tests do not replace them. HRS → ELSA remains unresolved feasibility/engineering work, with no established real training result.

## Verification and release status

The final local suite passed **207 tests, 0 failures**, including 19 new handoff/figure/traceability/publication-boundary cases. Ruff lint/format, source-preservation, allowlist/link/SVG/privacy checks, package import/build and the public synthetic demonstrations are part of the required pre-push verification. Actual local results and current remote CI URLs are recorded in PR #1 and the separate local supervisor handoff. Remote success is not inferred from a local run. The paired-contrast SVG was rendered and visually inspected; local academic-copy compilation/rebuild is recorded outside Git because that copy is not approved for publication.

Scans cover explicit tracked public files and known credential/path patterns. They do not prove the absence of every possible secret, authenticate publisher provenance, establish clinical validity or grant publication rights. Full empirical reconstruction cannot be run from this checkout alone.

The branch is suitable for supervisor inspection through PR #1. It is **not automatically merged**: the earlier author-controlled manual review remains unresolved. Report/authorship publication scope, exact MHAS product citations/notification, licensing choice and final institutional/manuscript wording still require independent author decisions. No license, signature, acceptance or institutional endorsement is invented.
