# Data access, disclosure and attribution

[Phase 1 index](overview.md) · [Historical release review](../RELEASE_REVIEW.md)

This repository distributes public code, synthetic tests and previously approved aggregates. It does not grant data rights. Obtain HAALSI from [ICPSR study 36633](https://www.icpsr.umich.edu/web/NACDA/studies/36633) and MHAS through its [official data products](https://www.mhasweb.org/DataProducts/Home.aspx), following provider and institutional terms. Do not put participant records, assignments, predictions, checkpoints, credentials or private execution evidence into GitHub, issues, CI logs or AI tools.

Cite the original [DMV-MAT EEG paper](https://doi.org/10.1109/TNNLS.2024.3350085) for inspiration, not as a claim of exact reproduction. Existing study citations remain in the [manuscript bibliography](../FINAL_SUBMISSION_MANUSCRIPT.md). The HAALSI V4 record provides DOI 10.3886/ICPSR36633.v4. Exact MHAS product-specific citation metadata, retrieval information and research-product notification status still require author confirmation. No ethics, notification, manuscript acceptance or institutional approval is invented.

## Threshold publication gate

The new empirical threshold tables and figures remain **not cleared for public disclosure**. Operator-reported private completion and an integrity check do not constitute disclosure approval. This branch publishes no new empirical TP/TN/FP/FN, classification rates, private confusion matrices, source fingerprints or result archives.

Before a later PR can add results, an independently authorized reviewer must establish applicable permission, review the exact proposed artifact allowlist and joint disclosure risks, and approve the public wording. Review all models/draws/thresholds together: differencing nested cutoff counts can reveal small cells. Removing IDs alone is insufficient. A statistical integrity manifest is not a publisher-authenticity or confidentiality assessment.

The publication mechanism is a **separate reviewed results PR**, with an updated explicit public-file allowlist, source provenance retained privately, disclosure approval recorded through the applicable governance process, and rerun public checks. There is no auto-publish command or default approval flag. Until then, documentation contains methodology and synthetic examples only. Never add the private comparison archive to bypass this gate.

## Licensing and author review

No code license has been granted. Public visibility is not a substitute for an explicit reuse license. This update adds no license. Final manuscript wording, author attribution, institutional/data-use statements and product citations remain subject to author approval. The preservation and automated scans support review; they cannot certify legal or scientific acceptance.

## Official policy recheck — 8 November 2026

The [MHAS AI/LLM policy](https://mhasweb.org/home/AI-llm-use-policy.html), updated October 2026, permits public documentation, non-identifying aggregate estimates and code assistance; it prohibits supplying participant/household microdata to external AI tools. That distinction supports public-code and approved-aggregate work here, not automatic release of every small-cell derivative. The [data-products terms](https://www.mhasweb.org/DataProducts/Home.aspx) require registration, attribution and research-product notification; exact product citations and notification remain author-review items. The [HAALSI distributor record](https://www.icpsr.umich.edu/web/NACDA/studies/36633) confirms V4 and its citation, not permission to redistribute all local files. No terms were accepted, account created, private input opened or publication approval inferred.
