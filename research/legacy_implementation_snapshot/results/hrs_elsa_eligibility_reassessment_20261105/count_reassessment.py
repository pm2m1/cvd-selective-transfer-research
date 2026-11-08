"""Future independent count-only operation. Not executed against protected data here."""
from pathlib import Path
import sys,json
import re
from local_execution import cli,need,descriptor,load_json,write_json,sha,require_local,exclusive_output
from eligibility import count,invented_people
ROOT=Path(__file__).resolve().parent
PURPOSE='new_elsa_eligibility_reassessment_count_only_v1'


def digest(value):
    return isinstance(value,str) and re.fullmatch('[0-9a-f]{64}',value) is not None


def validate_contract(config,bundle,mapping):
    need(config.get('schema')=='elsa-count-local-v1' and config.get('mode')=='independent_local_only',
         'COUNT_CONFIG_INVALID')
    need(bundle.get('schema')=='elsa-reviewed-canonical-v1' and set(bundle)=={'schema','source_bindings','mapping_sha256','people'},
         'CANONICAL_BUNDLE_INVALID')
    need(mapping.get('schema')=='elsa-reviewed-route-map-v1' and mapping.get('status')=='REVIEWED_FOR_THIS_OPERATION'
         and mapping.get('codebook_bindings') and mapping.get('component_field_maps')
         and mapping.get('baseline_and_since_wave_routing') and mapping.get('dates_preserve_bounds') is True,
         'REVIEWED_RAW_MAPPING_REQUIRED')
    need(digest(bundle['mapping_sha256']) and bundle['mapping_sha256']==config['mapping']['sha256'],'CANONICAL_MAP_BINDING_MISMATCH')
    need(isinstance(bundle['source_bindings'],dict) and bundle['source_bindings']==mapping.get('source_bindings') and bundle['source_bindings'],
         'SOURCE_RELEASE_BINDINGS_MISMATCH')
    for record in mapping['source_bindings'].values():
        need(isinstance(record,dict) and digest(record.get('sha256'))
             and isinstance(record.get('edition'),str) and record['edition'].strip()
             and isinstance(record.get('member'),str) and record['member'].strip(),'SOURCE_RELEASE_IDENTITY_UNRESOLVED')
    need(isinstance(mapping['codebook_bindings'],dict) and mapping['codebook_bindings'],'CODEBOOK_BINDINGS_REQUIRED')
    for record in mapping['codebook_bindings'].values():
        need(isinstance(record,dict) and digest(record.get('sha256')) and record.get('official_url')
             and record.get('edition') and record.get('sections'),'CODEBOOK_BINDING_INVALID')
    need(isinstance(mapping['component_field_maps'],dict) and set(mapping['component_field_maps'])=={'mi','stroke'},'COMPONENT_MAPS_REQUIRED')
    needed_waves={v['wave'] for p in bundle['people'] for v in p['visits']
                  if v['kind'] in ['personal','proxy','partial','institutional']}
    for component in ['mi','stroke']:
        maps=mapping['component_field_maps'][component]
        need(isinstance(maps,list) and maps,'COMPONENT_MAPS_REQUIRED')
        for item in maps:
            need(isinstance(item,dict) and type(item.get('wave')) is int and 1<=item['wave']<=9
                 and item.get('raw_fields') and item.get('codebook_key') in mapping['codebook_bindings']
                 and item.get('negative_proof_rule') and item.get('positive_report_rule')
                 and item.get('missing_dispute_rule'),'COMPONENT_ROUTE_RULES_REQUIRED')
        need(needed_waves<={item['wave'] for item in maps},'WAVE_SPECIFIC_COMPONENT_MAP_MISSING')
    need(isinstance(mapping['baseline_and_since_wave_routing'],list)
         and mapping['baseline_and_since_wave_routing'],'INTERVAL_ROUTING_REQUIRED')
    routing=mapping['baseline_and_since_wave_routing']
    for item in routing:
        need(isinstance(item,dict) and type(item.get('wave')) is int and 1<=item['wave']<=9
             and item.get('interview_fields') and item.get('date_fields') and item.get('scope_rule')
             and item.get('since_wave_rule') and item.get('codebook_key') in mapping['codebook_bindings'],
             'WAVE_ROUTING_RULES_REQUIRED')
    need(needed_waves<={item['wave'] for item in routing},'WAVE_SPECIFIC_ROUTING_MISSING')
    need(mapping.get('canonicalizer_source_sha256') and digest(mapping['canonicalizer_source_sha256'])
         and mapping.get('reviewed_for_protected_operation') is True,'CANONICALIZER_REVIEW_REQUIRED')
    return True


def execute(config,out):
    require_local()  # even a direct execute() call must reject agent/CI operation
    need(config.get('protocol_sha256')==sha(ROOT/'COUNT_PROTOCOL.json'),'COUNT_PROTOCOL_CHANGED')
    source=descriptor(config['canonical_input']);map_path=descriptor(config['mapping'])
    bundle=load_json(source);mapping=load_json(map_path);validate_contract(config,bundle,mapping)
    report=count(bundle['people'])
    report['bindings']={'canonical_input_sha256':sha(source),'mapping_sha256':sha(map_path),
        'source_bindings':bundle['source_bindings'],'protocol_sha256':sha(ROOT/'COUNT_PROTOCOL.json')}
    # Hash after reading: record source/config changes as a failure, never reuse.
    need(report['bindings']['canonical_input_sha256']==config['canonical_input']['sha256']
         and report['bindings']['mapping_sha256']==config['mapping']['sha256'],'INPUT_CHANGED_DURING_COUNT')
    write_json(out/'reassessment_counts.private.json',report)
    write_json(out/'processing_boundary.private.json',{'raw_datasets_loaded':False,'canonical_records_processed':True,
        'models_fitted':False,'participants_written':False,'disclosure_review_required':True})


def demo(output):
    with exclusive_output(output,False) as out:
        report=count(invented_people());report['scope']='INVENTED_SYNTHETIC_ONLY_NOT_EMPIRICAL_COUNTS'
        write_json(out/'SYNTHETIC_COUNTS.json',report)


if __name__=='__main__':sys.exit(cli(PURPOSE,execute,demo))
