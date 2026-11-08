"""NEW exploratory development training; no held-out input or evaluation mode."""
import os
for _k in ('OMP_NUM_THREADS','MKL_NUM_THREADS','OPENBLAS_NUM_THREADS','VECLIB_MAXIMUM_THREADS'):os.environ[_k]='1'
from pathlib import Path
import sys,json,copy,random,math
import numpy as np
import torch
from torch import nn
from torch.utils.data import DataLoader,Dataset
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import GradientBoostingClassifier
from local_execution import need,descriptor,load_json,write_json,sha,cli,exclusive_output
from compute_classification_metrics import metrics,select_validation_threshold,summarize
from frozen_public.models.multiview_mlp import MultiViewRiskNet
from frozen_public.transfer.adapt import set_selective_trainability,snapshot_frozen,frozen_unchanged
from frozen_public.evaluation import ModuleRepresentations
from frozen_public.safeguards import SplitRole
from frozen_public.transfer.calibration import CalibrationConfig,calibrate_modules,calibrated_mask
PURPOSE='new_exploratory_development_training_no_test_v1'
HELPER_BINDINGS_SHA='026d7cc86cd3460806414af3941ea429aa4520e89cd71ebeff1b43f028934d8d'
VIEWS={'background':4,'haemodynamic':2,'metabolic':3,'behaviour':4,'comorbidity_medication':6}
ROLES=('source_train','source_validation','target_pool','target_validation')
COUNTS={'source_train':(1744,65),'source_validation':(581,21),'target_pool':(679,49),'target_validation':(171,13)}
class Encoded(Dataset):
    def __init__(self,views,y,role):
        self.views={k:torch.tensor(v,dtype=torch.float32) for k,v in views.items()};self.y=torch.tensor(y,dtype=torch.float32);self.role=role
    def __len__(self):return len(self.y)
    def __getitem__(self,i):return {k:v[i] for k,v in self.views.items()},self.y[i]
class CompactRiskNet(MultiViewRiskNet):
    def __init__(self):
        super().__init__(VIEWS,8);self.fusion1=nn.Sequential(nn.Linear(40,32),nn.ReLU(),nn.LayerNorm(32));self.fusion2=nn.Sequential(nn.Linear(32,16),nn.ReLU(),nn.LayerNorm(16));self.head=nn.Linear(16,1)
def seed(s):random.seed(s);np.random.seed(s);torch.manual_seed(s);torch.use_deterministic_algorithms(True)
def loader(ds,shuffle=False,s=0):return DataLoader(ds,batch_size=64,shuffle=shuffle,num_workers=0,generator=torch.Generator().manual_seed(s))
def prob(model,ds):
    model.eval()
    with torch.no_grad():return torch.sigmoid(model(ds.views)).numpy()
def loss_value(z,y,kind,pos_weight=None):
    b=nn.functional.binary_cross_entropy_with_logits(z,y,reduction='none')
    if kind=='bce':return b.mean()
    if kind=='weighted_bce':
        need(pos_weight is not None and math.isfinite(pos_weight) and pos_weight>0,'LOSS_WEIGHT_INVALID')
        return (b*torch.where(y==1,torch.tensor(pos_weight),torch.tensor(1.))).mean()
    if kind=='focal':
        pt=torch.where(y==1,torch.sigmoid(z),torch.sigmoid(-z));return (((1-pt)**2)*b).mean()
    raise ValueError('UNKNOWN_LOSS')
