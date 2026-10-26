import numpy as np
import pytest

from dmv_mat_cvd.evaluation import ModuleRepresentations
from dmv_mat_cvd.safeguards import SplitRole
from dmv_mat_cvd.transfer.scores import (class_discriminability, multi_kernel_mmd,
                                        normalize_representations, score_modules)
from dmv_mat_cvd.transfer.selector import select_adaptation_mask


def test_vector_centroid_discriminability():
    labels = np.array([0, 0, 1, 1])
    # Centroids cancel if incorrectly collapsed to scalar averages.
    features = np.array([[-1, 1], [-2, 2], [1, -1], [2, -2]], dtype=float)
    assert class_discriminability(features, labels) == pytest.approx(6, abs=1e-6)
    assert class_discriminability(features, np.zeros(4)) == 0


def test_mmd_detects_shift_and_is_deterministic():
    x = np.random.default_rng(7).normal(size=(80, 4))
    assert multi_kernel_mmd(x, x) == pytest.approx(0, abs=1e-6)
    assert multi_kernel_mmd(x, x + 3) > .1
    assert multi_kernel_mmd(x, x + 3, max_samples=20, seed=7) == multi_kernel_mmd(x, x + 3, max_samples=20, seed=7)


def test_mmd_normalization_invariant_to_scale_translation_and_repeated_dimensions():
    rng = np.random.default_rng(3)
    x, y = rng.normal(size=(40, 4)), rng.normal(size=(32, 4)) + .8
    def discrepancy(a, b):
        left, right, _ = normalize_representations(a, b)
        return multi_kernel_mmd(left, right)
    value = discrepancy(x, y)
    assert discrepancy(x * 30 + 12, y * 30 + 12) == pytest.approx(value, abs=1e-6)
    assert discrepancy(np.tile(x, (1, 5)), np.tile(y, (1, 5))) == pytest.approx(value, abs=1e-6)
    assert normalize_representations(x, y)[2] == normalize_representations(x, y * 100)[2]


def test_constant_source_representations_are_finite():
    a, b, scale = normalize_representations(np.ones((8, 3)), np.full((6, 3), 2.0))
    assert scale > 0
    assert np.isfinite(multi_kernel_mmd(a, b))


def test_scoring_matches_legacy_when_normalization_disabled():
    rng = np.random.default_rng(8)
    source, target = rng.normal(size=(12, 5)), rng.normal(size=(10, 5))
    labels = np.tile([0, 1], 5)
    s = ModuleRepresentations({"a": source}, np.zeros(12), SplitRole.SOURCE_VALIDATION)
    t = ModuleRepresentations({"a": target}, labels, SplitRole.TARGET_ADAPTATION)
    values = score_modules(s, t, normalize=False)["a"]
    assert values["mmd"] == multi_kernel_mmd(source, target)
    assert values["discriminability"] == class_discriminability(target, labels)


def test_selector_deterministic_ties_and_extremes():
    tied = {"z": {"mmd": 1.0, "discriminability": 1.0}, "a": {"mmd": 1.0, "discriminability": 1.0}}
    mask, score = select_adaptation_mask(tied)
    assert mask == {"z": False, "a": True}
    assert mask == select_adaptation_mask(dict(reversed(list(tied.items()))))[0]
    assert score == {"z": .5, "a": .5}
    assert not any(select_adaptation_mask(tied, adapt_fraction=0)[0].values())
    assert all(select_adaptation_mask(tied, adapt_fraction=1)[0].values())
    shifted = {"stable": {"mmd": 0.0, "discriminability": 1.0},
               "shifted": {"mmd": 1.0, "discriminability": 0.0}}
    assert select_adaptation_mask(shifted)[0] == {"stable": False, "shifted": True}
    with pytest.raises(ValueError):
        select_adaptation_mask(tied, adapt_fraction=2)
