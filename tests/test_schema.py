import numpy as np
import pytest

from dmv_mat_cvd.data.base import CohortTable
from dmv_mat_cvd.data.schema import ENDPOINT_FIELDS, PREDICTORS, VIEW_FEATURES


def test_valid_canonical_cohort(source):
    assert len(source) == 160
    assert list(source.predictors()) == list(PREDICTORS)
    assert len(VIEW_FEATURES) == 5


@pytest.mark.parametrize("column", ["participant_id", *PREDICTORS])
def test_missing_required_column(source, column):
    with pytest.raises(ValueError, match="Missing required"):
        CohortTable(source.records.drop(columns=column), "invalid")


def test_endpoint_and_extra_columns_never_predictors(source):
    frame = source.records.copy()
    frame["future_extension"] = frame.label
    predictors = CohortTable(frame, "test").predictors()
    assert not set(ENDPOINT_FIELDS).intersection(predictors)
    assert "participant_id" not in predictors
    assert "future_extension" not in predictors


@pytest.mark.parametrize("name,value", [("sex", 1), ("smoking_status", "smoker"),
                                        ("antihypertensive_treatment", "Y"), ("age", np.inf)])
def test_raw_codes_and_infinities_rejected(source, name, value):
    frame = source.records.copy()
    frame[name] = value
    with pytest.raises(ValueError):
        CohortTable(frame, "invalid")


def test_label_status_consistency(source):
    frame = source.records.copy()
    frame["endpoint_status"] = "unknown"
    with pytest.raises(ValueError, match="disagrees"):
        CohortTable(frame, "invalid")
