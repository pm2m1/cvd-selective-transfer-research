"""Isolated epoch-zero option. Original target fit is imported without modification."""
import copy
import hashlib
import random
import pickle
import numpy as np
import torch
from retained_runtime import api
from local_execution import need
t=api()


def state_hash(model):
    h=hashlib.sha256()
    for name,value in model.state_dict().items():
        h.update(name.encode());h.update(str(value.dtype).encode());h.update(str(tuple(value.shape)).encode())
        h.update(value.detach().cpu().contiguous().numpy().tobytes())
    return h.hexdigest()


def rng_hash():
    return hashlib.sha256(pickle.dumps((random.getstate(),np.random.get_state(),
                         torch.random.get_rng_state().numpy().tobytes()),protocol=4)).hexdigest()


def stopping_bce(model,stop):
    mode=model.training;before=state_hash(model);rng=rng_hash()
    model.eval()
    with torch.no_grad():
        value=float(torch.nn.functional.binary_cross_entropy_with_logits(model(stop.views),stop.y))
    model.train(mode)
    need(state_hash(model)==before and rng_hash()==rng,'EPOCH_ZERO_EVALUATION_MUTATED_STATE_OR_RNG')
    need(np.isfinite(value),'NONFINITE_INITIAL_STOPPING_LOSS')
    return value


def fit_epoch_zero(model,train,val,epochs,lr,patience=5):
    """Target-only copy of frozen BCE fit; only initial checkpoint eligibility differs.

    No initial patience increment. Subsequent non-improvements increment bad in
    exactly the old way; hence Arm B may stop sooner than Arm A.
    """
    need(train.role=='target_adaptation' and val.role=='target_validation','FORBIDDEN_TRAINING_OR_VALIDATION_ROLE')
    optimizer=torch.optim.AdamW([p for p in model.parameters() if p.requires_grad],lr=lr,weight_decay=1e-4)
    best=copy.deepcopy(model.state_dict());initial_sha=state_hash(model);bestloss=stopping_bce(model,val)
    initial_loss=bestloss;bad=0;curve=[];best_epoch=0
    batches=t.loader(train,True,int(torch.initial_seed()))
    for epoch in range(epochs):
        model.train();total=0.;count=0
        for x,y in batches:
            optimizer.zero_grad();z=model(x);value=t.loss_value(z,y,'bce',None)
            need(bool(torch.isfinite(value)),'NONFINITE_OPTIMIZATION')
            value.backward();optimizer.step();total+=float(value.detach())*len(y);count+=len(y)
        model.eval()
        with torch.no_grad():
            p=t.prob(model,val);vl=float(torch.nn.functional.binary_cross_entropy_with_logits(model(val.views),val.y))
        with torch.no_grad():train_bce=float(torch.nn.functional.binary_cross_entropy_with_logits(model(train.views),train.y))
        m=t.metrics(val.y.numpy(),p);curve.append({'epoch':epoch+1,'train_objective':total/count,
            'train_unweighted_bce':train_bce,'validation_bce':vl,'validation_ap':m['ap'],
            'validation_auroc':m['auroc'],'validation_brier':m['brier']})
        if vl<bestloss-1e-5:bestloss=vl;best=copy.deepcopy(model.state_dict());bad=0;best_epoch=epoch+1
        else:bad+=1
        if bad>=patience:break
    model.load_state_dict(best)
    return {'curve':curve,'selected_epoch':best_epoch,'stopped_epoch':len(curve),
            'restored_unweighted_validation_BCE':bestloss,'training_positive_weight':None,
            'epoch_zero_bce':initial_loss,'epoch_zero_eligible':True,
            'epoch_zero_candidate':{'epoch':0,'stopping_bce':initial_loss,'state_sha256':initial_sha}}


