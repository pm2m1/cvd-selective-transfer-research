from __future__ import annotations

from copy import deepcopy
from typing import Dict

import torch


def clone_model(model):
    return deepcopy(model)


def set_selective_trainability(model, adapt_mask: Dict[str, bool], train_head: bool = True):
    unknown = set(adapt_mask) - set(model.selectable_modules())
    if unknown or any(not isinstance(value, bool) for value in adapt_mask.values()):
        raise ValueError(f"Invalid module mask; unknown modules: {sorted(unknown)}")
    for p in model.parameters():
        p.requires_grad = False

    selectable = model.selectable_modules()
    for name, module in selectable.items():
        if adapt_mask.get(name, False):
            for p in module.parameters():
                p.requires_grad = True

    if train_head:
        for p in model.head.parameters():
            p.requires_grad = True


def snapshot_frozen(model, adapt_mask: Dict[str, bool]):
    out = {}
    for name, module in model.selectable_modules().items():
        if not adapt_mask.get(name, False):
            out[name] = {k: v.detach().cpu().clone() for k, v in module.state_dict().items()}
    return out


def frozen_unchanged(model, snapshot, atol=0.0):
    for name, before in snapshot.items():
        now = model.selectable_modules()[name].state_dict()
        for k, v in before.items():
            if not torch.allclose(v, now[k].detach().cpu(), atol=atol, rtol=0.0):
                return False, f"{name}:{k} changed"
    return True, "all frozen tensors unchanged"


def adapt_model(source, mask, train_loader, val_loader, device, **training_options):
    from ..safeguards import SplitRole, require_role
    from ..training import train_model

    require_role(train_loader, {SplitRole.TARGET_ADAPTATION}, "adaptation")
    require_role(val_loader, {SplitRole.TARGET_VALIDATION}, "adaptation early stopping")
    model = clone_model(source)
    set_selective_trainability(model, mask, train_head=True)
    snapshot = snapshot_frozen(model, mask)
    train_model(model, train_loader, val_loader, device, **training_options)
    ok, message = frozen_unchanged(model, snapshot)
    if not ok:
        raise RuntimeError(message)
    return model, {"ok": ok, "message": message, "frozen_modules_checked": len(snapshot)}
