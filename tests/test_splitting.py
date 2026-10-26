import pandas as pd
import pytest

from dmv_mat_cvd.data.base import CohortTable
from dmv_mat_cvd.data.splitting import assert_disjoint, split_source, split_target


def test_reproducible_disjoint_cover(source):
    first, second = split_source(source, seed=2), split_source(source, seed=2)
    assert_disjoint(*first.values())
    assert sum(len(part) for part in first.values()) == len(source)
    assert {k: v.participant_ids for k, v in first.items()} == {k: v.participant_ids for k, v in second.items()}
    assert first["source_train"].participant_ids != split_source(source, seed=3)["source_train"].participant_ids


def test_grouped_participants(source):
    repeated = CohortTable(pd.concat([source.records, source.records.iloc[:20]]), source.domain)
    parts = split_source(repeated, seed=1)
    assert_disjoint(*parts.values())
    assert sum(len(p) for p in parts.values()) == len(repeated)
    for participant in source.records.participant_id:
        assert sum(participant in p.participant_ids for p in parts.values()) == 1


def test_target_lock_independent_of_adaptation_budget(target):
    first = split_target(target, adaptation_fraction=0.8, seed=12)
    other = split_target(target, adaptation_fraction=0.4, seed=12)
    assert first["target_test"].participant_ids == other["target_test"].participant_ids
    assert len(first["target_test"]) == 30
    assert_disjoint(*first.values())


def test_optional_source_test(source):
    assert set(split_source(source, 0.8, 0.2)) == {"source_train", "source_validation"}


@pytest.mark.parametrize("test_fraction", [0, 1, -1, 1.1])
def test_bad_target_fraction(target, test_fraction):
    with pytest.raises(ValueError):
        split_target(target, test_fraction=test_fraction)


def test_small_cohort_clear_error(source):
    with pytest.raises(ValueError, match="Too few"):
        split_source(CohortTable(source.records.iloc[:2], source.domain))