def fit(model,train,val,epochs,lr,loss='bce',anchor=None,shrink=0.,patience=5):
    need(train.role in ('source_train','target_adaptation') and val.role==('source_validation' if train.role=='source_train' else 'target_validation'),'FORBIDDEN_TRAINING_OR_VALIDATION_ROLE')
    weight=(len(train.y)-float(train.y.sum()))/float(train.y.sum()) if loss=='weighted_bce' else None
    optimizer=torch.optim.AdamW([p for p in model.parameters() if p.requires_grad],lr=lr,weight_decay=1e-4)
    best=copy.deepcopy(model.state_dict());bestloss=float('inf');bad=0;curve=[];best_epoch=0
    anchors=dict(anchor.named_parameters()) if anchor is not None else {}
    batches=loader(train,True,int(torch.initial_seed()))
    for epoch in range(epochs):
        model.train();total=0.;count=0
        for x,y in batches:
            optimizer.zero_grad();z=model(x);value=loss_value(z,y,loss,weight)
            if shrink:
                terms=[(p-anchors[n].detach()).square().sum() for n,p in model.named_parameters() if not n.startswith('head.') and p.requires_grad]
                n=sum(p.numel() for n,p in model.named_parameters() if not n.startswith('head.') and p.requires_grad)
                value=value+shrink*sum(terms)/max(n,1)
            need(bool(torch.isfinite(value)),'NONFINITE_OPTIMIZATION')
            value.backward();optimizer.step();total+=float(value.detach())*len(y);count+=len(y)
        model.eval()
        with torch.no_grad():
            p=prob(model,val);vl=float(nn.functional.binary_cross_entropy_with_logits(model(val.views),val.y))
        with torch.no_grad():train_bce=float(nn.functional.binary_cross_entropy_with_logits(model(train.views),train.y))
        m=metrics(val.y.numpy(),p);curve.append({'epoch':epoch+1,'train_objective':total/count,'train_unweighted_bce':train_bce,'validation_bce':vl,'validation_ap':m['ap'],'validation_auroc':m['auroc'],'validation_brier':m['brier']})
        if vl<bestloss-1e-5:bestloss=vl;best=copy.deepcopy(model.state_dict());bad=0;best_epoch=epoch+1
        else:bad+=1
        if bad>=patience:break
    model.load_state_dict(best)
    return {'curve':curve,'selected_epoch':best_epoch,'stopped_epoch':len(curve),'restored_unweighted_validation_BCE':bestloss,'training_positive_weight':weight}

def validate_bundle(data,manifest,synthetic=False):
    expected=set()
    for role in ROLES:expected|={role+'__ids',role+'__y'}|{role+'__'+v for v in VIEWS}
    expected|={f'draw_{i}' for i in range(10)}
    need(set(data)==expected,'DEVELOPMENT_BUNDLE_FIELDS_INVALID') # Test rows/extra future features forbidden.
    memberships={}
    for role in ROLES:
        ids=data[role+'__ids'];y=data[role+'__y'];n,e=(len(y),int(y.sum())) if synthetic else COUNTS[role]
        need(ids.ndim==1 and ids.dtype.kind=='U' and len(ids)==n and len(set(ids.tolist()))==n and np.isin(y,[0,1]).all() and y.shape==(n,) and int(y.sum())==e,'DEVELOPMENT_MEMBERSHIP_INVALID')
        memberships[role]=set(ids.tolist())
        for v,dim in VIEWS.items():
            x=data[role+'__'+v];need(x.shape==(n,dim) and np.isfinite(x).all(),'DEVELOPMENT_FEATURES_INVALID')
    need(sum(map(len,memberships.values()))==len(set.union(*memberships.values())),'DEVELOPMENT_ROLES_OVERLAP')
    for i in range(10):
        ix=data[f'draw_{i}'];need(ix.ndim==1 and ix.dtype.kind in 'iu' and len(set(ix.tolist()))==len(ix) and (ix>=0).all() and (ix<len(data['target_pool__y'])).all(),'DRAW_INDEX_INVALID')
        if not synthetic:need(len(ix)==100 and int(data['target_pool__y'][ix].sum())==25,'ADAPTATION_BUDGET_INVALID')
    need(manifest['preprocessing_fit_role']=='source_train' and manifest['protocol']=='public-haalsi-mhas-v2' and manifest['test_rows_included'] is False,'PREPROCESSING_OR_TEST_LEAKAGE')
    return data

