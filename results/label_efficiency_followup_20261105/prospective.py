"""Future independent-cohort registration/evaluation; never an old-test adapter."""
import datetime
import numpy as np
from local_execution import need,descriptor,load_json,sha,write_json
from package_runtime import ROOT,api

COVERAGE={'HAALSI_SOURCE_TRAIN','HAALSI_SOURCE_VALIDATION','HAALSI_SOURCE_HELDOUT',
          'MHAS_ADAPTATION_POOL','MHAS_DEVELOPMENT_VALIDATION','MHAS_ORIGINAL_LOCKED_TEST','OTHER_PRIOR_STUDY_ACCESS'}


def verify_new_membership(membership,registry):
    import re
    need(membership['schema']=='new-cohort-membership-v1' and registry['schema']=='prior-person-token-registry-v1',
         'PROSPECTIVE_MEMBERSHIP_SCHEMA_INVALID')
    ids=membership['ids'];tokens=membership['person_tokens']
    need(isinstance(ids,list) and len(ids)>0 and all(isinstance(x,str) and x for x in ids)
         and len(ids)==len(set(ids))==len(tokens)==len(set(tokens)), 'NEW_COHORT_ID_INVALID')
    need(all(isinstance(t,str) and re.fullmatch('[0-9a-f]{64}',t) for t in tokens),'PERSON_TOKEN_INVALID')
    context=registry.get('tokenization_context_sha256')
    need(isinstance(context,str) and re.fullmatch('[0-9a-f]{64}',context)
         and membership.get('tokenization_context_sha256')==context,'PERSON_TOKEN_CONTEXT_MISMATCH')
    need(registry['complete_for_all_prior_study_access'] is True
         and registry['identity_resolution']=='cross_dataset_person_linkage_verified_by_independent_operator'
         and registry['token_standard']=='sha256_resolved_person_id_with_private_study_salt'
         and set(registry['partition_tokens'])>=COVERAGE,'PRIOR_MEMBERSHIP_COVERAGE_INSUFFICIENT')
    prior=set()
    for name,values in registry['partition_tokens'].items():
        need(isinstance(values,list) and all(isinstance(t,str) and re.fullmatch('[0-9a-f]{64}',t) for t in values),
             'PRIOR_TOKEN_INVALID')
        if name in COVERAGE-{'OTHER_PRIOR_STUDY_ACCESS'}:need(len(values)>0,'PRIOR_MEMBERSHIP_COVERAGE_INSUFFICIENT')
        prior.update(values)
    need(not set(tokens)&prior,'NEW_COHORT_OVERLAPS_PRIOR_STUDY')


