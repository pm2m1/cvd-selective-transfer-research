import numpy as np
import pandas as pd
import pytest

from dmv_mat_cvd.data.endpoint import EventMetadata, build_endpoint, construct_endpoints


@pytest.mark.parametrize("event,state,label", [
    (EventMetadata("mi", 100), "positive", 1),
    (EventMetadata("stroke", 1826), "positive", 1),
    (EventMetadata("mi", 1900, last_followup_days=2000), "known_negative", 0),
    (EventMetadata("mi", 1900, last_followup_days=1000), "unknown", None),
    (EventMetadata(last_followup_days=1826), "known_negative", 0),
    (EventMetadata(last_followup_days=300), "unknown", None),
    (EventMetadata(), "unknown", None),
    (EventMetadata(death_time_days=800, death_is_nonqualifying=True), "competing_death", None),
    (EventMetadata(death_time_days=800), "unknown", None),
    (EventMetadata("mi", 100, 200, 100, True), "positive", 1),
    (EventMetadata("stroke", 200, 200, 200, True), "positive", 1),
    (EventMetadata(death_time_days=1826, last_followup_days=1826, death_is_nonqualifying=True), "known_negative", 0),
    (EventMetadata(death_time_days=1826, death_is_nonqualifying=True), "unknown", None),
    (EventMetadata("nonqualifying", 100, last_followup_days=1900), "known_negative", 0),
])
def test_endpoint_states(event, state, label):
    result = build_endpoint(event)
    assert result.status.value == state
    assert result.label == label


@pytest.mark.parametrize("event", [
    EventMetadata("mi", 301, 300), EventMetadata("stroke", -1), EventMetadata("mi", 0),
    EventMetadata("mi", np.inf), EventMetadata("mi", np.nan), EventMetadata("mi"),
    EventMetadata(event_time_days=100), EventMetadata(last_followup_days=-1),
    EventMetadata(death_time_days=200, last_followup_days=300),
    EventMetadata(death_is_nonqualifying=True), EventMetadata("raw_unverified_code", 100),
    EventMetadata(death_time_days=300, death_is_nonqualifying="no"),
])
def test_invalid_chronology_and_unharmonized_events_rejected(event):
    with pytest.raises(ValueError):
        build_endpoint(event)


def test_configurable_horizon():
    assert build_endpoint(EventMetadata("mi", 100, last_followup_days=150), 90).label == 0
    with pytest.raises(ValueError):
        build_endpoint(EventMetadata(), 0)


def test_table_nullable_labels_and_synthetic_consistency(source):
    built = construct_endpoints(source.records)
    np.testing.assert_array_equal(built.label, source.records.label)
    frame = pd.DataFrame([dict(event_type=None, event_time_days=None, death_time_days=None,
                               last_followup_days=12)])
    assert pd.isna(construct_endpoints(frame).label.iloc[0])