def ds(data,role,ix=None):
    x={v:data[role+'__'+v] if ix is None else data[role+'__'+v][ix] for v in VIEWS};y=data[role+'__y'] if ix is None else data[role+'__y'][ix]
    return Encoded(x,y,'target_adaptation' if role=='target_pool' else role)
def representations(model,part,role):
    model.eval()
    with torch.no_grad():_,f=model(part.views,return_features=True)
    return ModuleRepresentations({k:v.numpy() for k,v in f.items()},part.y.numpy(),role)
def candidate_plan():
    base={'architecture':'original','source_epochs':30,'target_epochs':20,'source_lr':.001,'target_lr':.001,'loss':'bce','strategy':'full','tier':1}
    changes=[('matched_control',{}),('head_only',{'strategy':'head'}),('logical',{'strategy':'logical'}),('compact_full',{'architecture':'compact'}),('target_lr_1e4',{'target_lr':.0001}),('target_lr_3e4',{'target_lr':.0003}),('longer_epochs',{'source_epochs':50,'target_epochs':30,'tier':2}),('source_lr_1e4',{'source_lr':.0001,'tier':2}),('source_lr_3e4',{'source_lr':.0003,'tier':2}),('weighted_target_bce',{'loss':'weighted_bce','tier':2}),('focal_target',{'loss':'focal','tier':2}),('fixed_fusion2',{'strategy':'fusion2','tier':2}),('fixed_both_fusion',{'strategy':'both_fusion','tier':2}),('source_shrinkage',{'strategy':'shrinkage','tier':2}),('target_logistic',{'strategy':'logistic','tier':1}),('target_gbt',{'strategy':'gbt','tier':2})]
    return [{'id':name,**base,**d} for name,d in changes]