def register(config,out):
    p=load_json(descriptor(config['proposal']))
    need(p['schema']=='genuine-independent-test-proposal-v1'
         and p['availability_attested_by_independent_operator'] is True
         and p['previously_used_in_any_model_decision'] is False
         and p['outcomes_not_inspected_for_registration'] is True
         and p['cohort_origin']=='new_unaccessed_eligible_participants'
         and p['cohort_id'] not in {'MHAS_ORIGINAL_LOCKED_TEST','MHAS_LOCKED_TEST'},'INDEPENDENT_TEST_NOT_AVAILABLE')
    need('outcomes' not in p and p['predictor_schema']=='cvd-public-wave-v2-ten-doctor-report',
         'REGISTRATION_MUST_NOT_ACCESS_OUTCOMES')
    for key in ['target_population','eligibility','outcome_definition','baseline_timing','followup_horizon','exclusion_criteria']:
        need(isinstance(p['scientific_contract'][key],str) and bool(p['scientific_contract'][key].strip()),'PROSPECTIVE_SCIENTIFIC_CONTRACT_MISSING')
    membership=load_json(descriptor(p['membership']));registry=load_json(descriptor(p['prior_person_token_registry']))
    verify_new_membership(membership,registry)
    model=p['frozen_model'];need(model['architecture'] in ['original','compact'],'UNSUPPORTED_FROZEN_ARCHITECTURE')
    threshold=model['numerical_threshold']
    need(type(threshold) in (int,float) and np.isfinite(threshold) and 0<=threshold<=1,'FROZEN_THRESHOLD_INVALID')
    checkpoint=descriptor(model['checkpoint']);pp=load_json(descriptor(model['source_preprocessing']))
    need(pp['fit_role']=='source_train' and pp['schema_version']==p['predictor_schema'],'FROZEN_PREPROCESSING_INVALID')
    hp=load_json(descriptor(model['hyperparameter_record']))
    need(hp['model_finalized_before_external_outcomes'] is True,'MODEL_NOT_FINALIZED')
    calibration=load_json(descriptor(model['threshold_calibration_record']))
    need(calibration['checkpoint_sha256']==model['checkpoint']['sha256']
         and calibration['threshold']==threshold and calibration['selection_data_role']=='training_side_only'
         and calibration['evaluation_outcomes_used'] is False and calibration['all_target_label_cost_recorded'] is True,
         'THRESHOLD_NOT_TRAINING_SIDE_FROZEN')
    fm=load_json(descriptor(p['feature_provenance']))
    need(fm['preprocessing_sha256']==model['source_preprocessing']['sha256']
         and fm['input_features_only'] is True and fm['no_future_information'] is True
         and fm['timing_and_outcome_definition_reviewed_by_operator'] is True
         and fm['previous_model_development_use'] is False,'EXTERNAL_FEATURE_PROVENANCE_INVALID')
    features=descriptor(p['features']);t=api()
    # Validate frozen weights at registration, before consuming an evaluation.
    import torch
    frozen=t.MultiViewRiskNet(t.VIEWS) if model['architecture']=='original' else t.CompactRiskNet()
    frozen.load_state_dict(torch.load(checkpoint,map_location='cpu',weights_only=True),strict=True)
    need(all(bool(torch.isfinite(value).all()) for value in frozen.state_dict().values()),'FROZEN_MODEL_NONFINITE')
    with np.load(features,allow_pickle=False) as z:
        need(len(z.files)==6 and set(z.files)=={'ids',*t.VIEWS},'EXTERNAL_FEATURE_FILE_CONTAINS_UNREGISTERED_FIELDS')
        need(z['ids'].tolist()==membership['ids'],'EXTERNAL_MEMBERSHIP_MISMATCH')
    contract=load_json(ROOT/'independent_protocol_v1.json')
    write_json(out/'registered_test.private.json',{'schema':'registered-independent-test-v1','proposal':p,
        'proposal_sha256':config['proposal']['sha256'],'protocol':contract,
        'package_manifest_sha256':sha(ROOT/'PUBLIC_PACKAGE_MANIFEST.json'),
        'registered_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'nonoverlap_checked':True,'claims_are_operator_assertions_not_institutional_certification':True,
        'outcomes_opened':False})


