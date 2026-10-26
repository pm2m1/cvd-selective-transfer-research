import torch

from dmv_mat_cvd.data.synthetic import VIEW_DIMS
from dmv_mat_cvd.models.multiview_mlp import MultiViewRiskNet
from dmv_mat_cvd.transfer.adapt import frozen_unchanged, set_selective_trainability, snapshot_frozen


def test_selective_freezing_snapshot():
    model = MultiViewRiskNet(VIEW_DIMS)
    mask = {name: (name == "view:metabolic") for name in model.selectable_modules()}
    set_selective_trainability(model, mask)
    snap = snapshot_frozen(model, mask)

    with torch.no_grad():
        for p in model.encoders["metabolic"].parameters():
            p.add_(0.01)

    ok, _ = frozen_unchanged(model, snap)
    assert ok


def test_actual_selective_training_changes_only_trainable_parameters(source_parts, target_parts):
    from dmv_mat_cvd.data.preprocessing import Preprocessor
    from dmv_mat_cvd.experiments.runner import loader
    from dmv_mat_cvd.transfer.adapt import adapt_model

    pp = Preprocessor().fit(source_parts["source_train"])
    model = MultiViewRiskNet(pp.view_dims)
    mask = {name: name == "view:metabolic" for name in model.selectable_modules()}
    source_before = {k: v.clone() for k, v in model.state_dict().items()}
    trained, integrity = adapt_model(
        model, mask, loader(pp.transform(target_parts["target_adaptation"])),
        loader(pp.transform(target_parts["target_validation"])), "cpu", epochs=2,
    )
    assert integrity["ok"] and integrity["frozen_modules_checked"] == 6
    assert all(torch.equal(source_before[k], v) for k, v in model.state_dict().items())
    assert not torch.equal(source_before["head.weight"], trained.head.weight)
    assert not torch.equal(source_before["encoders.metabolic.net.0.weight"], trained.encoders["metabolic"].net[0].weight)
    snap = snapshot_frozen(trained, mask)
    with torch.no_grad():
        next(trained.encoders["background"].parameters()).add_(.1)
    assert not frozen_unchanged(trained, snap)[0]


def test_mask_typo_rejected():
    import pytest
    with pytest.raises(ValueError, match="Invalid module mask"):
        set_selective_trainability(MultiViewRiskNet(VIEW_DIMS), {"typo": True})
