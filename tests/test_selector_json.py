"""Synthetic-only regression for pandas/NumPy scalar JSON interoperability."""

import json

import numpy as np
import pytest

from dmv_mat_cvd.experiments.selector_validation import write_json


@pytest.mark.parametrize("value", [np.int64(10), np.float32(0.25), np.float64(0.75), np.bool_(True)])
def test_numpy_summary_scalar_preserves_value(tmp_path, value):
    path = tmp_path / "INVENTED_summary.json"
    write_json(path, {"groups": [{"value": value}]})
    assert json.loads(path.read_text()) == {"groups": [{"value": value.item()}]}


@pytest.mark.parametrize("value", [np.float64(np.nan), np.float32(np.inf), float("nan")])
def test_nonfinite_summary_still_rejected_without_partial_output(tmp_path, value):
    path = tmp_path / "INVENTED_summary.json"
    with pytest.raises(ValueError):
        write_json(path, {"value": value})
    assert not path.exists()


def test_unsupported_summary_object_still_rejected(tmp_path):
    path = tmp_path / "INVENTED_summary.json"
    with pytest.raises(TypeError):
        write_json(path, {"value": object()})
    assert not path.exists()
