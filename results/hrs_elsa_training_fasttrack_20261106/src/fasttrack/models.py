"""Reused five-view network and frozen selector; isolated new training loop."""
import copy
import hashlib
import random
import time
import os
import numpy as np
import torch
from torch import nn
from sklearn.linear_model import LogisticRegression,SGDClassifier
from sklearn.ensemble import HistGradientBoostingClassifier
from dmv_mat_cvd.models.multiview_mlp import MultiViewRiskNet
from dmv_mat_cvd.transfer.adapt import set_selective_trainability,snapshot_frozen,frozen_unchanged
from dmv_mat_cvd.transfer.calibration import CalibrationConfig,calibrate_modules,calibrated_mask
from dmv_mat_cvd.evaluation import ModuleRepresentations
from dmv_mat_cvd.safeguards import SplitRole
from .preprocessing import flat
from .contracts import need

METHODS=('source_logistic','source_regularized','source_boosting','source_dmvmat','head','full','selective')


def seed_all(seed):
    os.environ.setdefault('LOKY_MAX_CPU_COUNT','1')
    random.seed(seed);np.random.seed(seed);torch.manual_seed(seed)
    torch.set_num_threads(1);torch.use_deterministic_algorithms(True)


def device_checked(name):
    need(name in ('cpu','mps'),'UNSUPPORTED_DEVICE')
    need(name!='mps' or torch.backends.mps.is_available(),'MPS_UNAVAILABLE_NO_SILENT_FALLBACK')
    return torch.device(name)


def tensor_views(views,device):
    return {k:torch.tensor(v,dtype=torch.float32,device=device) for k,v in views.items()}


def weight_hash(model):
    h=hashlib.sha256()
    for k,v in model.state_dict().items():h.update(k.encode());h.update(v.detach().cpu().numpy().tobytes())
    return h.hexdigest()


def probability(model,views,device):
    model.to(device).eval()
    with torch.no_grad():return torch.sigmoid(model(tensor_views(views,device))).cpu().numpy()


def fit(model,train,y,stop,ys,*,train_role,stop_role,epochs,lr,patience,seed,device,epoch_zero):
    need((train_role,stop_role) in [('source_train','source_stop'),('target_fit','target_stop')],'TRAINING_OR_STOP_ROLE_FORBIDDEN')
    need(len(np.unique(y))==2,'INSUFFICIENT_TRAINING_CLASS_SUPPORT')
    need(epochs>0 and patience>0 and lr>0,'INVALID_OPTIMIZATION_PLAN')
    model.to(device);x=tensor_views(train,device);sx=tensor_views(stop,device)
    y=torch.tensor(y,dtype=torch.float32,device=device);ys=torch.tensor(ys,dtype=torch.float32,device=device)
    parameters=[p for p in model.parameters() if p.requires_grad]
    optimizer=torch.optim.AdamW(parameters,lr=lr,weight_decay=1e-4)
    need({id(p) for g in optimizer.param_groups for p in g['params']}=={id(p) for p in model.parameters() if p.requires_grad},'OPTIMIZER_MASK_MISMATCH')
    loss=nn.BCEWithLogitsLoss()
    def stop_loss():
        model.eval()
        with torch.no_grad():return float(loss(model(sx),ys).cpu())
    best=copy.deepcopy(model.state_dict());best_loss=stop_loss() if epoch_zero else float('inf')
    selected=0 if epoch_zero else None;bad=0;curve=[]
    gen=torch.Generator().manual_seed(seed)
    start=time.perf_counter()
    for epoch in range(1,epochs+1):
        model.train()
        order=torch.randperm(len(y),generator=gen).tolist();total=0.
        for offset in range(0,len(y),64):
            ix=order[offset:offset+64]
            optimizer.zero_grad(set_to_none=True);value=loss(model({k:v[ix] for k,v in x.items()}),y[ix])
            need(bool(torch.isfinite(value)),'NONFINITE_OPTIMIZATION')
            value.backward();optimizer.step();total+=float(value.detach().cpu())*len(ix)
        vl=stop_loss();need(np.isfinite(vl),'NONFINITE_STOPPING_LOSS')
        curve.append({'epoch':epoch,'training_bce':total/len(y),'stopping_bce':vl})
        if vl<best_loss-1e-5:best_loss=vl;best=copy.deepcopy(model.state_dict());selected=epoch;bad=0
        else:bad+=1
        if bad>=patience:break
    model.load_state_dict(best)
    return {'selected_epoch':selected,'stopped_epoch':len(curve),'epoch_zero_eligible':epoch_zero,
            'restored_stopping_bce':best_loss,'curve':curve,'elapsed_seconds':time.perf_counter()-start}


