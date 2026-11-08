from __future__ import annotations

from copy import deepcopy

import torch
from torch import nn

from .safeguards import SplitRole, require_role


def move_views(views, device):
    return {k: v.to(device) for k, v in views.items()}


def train_model(model, train_loader, val_loader, device, epochs=30, lr=1e-3, patience=8):
    role = require_role(train_loader, {SplitRole.SOURCE_TRAIN, SplitRole.TARGET_ADAPTATION}, "training")
    validation_role = (SplitRole.SOURCE_VALIDATION if role == SplitRole.SOURCE_TRAIN
                       else SplitRole.TARGET_VALIDATION)
    require_role(val_loader, {validation_role}, "early stopping")
    if not len(train_loader.dataset) or not len(val_loader.dataset):
        raise ValueError("Training and validation partitions must be nonempty")
    if epochs < 1 or lr <= 0 or patience < 1:
        raise ValueError("epochs, learning rate and patience must be positive")
    model.to(device)
    opt = torch.optim.AdamW([p for p in model.parameters() if p.requires_grad], lr=lr, weight_decay=1e-4)
    loss_fn = nn.BCEWithLogitsLoss()
    best = deepcopy(model.state_dict())
    best_val = float("inf")
    bad = 0

    for _ in range(epochs):
        model.train()
        for views, y in train_loader:
            views = move_views(views, device)
            y = y.to(device)
            opt.zero_grad()
            logits = model(views)
            loss = loss_fn(logits, y)
            if not torch.isfinite(loss):
                raise FloatingPointError("Nonfinite training loss; check inputs and numerical stability")
            loss.backward()
            opt.step()

        model.eval()
        total, count = 0.0, 0
        with torch.no_grad():
            for views, y in val_loader:
                views = move_views(views, device)
                y = y.to(device)
                loss = loss_fn(model(views), y)
                if not torch.isfinite(loss):
                    raise FloatingPointError("Nonfinite validation loss; check inputs and numerical stability")
                total += float(loss.item()) * len(y)
                count += len(y)
        val_loss = total / max(count, 1)
        if val_loss < best_val - 1e-5:
            best_val = val_loss
            best = deepcopy(model.state_dict())
            bad = 0
        else:
            bad += 1
            if bad >= patience:
                break

    model.load_state_dict(best)
    return model