def evaluate(config,out):
    registration_path=descriptor(config['registration'])
    registration=load_json(registration_path)
    started=load_json(descriptor(config['registration_started_receipt']))
    completed=load_json(descriptor(config['registration_completed_receipt']))
    need(started['status']=='STARTED_CONSUMED' and completed['status']=='COMPLETED_PRIVATE_DISCLOSURE_REVIEW_REQUIRED'
         and completed['attempt_consumed'] is True and registration['schema']=='registered-independent-test-v1'
         and registration['package_manifest_sha256']==sha(ROOT/'PUBLIC_PACKAGE_MANIFEST.json')
         and registration['outcomes_opened'] is False,'PROSPECTIVE_REGISTRATION_BINDING_INVALID')
    need(registration['protocol']==load_json(ROOT/'independent_protocol_v1.json'),'PROSPECTIVE_PROTOCOL_CHANGED')
    # One registration cannot be evaluated twice under fresh output names/auths.
    # This marker is additional new-protocol evidence; no existing receipt changes.
    marker=registration_path.parent/'independent_evaluation.consumed.private.json'
    need(not marker.exists() and not marker.is_symlink(),'INDEPENDENT_REGISTRATION_ALREADY_CONSUMED')
    write_json(marker,
        {'status':'STARTED_CONSUMED_NO_RETRY','registration_sha256':config['registration']['sha256']})
    p=registration['proposal'];membership=load_json(descriptor(p['membership']))
    registry=load_json(descriptor(p['prior_person_token_registry']));verify_new_membership(membership,registry)
    t=api();model_record=p['frozen_model'];checkpoint=descriptor(model_record['checkpoint'])
    # Descriptor checks bind every frozen artifact again; no fitting is performed.
    for key in ['source_preprocessing','hyperparameter_record','threshold_calibration_record']:descriptor(model_record[key])
    descriptor(p['feature_provenance'])
    features=descriptor(p['features'])
    with np.load(features,allow_pickle=False) as z:
        need(len(z.files)==6 and set(z.files)=={'ids',*t.VIEWS},'EXTERNAL_FEATURE_FILE_CONTAINS_UNREGISTERED_FIELDS')
        ids=z['ids'].copy();views={v:z[v].copy() for v in t.VIEWS}
    need(ids.dtype.kind=='U' and ids.tolist()==membership['ids'],'EXTERNAL_MEMBERSHIP_MISMATCH')
    need(all(views[v].shape==(len(ids),d) and np.isfinite(views[v]).all() for v,d in t.VIEWS.items()),'EXTERNAL_FEATURE_INVALID')
    import torch
    model=t.MultiViewRiskNet(t.VIEWS) if model_record['architecture']=='original' else t.CompactRiskNet()
    model.load_state_dict(torch.load(checkpoint,map_location='cpu',weights_only=True),strict=True)
    model.eval()
    scores=t.prob(model,t.Encoded(views,np.zeros(len(ids)),'genuinely_new_prediction_only'))
    # First outcome access occurs AFTER fixed model/threshold and predictions.
    outcomes=descriptor(config['outcomes'])
    with np.load(outcomes,allow_pickle=False) as z:
        need(len(z.files)==2 and set(z.files)=={'ids','y'},'EXTERNAL_OUTCOME_FIELDS_INVALID')
        outcome_ids=z['ids'].copy();y=z['y'].copy()
    need(outcome_ids.dtype.kind=='U' and len(outcome_ids)==len(ids)==len(set(outcome_ids.tolist()))
         and set(outcome_ids.tolist())==set(ids.tolist()) and y.shape==(len(ids),) and np.isin(y,[0,1]).all(),
         'EXTERNAL_OUTCOME_MEMBERSHIP_INVALID')
    order={pid:i for i,pid in enumerate(outcome_ids.tolist())};y=y[[order[i] for i in ids.tolist()]]
    from results_report import participant_bootstrap
    c=registration['protocol']
    result={'scope':'ONE_FIXED_MODEL_NEW_PARTICIPANT_EVALUATION_NOT_CLINICAL_ADJUDICATION',
        'registration_sha256':config['registration']['sha256'],
        'fixed_0_50':t.metrics(y,scores,.5),'registered_threshold':t.metrics(y,scores,model_record['numerical_threshold']),
        'primary_ap_uncertainty':participant_bootstrap(y,scores[None,:],None,c['bootstrap_repetitions'],c['bootstrap_seed']),
        'threshold_retuned':False,'model_fitted':False,'original_mhas_locked_test_used':False,
        'membership_n':len(ids),'clinical_success_claimed':False}
    write_json(out/'independent_evaluation.private.json',result)
    with (out/'new_cohort_predictions.private.npz').open('xb') as stream:np.savez_compressed(stream,ids=ids,labels=y,probabilities=scores)
