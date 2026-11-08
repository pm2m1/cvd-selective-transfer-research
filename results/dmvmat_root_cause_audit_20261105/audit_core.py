"""Public-code audit primitives. No datasets, private paths or execution gates.

Imports pure public model functions only; this module never calls data loaders.
"""
from pathlib import Path
import copy
import hashlib
import json
import sys
import numpy as np
import torch

ROOT = Path(__file__).resolve().parent
FOLLOWUP = ROOT.parent / 'label_efficiency_followup_20261105'
sys.path.insert(0, str(FOLLOWUP))
from package_runtime import api
from design import outer_splits, budget_roles, threshold_from_calibration
from experiment import TrainingAdapter
t = api()
from frozen_public.transfer.calibration import relative_geometry, permutation_mmd
torch.set_num_threads(1)


def logical_reference(e):
    """Independent scalar logical specification; no production selector call."""
    if e['geometry_status'] != 'valid':
        return False
    r, u = e['signed_retention'], e['retention_upper']
    if r is None or u is None or not np.isfinite([r, u]).all():
        raise ValueError('INVALID_REFERENCE_GEOMETRY')
    strong = u < .75
    corroborated = e['domain_status'] == 'valid' and e['domain_p'] <= .05 and r < .8 and u < 1.
    return bool(strong or corroborated)


def geometry_reference(s, sy, x, y):
    """Independent NumPy signed-retention point estimate (valid inputs only)."""
    ds = np.mean(s[sy == 1], 0) - np.mean(s[sy == 0], 0)
    dt = np.mean(x[y == 1], 0) - np.mean(x[y == 0], 0)
    unit = ds / np.sqrt(np.sum(ds**2))
    def radius(a, b):
        return sum(np.sqrt(np.sum((a[b == c] - np.mean(a[b == c], 0))**2, 1)).mean()
                   for c in (0, 1)) / 2
    return float(np.dot(dt, unit) / radius(x, y) * radius(s, sy) / np.dot(ds, unit))


def mmd_reference(s, x, permutations=19, seed=12):
    """Independent explicit-kernel/partition implementation for small fixtures."""
    rng = np.random.default_rng(seed)
    s = s[rng.choice(len(s), len(s), replace=False)].astype(float)
    x = x[rng.choice(len(x), len(x), replace=False)].astype(float)
    z = np.concatenate([s, x]); z -= np.mean(z, 0)
    z /= max(np.sqrt(np.mean(np.sum(z*z, 1))), 1e-8*np.sqrt(z.shape[1]))
    kernel = np.array([[sum(np.exp(-np.sum((a-b)**2)/(2*h*h)) for h in [.5, 1, 2, 4])/4
                        for b in z] for a in z])
    n, m = len(s), len(x)
    def value(idx):
        other = np.array([i for i in range(n+m) if i not in set(idx)])
        return max(0., float(kernel[np.ix_(idx, idx)].mean()+kernel[np.ix_(other, other)].mean()
                             -2*kernel[np.ix_(idx, other)].mean()))
    observed = value(np.arange(n))
    null = np.array([value(rng.permutation(n+m)[:n]) for _ in range(permutations)])
    return observed, float((1+np.sum(null >= observed-1e-12))/(permutations+1))


def state_hash(model):
    h = hashlib.sha256()
    for name, p in model.state_dict().items():
        h.update(name.encode()); h.update(p.detach().cpu().numpy().tobytes())
    return h.hexdigest()


def module_counts(model):
    return {k: sum(p.numel() for p in m.parameters()) for k, m in model.selectable_modules().items()}


def population(rng, n, prevalence=.2, shift=0., reverse=False):
    """Invented Gaussian features, Bernoulli labels; NOT a clinical simulation."""
    y = (rng.random(n) < prevalence).astype(int)
    delta = np.zeros(sum(t.VIEWS.values())); delta[[0,4,6,10,14]] = [1.5,-1.2,.8,.3,-.6]
    if reverse: delta = -delta
    x = rng.normal(size=(n,len(delta))) + (y[:,None]-.5)*delta
    x[:,[0,4,6]] += shift
    views = {}; start = 0
    for k, d in t.VIEWS.items():
        views[k] = x[:,start:start+d].astype('float32'); start += d
    return views, y