class UpdateTrace:
    """In-process paired audit; state hashes/gradients are private in real runs."""
    def __init__(self,model):
        self.model=model;self.original=torch.optim.AdamW;self.updates=[]
    def __enter__(self):
        ctx=self
        class TracedAdamW(ctx.original):
            def __init__(self,params,*args,**kwargs):
                params=list(params)
                names={id(p):name for name,p in ctx.model.named_parameters()}
                ctx.parameter_names=[names[id(p)] for p in params]
                need({id(p) for p in params}=={id(p) for p in ctx.model.parameters() if p.requires_grad},'OPTIMIZER_PARAMETER_MISMATCH')
                super().__init__(params,*args,**kwargs)
                ctx.initial_optimizer={'state_entries':len(self.state),'parameter_names':ctx.parameter_names,
                    'groups':[{k:v for k,v in g.items() if k!='params'} for g in self.param_groups]}
            def step(self,*args,**kwargs):
                gradient=float(sum(float(p.grad.square().sum()) for p in ctx.model.parameters() if p.grad is not None)**.5)
                result=super().step(*args,**kwargs)
                ctx.updates.append({'state_sha256':state_hash(ctx.model),'rng_sha256':rng_hash(),'gradient_norm':gradient})
                return result
        torch.optim.AdamW=TracedAdamW
        return self
    def __exit__(self,*args):torch.optim.AdamW=self.original


def drift(model,source):
    result={}
    for name,module in {**model.selectable_modules(),'head':model.head}.items():
        origin=source.head if name=='head' else source.selectable_modules()[name]
        x=torch.cat([p.detach().flatten() for p in module.parameters()])
        z=torch.cat([p.detach().flatten() for p in origin.parameters()])
        result[name]=float(torch.linalg.vector_norm(x-z)/max(float(torch.linalg.vector_norm(z)),1e-12))
    return result


def paired_fit(source,fit,stop,seed,protocol):
    """Calls exact frozen A and isolated B; fail closed on trajectory mismatch."""
    models={};traces={};records={};initial=state_hash(source)
    for arm in ['A','B']:
        t.seed(seed);model=copy.deepcopy(source)
        t.set_selective_trainability(model,{k:True for k in model.selectable_modules()})
        need(state_hash(model)==initial,'PAIRED_INITIAL_STATE_MISMATCH')
        zero_bce=stopping_bce(model,stop)
        with UpdateTrace(model) as capture:
            if arm=='A':
                trace=t.fit(model,fit,stop,protocol['target_epochs'],protocol['target_lr'],
                            loss='bce',patience=protocol['patience'])
            else:
                trace=fit_epoch_zero(model,fit,stop,protocol['target_epochs'],protocol['target_lr'],protocol['patience'])
        trace.update(initial_state_sha256=initial,initial_stopping_bce=zero_bce,
                     selected_state_sha256=state_hash(model),relative_layer_drift=drift(model,source))
        if arm=='B' and trace['selected_epoch']==0:
            need(state_hash(model)==initial,'EPOCH_ZERO_RESTORATION_MISMATCH')
        models[arm]=model;traces[arm]=trace;records[arm]=capture
    need(records['A'].initial_optimizer==records['B'].initial_optimizer,'PAIRED_OPTIMIZER_INITIALIZATION_MISMATCH')
    common=min(len(records['A'].updates),len(records['B'].updates))
    need(records['A'].updates[:common]==records['B'].updates[:common],'PAIRED_UPDATE_OR_RNG_MISMATCH')
    epochs=min(len(traces['A']['curve']),len(traces['B']['curve']))
    need(traces['A']['curve'][:epochs]==traces['B']['curve'][:epochs],'PAIRED_CHECKPOINT_SCORE_MISMATCH')
    need(state_hash(source)==initial,'CACHED_SOURCE_MUTATED')
    verification={'initial_state_sha256':initial,'initial_optimizer':records['A'].initial_optimizer,
        'matched_update_prefix':common,'matched_epoch_prefix':epochs,
        'arm_update_counts':{a:len(records[a].updates) for a in ['A','B']},
        'optimizer_update_traces':{a:records[a].updates for a in ['A','B']},
        'source_unchanged':True,'different_stopped_epochs_permitted_due_to_patience':True}
    return models,traces,verification
