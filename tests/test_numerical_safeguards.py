import numpy as np
import pytest
import torch

from dmv_mat_cvd.data.base import MultiViewDataset
from dmv_mat_cvd.experiments.runner import loader
from dmv_mat_cvd.safeguards import SplitRole
from dmv_mat_cvd.training import train_model


def test_nonbinary_labels_rejected_before_float32_rounding():
    with pytest.raises(ValueError, match="binary"):
        MultiViewDataset({"view": np.zeros((2, 1))}, np.array([0, 1 + 1e-8]))


def test_float32_overflow_rejected_at_tensor_boundary():
    with pytest.raises(ValueError, match="float32"):
        MultiViewDataset({"view": np.full((2, 1), 1e100)}, np.array([0, 1]))


def test_observed_object_dtype_labels_remain_supported():
    # Nullable tabular integer columns can yield object arrays on conversion.
    dataset = MultiViewDataset({"view": np.zeros((2, 1))}, np.array([0, 1], dtype=object))
    assert torch.equal(dataset.labels, torch.tensor([0.0, 1.0]))


@pytest.mark.parametrize("stage", ["training", "validation"])
def test_nonfinite_loss_never_returns_a_silent_fallback_checkpoint(stage):
    class NonfiniteModel(torch.nn.Module):
        def __init__(self):
            super().__init__()
            self.weight = torch.nn.Parameter(torch.tensor(0.1))

        def forward(self, views):
            logits = self.weight.expand(len(views["view"]))
            if self.training == (stage == "training"):
                logits = logits * float("nan")
            return logits

    views, labels = {"view": np.zeros((4, 1))}, np.array([0, 1, 0, 1])
    train = loader(MultiViewDataset(views, labels, SplitRole.SOURCE_TRAIN))
    validation = loader(MultiViewDataset(views, labels, SplitRole.SOURCE_VALIDATION))
    with pytest.raises(FloatingPointError, match=f"Nonfinite {stage} loss"):
        train_model(NonfiniteModel(), train, validation, "cpu", epochs=1)
