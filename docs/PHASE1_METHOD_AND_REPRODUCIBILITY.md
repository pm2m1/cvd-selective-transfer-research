# Phase 1 method and reproducibility boundary

This is a **release-copy summary**. The historical protocol, registration, checkpoint inventories, private target lock, original failure record and recovery audit remain unchanged in the closed research workspace. They are intentionally absent here because some contain local paths, participant assignments or restricted execution metadata. Links in the manuscript to this page point to a summary, **not to a copy of the original records**.

## Frozen study

- Source: HAALSI Wave 1, South Africa. Target: MHAS 2012 examination cohort, Mexico.
- Endpoint: **wave-observed, doctor-reported heart attack or stroke** among baseline-negative people with an observed follow-up outcome. It was neither adjudicated nor an exact first-event date.
- Five clinical views: background (age, sex), haemodynamic (SBP, DBP), metabolic (BMI, total cholesterol, HDL), behaviour (smoking), and comorbidity/medication (doctor-reported diabetes, antihypertensive treatment).
- Existing five-view network: one encoder per view, two fusion modules and a binary head. The re-engineered selector computed detached module representations, permutation-calibrated source/target MMD and source-relative class geometry, then made SHARE/ADAPT decisions. **MMD was a selection statistic, not a backpropagated alignment loss.**
- The prespecified primary method was `calibrated_logical`; full fine-tuning was its primary comparator. Head-only and matched random were interpretive controls. Ten paired 25-positive/75-negative target adaptation draws shared a single target validation and test population; a nested 10+30 budget was secondary.

The published [aggregate-only result](../results/aggregate_only_results.json) identifies the frozen protocol and registration digest. The immutable target test contained 283 people and 21 positive reports. The mean paired AP contrast was +0.001819, with descriptive joint participant-bootstrap interval −0.024809 to +0.032340. **This does not establish superiority.** The original selector chose no additional module in nine of ten primary draws. Matched random masks were identical in nine of ten primary draws and all ten low-label draws, limiting that control's independence.

## What can be reproduced from this repository

The included code and synthetic tests reproduce the **software behavior**: five-view tensors, detached selector scoring, module masks, freezing, fairness and controlled synthetic shifts. See the [README](../README.md). Synthetic results are not clinical evidence and do not regenerate the historical real-data result.

The historical real-cohort analysis cannot be rerun from this release. It needs separately obtained HAALSI and MHAS products under their respective terms, release-specific mappings, private participant assignments, fitted preprocessing and frozen checkpoints. None are distributed here. This release offers no command to evaluate the original locked MHAS test.

## Final-test incident

The first authorized final-test attempt **accessed target-test rows and failed during a native PyTorch/OpenMP inference stall**, before producing predictions or metrics. Its authorization was consumed. A separate runtime investigation used synthetic data and found evidence consistent with a thread/runtime interaction, without proving LayerNorm itself defective. A newly versioned, process-isolated executor received **separate explicit authorization** for one recovery evaluation of the **same frozen test**. No method, checkpoint, mask, preprocessing statistic, participant assignment, metric or bootstrap rule changed. The recovery produced the aggregate result. This history is disclosed in the manuscript; the first execution is not described as untouched or successful.

## Data use and citation

Get HAALSI from [ICPSR study 36633](https://www.icpsr.umich.edu/web/NACDA/studies/36633) and MHAS from the [official MHAS data products](https://www.mhasweb.org/DataProducts/Home.aspx), subject to the distributors' registration and use terms. No participant data, credentials or private records are in this repository. Before any public manuscript/code release, authors must verify the exact MHAS product names, release years and retrieval dates for product-specific citations, the MHAS research-product notification status, the final code license, author approvals and applicable institutional/data-use statements. No such approval or notification is inferred from this page.
