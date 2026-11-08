import copy,sys
from pathlib import Path
import numpy as np,pytest,torch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from train_exploratory_candidates import *
from local_execution import Rejected
torch.set_num_threads(1)
@pytest.mark.parametrize('constructor,count',[(lambda:MultiViewRiskNet(VIEWS),8033),(CompactRiskNet,2225)])
def test_parameter_counts(constructor,count):assert sum(p.numel() for p in constructor().parameters())==count
@pytest.mark.parametrize('kind',['bce','weighted_bce','focal'])
def test_loss_finite_gradient(kind):
 z=torch.tensor([100.,-100.,0.,1.],requires_grad=True);y=torch.tensor([1.,0.,1.,0.]);v=loss_value(z,y,kind,3.);v.backward();assert torch.isfinite(v) and torch.isfinite(z.grad).all()
def test_no_double_weighted_focal():
 z=torch.tensor([.1,.2]);y=torch.tensor([0.,1.]);assert loss_value(z,y,'focal',100.)==loss_value(z,y,'focal',1.)
def test_bundle_accepts_invented():validate_bundle(invented_bundle(),{'preprocessing_fit_role':'source_train','protocol':'public-haalsi-mhas-v2','test_rows_included':False},True)
@pytest.mark.parametrize('extra',['target_test__y','future_event_date','source_test__ids'])
def test_test_or_future_fields_rejected(extra):
 d=invented_bundle();d[extra]=np.array([1])
 with pytest.raises(Rejected):validate_bundle(d,{},True)
def test_development_overlap_rejected():
 d=invented_bundle();d['target_validation__ids'][0]=d['target_pool__ids'][0]
 with pytest.raises(Rejected):validate_bundle(d,{},True)
def test_wrong_preprocess_role():
 with pytest.raises(Rejected):validate_bundle(invented_bundle(),{'preprocessing_fit_role':'target_validation','protocol':'public-haalsi-mhas-v2','test_rows_included':False},True)
def test_duplicate_draw_rejected():
 d=invented_bundle();d['draw_0'][1]=d['draw_0'][0]
 with pytest.raises(Rejected):validate_bundle(d,{},True)
def test_finite_input_check():
 d=invented_bundle();d['source_train__background'][0,0]=np.nan
 with pytest.raises(Rejected):validate_bundle(d,{},True)
def test_new_small_data_cannot_pass_real_counts():
 with pytest.raises(Rejected):validate_bundle(invented_bundle(),{},False)
def test_head_freezing_and_restored_validation_loss():
 d=invented_bundle();seed(7);m=MultiViewRiskNet(VIEWS);mask={n:False for n in m.selectable_modules()};set_selective_trainability(m,mask);before=snapshot_frozen(m,mask);a=ds(d,'target_pool',d['draw_0']);v=ds(d,'target_validation');tr=fit(m,a,v,3,.001)
 assert frozen_unchanged(m,before)[0] and sum(p.numel() for p in m.parameters() if p.requires_grad)==33
 assert tr['restored_unweighted_validation_BCE']==pytest.approx(min(x['validation_bce'] for x in tr['curve']))
def test_forbidden_role_fit():
 d=invented_bundle();a=ds(d,'target_pool',d['draw_0']);a.role='target_test'
 with pytest.raises(Rejected):fit(MultiViewRiskNet(VIEWS),a,ds(d,'target_validation'),2,.001)
def test_selector_abstains_without_class_support():
 from frozen_public.transfer.calibration import calibrated_mask,CalibrationConfig
 m,r=calibrated_mask({'view':{'geometry_status':'uncertain_source_geometry'}},'calibrated_logical',CalibrationConfig());assert m=={'view':False}
def test_plan_not_cartesian_search():
 p=candidate_plan();assert len(p)==16 and len({x['id'] for x in p})==16 and all(x['target_lr'] in [.0001,.0003,.001] for x in p)
def test_shrinkage_runs_without_changing_endpoint():
 d=invented_bundle();seed(9);m=CompactRiskNet();source=copy.deepcopy(m);tr=fit(m,ds(d,'target_pool',d['draw_0']),ds(d,'target_validation'),2,.001,anchor=source,shrink=.01)
 assert tr['selected_epoch'] in [1,2]
def test_faithful_public_helper_pins():
 import json,hashlib
 root=Path(__file__).resolve().parents[1];j=json.loads((root/'FROZEN_PUBLIC_HELPER_BINDINGS.json').read_text())
 assert all(hashlib.sha256((root/'frozen_public'/p).read_bytes()).hexdigest()==h for p,h in j.items())

def test_more_epochs_do_not_force_extra_optimization_after_patience():
 d=invented_bundle();seed(14);a=CompactRiskNet();b=copy.deepcopy(a)
 seed(14);r1=fit(a,ds(d,'target_pool',d['draw_0']),ds(d,'target_validation'),8,1e-20,patience=2)
 seed(14);r2=fit(b,ds(d,'target_pool',d['draw_0']),ds(d,'target_validation'),20,1e-20,patience=2)
 assert r1['stopped_epoch']==r2['stopped_epoch']==3
 assert all(torch.equal(v,b.state_dict()[k]) for k,v in a.state_dict().items())
