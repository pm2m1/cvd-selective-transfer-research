"""Separate human-only, one-attempt final count workflow. No model training."""
from pathlib import Path
import json,sys
from local_execution import cli,need,sha,write_json,require_local,exclusive_output,Rejected,load_json
from count_engine import analyze,CountError
from precision import summarize

ROOT=Path(__file__).resolve().parent
PURPOSE='elsa_final_two_design_count_only_v1_20261105'

def validate_config(config):
    need(config.get('schema')=='elsa-final-count-local-config-v1' and config.get('mode')=='independent_local_only','COUNT_CONFIG_INVALID')
    need(config.get('no_models') is True,'COUNT_ONLY_CONTRACT_REQUIRED')
    need(config.get('protocol_sha256')==sha(ROOT/'PROTOCOL.json'),'PROTOCOL_BINDING_MISMATCH')
    need(config.get('mapping_sha256')==sha(ROOT/'official_variable_map.json'),'PUBLIC_MAPPING_BINDING_MISMATCH')
    need(config.get('source_use_review')=='INDEPENDENTLY_ESTABLISHED_FOR_THIS_NEW_OPERATION','NEW_OPERATION_SCOPE_NOT_ESTABLISHED')
    # This literal is an operator's reviewed record, not a software-issued licence.
    return True

def execute(config,out):
    require_local()  # Guard direct API calls as well as the original CLI boundary.
    from verify_public import verify
    verify()
    validate_config(config)
    mapping=json.loads((ROOT/'official_variable_map.json').read_text());protocol=json.loads((ROOT/'PROTOCOL.json').read_text())
    from read_release import load_people
    try:people,bindings,qa=load_people(config,mapping)
    except CountError as e:raise Rejected('SOURCE_VALIDATION_'+str(e)) from None
    try:report=analyze(people,mapping,protocol)
    except CountError as e:
        # Our exception class contains stable codes only, no arbitrary context.
        raise Rejected('ELIGIBILITY_PROCESSING_'+str(e)) from None
    report['bindings']={'sources':bindings,'mapping_sha256':sha(ROOT/'official_variable_map.json'),
                        'protocol_sha256':sha(ROOT/'PROTOCOL.json')}
    report['source_linkage_quality']=qa
    write_json(out/'final_counts.private.json',report)
    write_json(out/'precision_assessment.private.json',summarize(report))
    write_json(out/'scientific_status.private.json',{'status':'EMPIRICAL_COUNTS_WRITTEN_SCIENTIFIC_ASSESSMENT_REQUIRED',
       'feature_metadata_supplied':qa['feature_metadata_supplied'],'model_training_authorized':False,
       'automatic_baseline_feature_derivation':qa['automatic_baseline_feature_derivation'],
       'independent_test_established':False,'publication_disclosure_review_required':True})
    from importlib.metadata import version
    from local_execution import code_hashes
    write_json(out/'runtime_bindings.private.json',{'python':sys.version,'pandas':version('pandas'),
        'numpy':version('numpy'),'code_bindings':code_hashes(),
        'protocol_sha256':sha(ROOT/'PROTOCOL.json'),'mapping_sha256':sha(ROOT/'official_variable_map.json')})
    write_json(out/'result_integrity.private.json',{'schema':'elsa-final-count-result-integrity-v1',
        'purpose':PURPOSE,'outputs':{name:sha(out/name) for name in ['final_counts.private.json',
        'precision_assessment.private.json','scientific_status.private.json','runtime_bindings.private.json']}})

def demo(output):
    from synthetic_fixture import invented_people
    mapping=json.loads((ROOT/'official_variable_map.json').read_text());protocol=json.loads((ROOT/'PROTOCOL.json').read_text())
    with exclusive_output(output,False) as out:
        report=analyze(invented_people(mapping),mapping,protocol)
        report['scope']='INVENTED_SYNTHETIC_FIXTURES_NOT_ELSA_EMPIRICAL_COUNTS'
        write_json(out/'SYNTHETIC_counts.json',report)
        planning=summarize(report);planning['scope']='INVENTED_SYNTHETIC_PLANNING_ONLY'
        write_json(out/'SYNTHETIC_precision.json',planning)

def main():
    # Application-level config readiness precedes the unchanged operator prompt.
    # This reads configuration only, never clinical paths or source contents.
    try:
        if '--authorize-local' in sys.argv:
            require_local()
            from verify_public import verify
            verify()
            import argparse
            parser=argparse.ArgumentParser(add_help=False);parser.add_argument('--config',type=Path)
            args,_=parser.parse_known_args();need(args.config is not None,'CONFIG_REQUIRED')
            validate_config(load_json(args.config))
    except BaseException:
        print('REVIEW ISSUE=CONFIG_NOT_READY_NO_AUTHORIZATION_RECORDED');return 2
    return cli(PURPOSE,execute,demo)

if __name__=='__main__':sys.exit(main())
