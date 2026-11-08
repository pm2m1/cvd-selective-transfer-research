"""Read only locked MHAS development rows for model development.

The first pass reads identifiers alone. The second pass seeks to permitted row
positions before reading disease or predictor columns. Test rows are never
materialized with those columns. This relies on pandas' StataReader row cursor;
its behavior is checked by fixture tests and fails if the cursor is unavailable.
"""
from __future__ import annotations

from pathlib import Path
import json

import numpy as np
import pandas as pd

from .real_cohorts import MHASAdapter, join_mhas_master_followup
from ..public_evidence_reconciliation import MASTER_COLUMNS


def read_allowed_stata_rows(path: Path, id_columns: tuple[str, ...],
                            allowed_keys: set[str], columns: set[str],
                            key_function) -> pd.DataFrame:
    """Use an ID-only index pass, then read selected row runs by file position."""
    if not allowed_keys or not id_columns or not columns:
        raise ValueError("Nonempty allowed IDs, ID columns and requested columns required")
    ids = pd.read_stata(path, columns=list(id_columns), convert_categoricals=False)
    keys = ids.apply(key_function, axis=1).astype(str)
    if keys.duplicated().any():
        raise ValueError("Duplicate raw identifiers in locked development input")
    positions = np.flatnonzero(keys.isin(allowed_keys).to_numpy())
    if set(keys.iloc[positions]) != allowed_keys:
        raise ValueError("Locked development identifiers missing from raw release")
    if len(positions) == 0:
        raise ValueError("No locked development rows found")
    runs: list[tuple[int, int]] = []
    start = previous = int(positions[0])
    for position in positions[1:]:
        position = int(position)
        if position != previous + 1:
            runs.append((start, previous - start + 1))
            start = position
        previous = position
    runs.append((start, previous - start + 1))
    frames = []
    with pd.read_stata(path, iterator=True, convert_categoricals=False) as reader:
        if not hasattr(reader, "_lines_read"):
            raise RuntimeError("Pandas StataReader no longer supports safe row-position reads")
        available = set(reader.variable_labels())
        if columns - available:
            raise ValueError("Requested mapped Stata columns are missing")
        for offset, count in runs:
            reader._lines_read = offset
            frames.append(reader.read(nrows=count, columns=sorted(columns),
                                      convert_categoricals=False))
    frame = pd.concat(frames, ignore_index=True)
    # Restrict row-wise key coercion to ID columns; mixed Stata float columns
    # can otherwise promote a numeric identifier and change its string form.
    output_keys = frame.loc[:, list(id_columns)].apply(key_function, axis=1).astype(str)
    if len(frame) != len(allowed_keys) or set(output_keys) != allowed_keys:
        raise RuntimeError("Selected Stata row offsets did not return the permitted identifiers "
                           f"(rows={len(frame)}, expected={len(allowed_keys)}, "
                           f"missing={len(allowed_keys - set(output_keys))}, "
                           f"extra={len(set(output_keys) - allowed_keys)})")
    return frame


def load_mhas_locked_development(root: Path, master_file: Path, mapping: dict,
                                 permitted_ids: set[str], forbidden_ids: set[str]) -> tuple[pd.DataFrame, dict]:
    """Build the existing public-v2 raw join from target development IDs only."""
    if mapping.get("cohort_name") != "MHAS" or mapping.get("id_namespace") != "MHAS":
        raise ValueError("This loader is restricted to the approved MHAS public cohort")
    if not permitted_ids or permitted_ids & forbidden_ids or not all(
            x.startswith("MHAS:") for x in permitted_ids | forbidden_ids):
        raise ValueError("Development/test role boundary is invalid")
    # The released harmonized ID column has mixed integer/float Stata storage.
    # Canonical lock strings preserve that representation, while the documented
    # cross-file join uses the integral numeric key.
    raw_keys = {str(int(float(x.removeprefix("MHAS:")))) for x in permitted_ids}
    if len(raw_keys) != len(permitted_ids):
        raise ValueError("Canonical MHAS IDs collide after validated numeric join conversion")
    main_path = root / mapping["files"]["main"]
    bio_path = root / mapping["files"]["biomarker"]
    eol_path = root / mapping["files"]["eol"]
    main_id = mapping["join_main_id"]
    main_columns = MHASAdapter(mapping)._required() - {
        mapping["fields"]["total_cholesterol"], mapping["fields"]["hdl"]}
    main_columns.add(main_id)
    main = read_allowed_stata_rows(main_path, (main_id,), raw_keys,
                                  main_columns, lambda row: str(int(row[main_id])))
    household, person = mapping["bio_household_id"], mapping["bio_person_number"]
    key = lambda row: str(int(row[household]) * 100 + int(row[person]))
    bio_columns = {household, person, mapping["fields"]["total_cholesterol"],
                   mapping["fields"]["hdl"], "date_12"}
    bio = read_allowed_stata_rows(bio_path, (household, person), raw_keys,
                                 bio_columns, key)
    bio["__join_id"] = pd.to_numeric(bio[household]).astype("int64") * 100 + pd.to_numeric(bio[person]).astype("int64")
    main["__join_id"] = pd.to_numeric(main[main_id]).astype("int64")
    joined = bio.merge(main, on="__join_id", how="left", validate="one_to_one")
    eol_id = mapping["eol_id"]
    # End-of-life records exist for only some anchors; discover intersection
    # from IDs alone and read no disease/death fields for forbidden IDs.
    eol_ids = pd.read_stata(eol_path, columns=[eol_id], convert_categoricals=False)
    eol_present = raw_keys & set(eol_ids[eol_id].astype(str))
    if eol_ids[eol_id].astype(str).duplicated().any():
        raise ValueError("Duplicate End-of-Life identifiers")
    if eol_present:
        eol = read_allowed_stata_rows(eol_path, (eol_id,), eol_present,
             {eol_id, mapping["eol_year"], mapping["eol_month"]},
             lambda row: str(row[eol_id]))
        eol = eol.rename(columns={eol_id: "__join_id", mapping["eol_year"]: "__eol_year",
                                  mapping["eol_month"]: "__eol_month"})
        eol["__join_id"] = pd.to_numeric(eol["__join_id"]).astype("int64")
        joined = joined.merge(eol, on="__join_id", how="left", validate="one_to_one", indicator="__eol_merge")
        joined["__has_eol"] = joined["__eol_merge"].eq("both")
        joined = joined.drop(columns="__eol_merge")
    else:
        joined["__eol_year"] = np.nan
        joined["__eol_month"] = np.nan
        joined["__has_eol"] = False
    master_key = lambda row: str(int(row["cunicah"]) * 100 + int(row["np"]))
    master = read_allowed_stata_rows(master_file, ("cunicah", "np"), raw_keys,
        set(MASTER_COLUMNS) | {"tipent_12", "tipne_12"}, master_key)
    joined, join_report = join_mhas_master_followup(joined, master,
        additional_metadata=("tipent_12", "tipne_12"))
    labels = pd.read_stata(main_path, iterator=True, convert_categoricals=False).value_labels()
    labels.update(pd.read_stata(bio_path, iterator=True, convert_categoricals=False).value_labels())
    if set("MHAS:" + joined[main_id].astype(str)) != permitted_ids:
        raise ValueError("MHAS development join changed permitted membership")
    return joined, {"labels": labels, "join": join_report,
                    "row_read_policy": "identifier-only index then permitted row runs"}