def representations(model,views,y,role,device):
    model.to(device).eval()
    with torch.no_grad():_,features=model(tensor_views(views,device),return_features=True)
    return ModuleRepresentations({k:v.detach().cpu().numpy() for k,v in features.items()},np.asarray(y),role)


def train_models(views,labels,config,synthetic=False):
    seed_all(config['seed']);device=device_checked(config['device']);trained={};traces={}
    x=flat(views['source_train']);y=labels['source_train']
    need(len(np.unique(y))==2,'SOURCE_TRAINING_NEEDS_BOTH_CLASSES')
    classical={'source_logistic':LogisticRegression(C=1.,max_iter=2000,random_state=config['seed']),
       'source_regularized':SGDClassifier(loss='log_loss',penalty='elasticnet',alpha=.001,l1_ratio=.15,
                                        max_iter=2000,tol=1e-5,random_state=config['seed']),
       'source_boosting':HistGradientBoostingClassifier(max_iter=config['tree_iterations'],learning_rate=.05,
                                       max_leaf_nodes=7,l2_regularization=1.,early_stopping=False,random_state=config['seed'])}
    for name,model in classical.items():
        start=time.perf_counter();model.fit(x,y)
        trained[name]={'kind':'sklearn','model':model}
        traces[name]={'elapsed_seconds':time.perf_counter()-start,'trainable_parameters':int(model.coef_.size+model.intercept_.size) if hasattr(model,'coef_') else None}
    source=MultiViewRiskNet({k:v.shape[1] for k,v in views['source_train'].items()})
    traces['source_dmvmat']=fit(source,views['source_train'],y,views['source_stop'],labels['source_stop'],
        train_role='source_train',stop_role='source_stop',epochs=config['source_epochs'],lr=.001,
        patience=config['patience'],seed=config['seed'],device=device,epoch_zero=False)
    original_hash=weight_hash(source);trained['source_dmvmat']={'kind':'neural','model':copy.deepcopy(source).cpu()}
    total=sum(p.numel() for p in source.parameters());traces['source_dmvmat'].update(total_parameters=total,trainable_parameters=total)
    for name in ('head','full','selective'):
        if len(np.unique(labels['target_fit']))<2:
            traces[name]={'unavailable':'TARGET_FITTING_LABELS_SINGLE_CLASS'};continue
        seed_all(config['seed']);model=copy.deepcopy(source);names=list(model.selectable_modules())
        mask={n:name=='full' for n in names};evidence=None;reasons={}
        if name=='selective' and len(labels['source_stop'])<2:
            reasons={n:'ABSTAIN:insufficient_source_stopping_samples' for n in names}
        elif name=='selective':
            cfg=CalibrationConfig(permutations=config['selector_permutations'],bootstraps=config['selector_bootstraps'])
            evidence=calibrate_modules(representations(source,views['source_stop'],labels['source_stop'],SplitRole.SOURCE_VALIDATION,device),
                representations(source,views['target_fit'],labels['target_fit'],SplitRole.TARGET_ADAPTATION,device),
                config=cfg,max_samples=128,seed=config['seed'])
            mask,reasons=calibrated_mask(evidence,'calibrated_logical',cfg)
        set_selective_trainability(model,mask);before=snapshot_frozen(model,mask)
        trace=fit(model,views['target_fit'],labels['target_fit'],views['target_stop'],labels['target_stop'],
            train_role='target_fit',stop_role='target_stop',epochs=config['target_epochs'],lr=.001,
            patience=config['patience'],seed=config['seed'],device=device,epoch_zero=True)
        need(frozen_unchanged(model,before)[0],'SHARED_PARAMETERS_UPDATED')
        trace.update(mask=mask,selector_reasons=reasons,selector_evidence=evidence,
              total_parameters=total,trainable_parameters=sum(p.numel() for p in model.parameters() if p.requires_grad),
              initial_source_hash=original_hash,selected_state_hash=weight_hash(model),shared_parameters_unchanged=True)
        trained[name]={'kind':'neural','model':model.cpu()};traces[name]=trace
    need(weight_hash(source)==original_hash,'SOURCE_INITIALIZATION_MUTATED')
    return trained,traces


def predict(item,views,device='cpu'):
    if item['kind']=='sklearn':return item['model'].predict_proba(flat(views))[:,1]
    return probability(item['model'],views,device_checked(device))