def run(data,candidates,out,synthetic=False):
    torch.set_num_threads(1);source_train=ds(data,'source_train');source_val=ds(data,'source_validation');tv=ds(data,'target_validation');cache={};rows=[];preds={};curves={}
    for c in candidates:
        key=(c['architecture'],c['source_epochs'],c['source_lr'])
        if c['strategy'] not in ('logistic','gbt') and key not in cache:
            seed(20261025);model=MultiViewRiskNet(VIEWS) if c['architecture']=='original' else CompactRiskNet()
            tr=fit(model,source_train,source_val,c['source_epochs'],c['source_lr']);cache[key]=(model,tr)
            source_name='source_'+str(len(cache))
            with (out/f'{source_name}.pt').open('xb') as stream:torch.save(model.state_dict(),stream)
            curves[source_name]={'architecture':c['architecture'],'maximum_epochs':c['source_epochs'],'learning_rate':c['source_lr'],'checkpoint_sha256':sha(out/f'{source_name}.pt'),**tr}
        for draw in range(10):
            seed(20261025+draw);adapt=ds(data,'target_pool',data[f'draw_{draw}']);strategy=c['strategy'];effect={};trace=None
            if strategy in ('logistic','gbt'):
                flat=lambda x:np.concatenate([x.views[v].numpy() for v in VIEWS],axis=1)
                model=LogisticRegression(C=1.,max_iter=1000,random_state=20261025+draw) if strategy=='logistic' else GradientBoostingClassifier(n_estimators=100,learning_rate=.05,max_depth=2,random_state=20261025+draw)
                model.fit(flat(adapt),adapt.y.numpy());p=model.predict_proba(flat(tv))[:,1];trainable=int(model.coef_.size+model.intercept_.size) if strategy=='logistic' else None;total=trainable;mask=None
            else:
                source=cache[key][0];model=copy.deepcopy(source);names=list(model.selectable_modules());mask={n:strategy in ('full','shrinkage') or strategy=='fusion2' and n=='fusion2' or strategy=='both_fusion' and n in ('fusion1','fusion2') for n in names}
                if strategy=='logical':
                    cfg=CalibrationConfig(permutations=9 if synthetic else 199,bootstraps=19 if synthetic else 199)
                    ev=calibrate_modules(representations(source,source_val,SplitRole.SOURCE_VALIDATION),representations(source,adapt,SplitRole.TARGET_ADAPTATION),config=cfg,max_samples=128,seed=20261025+draw)
                    mask,reasons=calibrated_mask(ev,'calibrated_logical',cfg);effect={'selector_reasons':reasons,'selector_evidence':ev}
                set_selective_trainability(model,mask);before=snapshot_frozen(model,mask)
                trace=fit(model,adapt,tv,c['target_epochs'],c['target_lr'],c['loss'],source if strategy=='shrinkage' else None,.01 if strategy=='shrinkage' else 0.)
                need(frozen_unchanged(model,before)[0],'FROZEN_PARAMETER_CHANGED')
                p=prob(model,tv);trainable=sum(x.numel() for x in model.parameters() if x.requires_grad);total=sum(x.numel() for x in model.parameters())
                with (out/f'{c["id"]}_draw_{draw}.pt').open('xb') as f:torch.save(model.state_dict(),f)
            fixed=metrics(tv.y.numpy(),p,.5);threshold=select_validation_threshold(tv.y.numpy(),p);selected=metrics(tv.y.numpy(),p,threshold)
            rows.append({'candidate':c,'draw':draw,'scope':'SYNTHETIC_ONLY' if synthetic else 'EXPLORATORY_TARGET_DEVELOPMENT_ONLY','trainable_parameters':trainable,'total_parameters':total,'mask':mask,'selector':effect,'fixed_0_5':fixed,'validation_selected_threshold':selected,'threshold_estimate_is_resubstitution':True,'training':trace})
            preds[f'{c["id"]}__draw_{draw}']=p
    # The probability payload is private development data, never public.
    with (out/'development_predictions.private.npz').open('xb') as f:np.savez_compressed(f,validation_labels=tv.y.numpy(),validation_ids=data['target_validation__ids'],**preds)
    stats={}
    for c in candidates:
        rr=[r for r in rows if r['candidate']['id']==c['id']];stats[c['id']]={'fixed_0_5':summarize([r['fixed_0_5'] for r in rr]),'validation_selected':summarize([r['validation_selected_threshold'] for r in rr])}
    rank=sorted(stats,key=lambda k:(-stats[k]['fixed_0_5']['ap']['mean'],k))
    report={'status':'SYNTHETIC_ONLY' if synthetic else 'PRIVATE_EXPLORATORY_DEVELOPMENT_NOT_EXTERNAL_VALIDATION','rows':rows,'summary':stats,'descriptive_development_AP_order':rank,'source_training_curves':curves,'test_predictions_generated':False,'adaptation_draws_are_not_independent_validations':True}
    write_json(out/'exploratory_development.private.json',report)
    _curves(report,out)
    return report

def _curves(report,out):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    fig,ax=plt.subplots(1,2,figsize=(10,4))
    for row in report['rows']:
        if row['draw']!=0 or row['training'] is None:continue
        curve=row['training']['curve'];name=row['candidate']['id']
        ax[0].plot([x['epoch'] for x in curve],[x['validation_ap'] for x in curve],label=name)
        ax[1].plot([x['epoch'] for x in curve],[x['validation_bce'] for x in curve],label=name)
    ax[0].set(xlabel='Epoch',ylabel='Development validation AP');ax[1].set(xlabel='Epoch',ylabel='Development validation BCE');ax[0].legend(fontsize=6);fig.suptitle(report['status']+' — draw 0 illustration; not independent test');fig.tight_layout()
    with (out/'development_learning_curves.private.svg').open('xb') as f:fig.savefig(f,format='svg')
    with (out/'development_learning_curves.private.png').open('xb') as f:fig.savefig(f,format='png',dpi=140)
    plt.close(fig)