def invented_adapter_data(seed=101, source_n=384, target_n=150):
    rng = np.random.default_rng(seed); data = {}
    for role, n in [('source_train',source_n),('source_validation',128),('target_pool',target_n)]:
        views, y = population(rng,n)
        data[role+'__y'] = y
        data[role+'__ids'] = np.array([f'INVENTED_{role}_{i}' for i in range(n)])
        data.update({role+'__'+k:v for k,v in views.items()})
    return data


def public_snapshot():
    """Explicit public-source allowlist only. No directory traversal."""
    names = ['experiment.py','design.py','results_report.py','package_runtime.py','protocol_v1.json',
             'local_execution.py','PUBLIC_PACKAGE_MANIFEST.json','VENDOR_BINDINGS.json',
             'vendor/train_exploratory_candidates.py','vendor/compute_classification_metrics.py',
             'vendor/frozen_public/models/multiview_mlp.py','vendor/frozen_public/transfer/adapt.py',
             'vendor/frozen_public/transfer/calibration.py','vendor/frozen_public/transfer/scores.py',
             'vendor/frozen_public/evaluation.py','vendor/frozen_public/safeguards.py']
    result = {str(Path('results/label_efficiency_followup_20261105')/n):
              hashlib.sha256((FOLLOWUP/n).read_bytes()).hexdigest() for n in names}
    stage = ROOT.parent/'supervisor_metrics_and_improvement_20261104/public_development_staging_20261104'
    for name in ['train_exploratory_candidates.py','compute_classification_metrics.py']:
        p = stage/'experiment_tools'/name
        result[str(p.relative_to(ROOT.parents[1]))] = hashlib.sha256(p.read_bytes()).hexdigest()
    return result


class GradientRecorder:
    """Synthetic-only instrumentation around the exact production AdamW."""
    def __init__(self, model):
        self.model = model; self.records = []; self.original = torch.optim.AdamW
    def __enter__(self):
        context = self
        class RecordedAdamW(context.original):
            def __init__(self, params, *args, **kwargs):
                params = list(params)
                context.optimizer_ids = {id(p) for p in params}
                super().__init__(params, *args, **kwargs)
            def step(self, *args, **kwargs):
                grads = {}
                for name, module in {**context.model.selectable_modules(),'head':context.model.head}.items():
                    grads[name] = float(sum(float(p.grad.square().sum()) for p in module.parameters()
                                            if p.grad is not None)**.5)
                context.records.append(grads)
                return super().step(*args, **kwargs)
        torch.optim.AdamW = RecordedAdamW
        return self
    def __exit__(self, *args):
        torch.optim.AdamW = self.original


def epoch_zero_demonstration():
    """Analytic conflict fixture: training asks for reversal; stopping supports source.

    Proposed gate is an isolated checkpoint comparison, NOT a frozen-code patch.
    """
    class OneWeight(torch.nn.Module):
        def __init__(self):
            super().__init__(); self.w = torch.nn.Parameter(torch.tensor(2.))
        def forward(self, x): return x['x'].flatten()*self.w
    x = np.tile(np.array([-1.,1.]),32).astype('float32')
    good = (x>0).astype(int)
    fit = t.Encoded({'x':x[:,None]},1-good,'target_adaptation')
    stop = t.Encoded({'x':x[:,None]},good,'target_validation')
    model = OneWeight(); initial = state_hash(model)
    with torch.no_grad(): bce0 = float(torch.nn.functional.binary_cross_entropy_with_logits(model(stop.views),stop.y))
    t.seed(11); trace = t.fit(model,fit,stop,10,.03)
    bce1 = trace['restored_unweighted_validation_BCE']
    return {'initial_bce':bce0,'selected_bce':bce1,'selected_epoch':trace['selected_epoch'],
            'production_changed_source':state_hash(model)!=initial,
            'proposed_epoch_zero_gate_would_choose':0 if bce0 <= bce1 else trace['selected_epoch'],
            'status':'SYNTHETIC_DESIGN_COUNTEREXAMPLE_NOT_SPECIFICATION_BUG'}