def execute(c,out):
    root=Path(__file__).resolve().parent
    need(sha(root/'FROZEN_PUBLIC_HELPER_BINDINGS.json')==HELPER_BINDINGS_SHA,'PUBLIC_HELPER_LEDGER_MISMATCH')
    for name,h in load_json(root/'FROZEN_PUBLIC_HELPER_BINDINGS.json').items():need(sha(root/'frozen_public'/name)==h,'ADOPTED_SELECTOR_CODE_MISMATCH')
    need(c['schema']=='exploratory-development-v1' and c['no_test_evaluation'] is True,'EXPLORATORY_CONTRACT_INVALID')
    manifest=load_json(descriptor(c['development_manifest']));bp=descriptor(c['development_bundle']);need(manifest['bundle_sha256']==sha(bp),'DEVELOPMENT_MANIFEST_MISMATCH')
    need(manifest['preparation_script_sha256']==sha(Path(__file__).with_name('prepare_development_inputs.py')),'DEVELOPMENT_EXPORT_CODE_MISMATCH')
    need(manifest['source_assignments_sha256']=='6dfcb3271cff9d0ee122ac4667d5d4fe600334b3927778e0eaa5d6441b3d9866','ORIGINAL_DRAW_BINDING_MISMATCH')
    with np.load(bp,allow_pickle=False) as z:data={k:z[k].copy() for k in z.files}
    validate_bundle(data,manifest)
    assignments=load_json(descriptor(c['original_assignments']))
    need(c['original_assignments']['sha256']==manifest['source_assignments_sha256'],'ASSIGNMENT_FILE_BINDING_MISMATCH')
    for role in ROLES:
        group=assignments['source_partitions'] if role.startswith('source_') else assignments['target_partitions']
        key='target_adaptation_pool' if role=='target_pool' else role
        need(set(data[role+'__ids'].tolist())==set(group[key]),'ORIGINAL_DEVELOPMENT_MEMBERSHIP_MISMATCH')
    for i in range(10):
        actual=set(data['target_pool__ids'][data[f'draw_{i}']].tolist())
        need(actual==set(assignments['adaptation_draws'][str(i)]['primary_25_75']),'ORIGINAL_DRAW_MEMBERSHIP_MISMATCH')
    wanted=c['candidates'];known={x['id']:x for x in candidate_plan()};need(isinstance(wanted,list) and wanted and len(set(wanted))==len(wanted) and set(wanted)<=set(known) and len(wanted)<=16,'CANDIDATE_PLAN_INVALID')
    need(c['phase'] in [1,2] and all(known[n]['tier']<=c['phase'] for n in wanted),'SECOND_TIER_REQUIRES_SEPARATE_PROTOCOL_BINDING')
    run(data,[known[n] for n in wanted],out)
    write_json(out/'execution_provenance.private.json',{'config':c,'script_sha256':sha(__file__),'numpy':np.__version__,'torch':torch.__version__,'device':'cpu','threads':1,'test_inference':False,'disclosure_cleared':False})
def invented_bundle():
    rng=np.random.default_rng(20261104);data={}
    sizes={'source_train':(60,20),'source_validation':(30,10),'target_pool':(40,12),'target_validation':(30,9)}
    for role,(n,e) in sizes.items():
        y=np.r_[np.ones(e),np.zeros(n-e)].astype(int);data[role+'__y']=y;data[role+'__ids']=np.array([f'SYNTHETIC_{role}_{i}' for i in range(n)])
        for name,d in VIEWS.items():data[role+'__'+name]=(rng.normal(size=(n,d))+.15*y[:,None]).astype('float32')
    for i in range(10):data[f'draw_{i}']=rng.choice(40,20,replace=False)
    return data
def demo(output):
    data=invented_bundle();c=[{**x,'source_epochs':2,'target_epochs':2} for x in candidate_plan() if x['id'] in ('matched_control','head_only','compact_full','logical','target_logistic')]
    with exclusive_output(output,False) as out:run(data,c,out,True)
if __name__=='__main__':sys.exit(cli(PURPOSE,execute,demo))
