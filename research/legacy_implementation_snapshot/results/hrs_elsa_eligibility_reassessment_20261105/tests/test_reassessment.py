"""Invented canonical records and public-marginal arithmetic only."""
import copy,json,os,sys,tempfile,subprocess
from datetime import date
from pathlib import Path
import unittest
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from eligibility import *
from local_execution import exclusive_output,Rejected


def p():return copy.deepcopy(invented_people()[0])


def visit(person,w):return next(v for v in person['visits'] if v['wave']==w)


class ScreenTests(unittest.TestCase):
    def test_exact_A_predicate(self):
        raw=p()['raw6'];self.assertTrue(strict6(raw))
        for key,value in [('inw1',1),('inw2',None),('hedim96',0),('hedimmi',1),('hedimst',None),('w6indout',13),('askpx',1),('r6agey',49)]:
            self.assertFalse(strict6({**raw,key:value}),key)

    def test_H_and_S_not_nested_by_code(self):
        a=p()['raw6'];a['r6hrtatte']=1
        b=p()['raw6'];b['inw1']=1
        self.assertTrue(strict6(a));self.assertFalse(harmonized6(a))
        self.assertTrue(harmonized6(b));self.assertFalse(strict6(b))

    def test_frechet_bounds_from_public_marginals(self):
        bounds=overlap_bounds(9734,8915,570)
        self.assertEqual(bounds['intersection'],[0,570])
        self.assertEqual(bounds['H_only'],[8345,8915]);self.assertEqual(bounds['S_only'],[0,570])
        self.assertEqual(bounds['neither'],[249,819])

    def test_invalid_marginals_rejected(self):
        for args in [(10,-1,1),(10,1,11),(10,1.2,1),(-1,0,0)]:
            with self.assertRaises(ValueError):overlap_bounds(*args)

    def test_missing_is_not_zero(self):
        raw=p()['raw6'];raw['inw1']=None
        self.assertFalse(strict6(raw))

    def test_first_response_stronger_than_first_personal(self):
        x=p();x['raw6']['inw4']=1
        v=visit(x,4);v.update(kind='proxy',scope='lifetime',mi='no',stroke='no')
        self.assertFalse(strict6(x['raw6']))
        self.assertTrue(baseline_eligible(x,'B','composite')[0])

    def test_hypertension_diabetes_allowed_in_B(self):
        x=p();x['raw6']['hedim96']=0;v=visit(x,6);v['conditions']=['hypertension','diabetes']
        self.assertFalse(strict6(x['raw6']));self.assertTrue(baseline_eligible(x,'B','composite')[0])

    def test_B_keeps_common_screen_for_controlled_comparison(self):
        x=p();x['raw6']['w6indout']=13
        self.assertFalse(baseline_eligible(x,'B','composite')[0])

    def test_raw_harmonized_positive_not_overridden_by_canonical_no(self):
        x=p();x['raw6']['r6hrtatte']=1
        self.assertFalse(baseline_eligible(x,'A','composite')[0])
        self.assertFalse(baseline_eligible(x,'B','mi')[0])
        self.assertTrue(baseline_eligible(x,'B','stroke')[0])

    def test_raw_selected_stroke_not_overridden_by_canonical_no(self):
        x=p();x['raw6']['hedimst']=1
        self.assertFalse(baseline_eligible(x,'B','stroke')[0])
        self.assertTrue(baseline_eligible(x,'B','mi')[0])

    def test_counts_do_not_enforce_nested_overlap(self):
        x=p();y=p();y['person_token']='INVENTED_OTHER'
        x['raw6']['r6hrtatte']=1;y['raw6']['inw1']=1
        report=count([x,y]);o=report['raw_screen_overlap']
        self.assertEqual(o['H_only'],1);self.assertEqual(o['S_only'],1);self.assertEqual(o['intersection'],0)


class HistoryTests(unittest.TestCase):
    def test_continuing_participant_uses_lifetime_anchor(self):
        x=copy.deepcopy(invented_people()[1])
        self.assertTrue(baseline_eligible(x,'B','composite')[0]);self.assertFalse(strict6(x['raw6']))

    def test_interval_none_alone_not_lifetime(self):
        x=p();visit(x,6).update(scope='interval',since_wave=5)
        self.assertFalse(baseline_eligible(x,'B','composite')[0])

    def test_prior_MI_not_erased_by_no(self):
        x=copy.deepcopy(invented_people()[1]);visit(x,4)['mi']='yes'
        self.assertFalse(baseline_eligible(x,'B','composite')[0])
        self.assertTrue(baseline_eligible(x,'B','stroke')[0])

    def test_prior_stroke_component_population(self):
        x=copy.deepcopy(invented_people()[1]);visit(x,4)['stroke']='historical'
        self.assertFalse(baseline_eligible(x,'B','composite')[0]);self.assertTrue(baseline_eligible(x,'B','mi')[0])

    def test_proxy_no_is_not_anchor(self):
        x=p();visit(x,6).update(kind='proxy')
        self.assertFalse(negative_history(x['visits'],6,'mi'))

    def test_missing_intervening_wave_no_coverage(self):
        x=copy.deepcopy(invented_people()[1]);visit(x,5).update(kind='none',mi='unknown',stroke='unknown')
        self.assertFalse(negative_history(x['visits'],6,'mi'))

    def test_documented_interval_can_bridge_gap(self):
        x=copy.deepcopy(invented_people()[1]);visit(x,5).update(kind='none',mi='unknown',stroke='unknown')
        visit(x,6)['since_wave']=4
        self.assertTrue(negative_history(x['visits'],6,'mi'))

    def test_new_lifetime_no_can_reestablish_after_missing_not_prior_positive(self):
        x=copy.deepcopy(invented_people()[1]);visit(x,5).update(mi='unknown');visit(x,6)['scope']='lifetime'
        self.assertTrue(negative_history(x['visits'],6,'mi'))
        visit(x,4)['mi']='disputed';self.assertFalse(negative_history(x['visits'],6,'mi'))

    def test_incomplete_or_uncleared_question_never_no(self):
        for field in ['list_complete','branch_clear']:
            x=p();visit(x,6)[field]=None
            self.assertFalse(baseline_eligible(x,'B','composite')[0])


class OutcomeTests(unittest.TestCase):
    def test_first_qualifying_report(self):self.assertEqual(outcome(p()['visits'],6,'mi'),'POSITIVE_REPORT')

    def test_repeated_historical_report_does_not_erase_case(self):
        x=p();visit(x,8)['mi']='historical'
        self.assertEqual(outcome(x['visits'],6,'mi'),'POSITIVE_REPORT')

    def test_confirmation_without_first_event_not_incident(self):
        x=p();visit(x,7)['mi']='historical'
        self.assertNotEqual(outcome(x['visits'],6,'mi'),'POSITIVE_REPORT')

    def test_prebaseline_diagnosis_delayed_report_not_incident(self):
        x=p();visit(x,7)['diagnosis_bounds']['mi']={'lower':'2010-01-01','upper':'2010-12-31'}
        self.assertEqual(outcome(x['visits'],6,'mi'),'DISPUTED_OR_PRIOR_OR_TIA')

    def test_disease_free_chain_needed_for_nonevents(self):
        x=p();visit(x,7)['mi']='no';visit(x,7)['conditions']=[]
        self.assertEqual(outcome(x['visits'],6,'mi'),'NEGATIVE_REPORT')
        visit(x,8)['mi']='unknown';self.assertNotEqual(outcome(x['visits'],6,'mi'),'NEGATIVE_REPORT')

    def test_proxy_followup_is_unknown_not_negative(self):
        x=p();visit(x,7)['mi']='no';visit(x,9)['kind']='proxy'
        self.assertNotEqual(outcome(x['visits'],6,'mi'),'NEGATIVE_REPORT')

    def test_withdrawal_not_negative(self):
        x=p();visit(x,7)['mi']='no';visit(x,9)['kind']='withdrawn'
        self.assertNotEqual(outcome(x['visits'],6,'mi'),'NEGATIVE_REPORT')

    def test_death_without_event_and_event_before_death(self):
        x=p();visit(x,8)['kind']='dead';visit(x,9)['kind']='none'
        self.assertEqual(outcome(x['visits'],6,'mi'),'POSITIVE_REPORT')
        visit(x,7)['mi']='no';self.assertEqual(outcome(x['visits'],6,'mi'),'CENSORED_DEATH')

    def test_tia_not_stroke(self):
        x=p();visit(x,7)['stroke']='tia'
        self.assertNotEqual(outcome(x['visits'],6,'stroke'),'POSITIVE_REPORT')

    def test_date_uncertainty_preserved_not_midpoint(self):
        x=p();visit(x,7)['mi']='no';visit(x,6).update(date_lower='2012-06-01',date_upper='2012-06-30')
        visit(x,9).update(date_lower='2018-06-01',date_upper='2018-06-30')
        self.assertNotEqual(outcome(x['visits'],6,'mi'),'NEGATIVE_REPORT')

    def test_late_positive_straddling_target_unknown(self):
        x=p();visit(x,7)['mi']='no';visit(x,9).update(mi='yes',date_lower='2018-07-01',date_upper='2018-07-01')
        self.assertEqual(outcome(x['visits'],6,'mi'),'UNKNOWN_TIMING')

    def test_dated_positive_can_resolve_straddling_interval(self):
        x=p();visit(x,7)['mi']='no';visit(x,9).update(mi='yes',date_lower='2018-07-01',date_upper='2018-07-01')
        visit(x,9)['diagnosis_bounds']['mi']={'lower':'2017-01-01','upper':'2017-01-31'}
        self.assertEqual(outcome(x['visits'],6,'mi'),'POSITIVE_REPORT')

    def test_future_wave_not_baseline_proof(self):
        x=p();visit(x,6).update(mi='unknown');visit(x,7).update(scope='lifetime',mi='no')
        self.assertFalse(baseline_eligible(x,'B','mi')[0])

    def test_wave4_earlier_baseline_six_year_report(self):
        x=copy.deepcopy(invented_people()[1]);visit(x,7).update(mi='yes')
        self.assertTrue(baseline_eligible(x,'C_W4','composite')[0])
        self.assertEqual(outcome(x['visits'],4,'mi'),'POSITIVE_REPORT')


class ContractTests(unittest.TestCase):
    def valid_contract(self):
        sources={'INVENTED_RELEASE':{'sha256':'a'*64,'edition':'INVENTED_EDITION','member':'INVENTED_MEMBER'}}
        mapping={'schema':'elsa-reviewed-route-map-v1','status':'REVIEWED_FOR_THIS_OPERATION',
            'source_bindings':sources,'dates_preserve_bounds':True,'canonicalizer_source_sha256':'c'*64,
            'reviewed_for_protected_operation':True,'codebook_bindings':{'INVENTED':{'sha256':'d'*64,
            'official_url':'https://example.invalid/INVENTED','edition':'INVENTED','sections':['INVENTED']}},
            'component_field_maps':{},'baseline_and_since_wave_routing':[]}
        mapping['component_field_maps']={c:[{'wave':w,'raw_fields':['INVENTED_FIELD'], 'codebook_key':'INVENTED',
            'negative_proof_rule':'INVENTED','positive_report_rule':'INVENTED','missing_dispute_rule':'INVENTED'}
            for w in range(4,10)] for c in ['mi','stroke']}
        mapping['baseline_and_since_wave_routing']=[{'wave':w,'interview_fields':['INVENTED_STATUS'],
            'date_fields':['INVENTED_DATE'],'scope_rule':'INVENTED','since_wave_rule':'INVENTED',
            'codebook_key':'INVENTED'} for w in range(4,10)]
        cfg={'schema':'elsa-count-local-v1','mode':'independent_local_only','mapping':{'sha256':'b'*64}}
        bundle={'schema':'elsa-reviewed-canonical-v1','source_bindings':copy.deepcopy(sources),'mapping_sha256':'b'*64,'people':invented_people()}
        return cfg,bundle,mapping

    def test_valid_invented_mapping_contract(self):
        from count_reassessment import validate_contract
        self.assertTrue(validate_contract(*self.valid_contract()))

    def test_mapping_binding_changed(self):
        from count_reassessment import validate_contract
        cfg,b,m=self.valid_contract();b['mapping_sha256']='e'*64
        with self.assertRaisesRegex(Rejected,'MAP_BINDING'):validate_contract(cfg,b,m)

    def test_source_edition_mismatch(self):
        from count_reassessment import validate_contract
        cfg,b,m=self.valid_contract();b['source_bindings']['INVENTED_RELEASE']['edition']='WRONG'
        with self.assertRaisesRegex(Rejected,'SOURCE_RELEASE'):validate_contract(cfg,b,m)

    def test_source_digest_not_hex(self):
        from count_reassessment import validate_contract
        cfg,b,m=self.valid_contract();m['source_bindings']['INVENTED_RELEASE']['sha256']='z'*64
        b['source_bindings']=copy.deepcopy(m['source_bindings'])
        with self.assertRaisesRegex(Rejected,'IDENTITY'):validate_contract(cfg,b,m)

    def test_no_codebook_fingerprint(self):
        from count_reassessment import validate_contract
        cfg,b,m=self.valid_contract();m['codebook_bindings']['INVENTED']['sha256']=None
        with self.assertRaisesRegex(Rejected,'CODEBOOK'):validate_contract(cfg,b,m)

    def test_unreviewed_canonicalizer(self):
        from count_reassessment import validate_contract
        cfg,b,m=self.valid_contract();m['reviewed_for_protected_operation']=False
        with self.assertRaisesRegex(Rejected,'CANONICALIZER'):validate_contract(cfg,b,m)

    def test_incomplete_component_rule(self):
        from count_reassessment import validate_contract
        cfg,b,m=self.valid_contract();m['component_field_maps']['mi'][0].pop('negative_proof_rule')
        with self.assertRaisesRegex(Rejected,'ROUTE_RULES'):validate_contract(cfg,b,m)

    def test_missing_wave_specific_map(self):
        from count_reassessment import validate_contract
        cfg,b,m=self.valid_contract();m['component_field_maps']['mi']=m['component_field_maps']['mi'][:1]
        with self.assertRaisesRegex(Rejected,'WAVE_SPECIFIC_COMPONENT'):validate_contract(cfg,b,m)

    def test_missing_wave_specific_routing(self):
        from count_reassessment import validate_contract
        cfg,b,m=self.valid_contract();m['baseline_and_since_wave_routing']=m['baseline_and_since_wave_routing'][:1]
        with self.assertRaisesRegex(Rejected,'WAVE_SPECIFIC_ROUTING'):validate_contract(cfg,b,m)

    def test_proof_flags_not_numeric(self):
        x=p();visit(x,6)['list_complete']=1
        with self.assertRaisesRegex(ValueError,'ROUTE_PROOF'):count([x])

    def test_prior_and_followup_disputes_not_negative(self):
        x=p();visit(x,7)['mi']='disputed'
        self.assertEqual(outcome(x['visits'],6,'mi'),'DISPUTED_OR_PRIOR_OR_TIA')
        visit(x,6)['stroke']='disputed'
        self.assertFalse(baseline_eligible(x,'B','composite')[0])

    def test_missing_encodings_all_fail_closed(self):
        for value in ['.a','.z','.',-1,-8,-9,float('nan'),True,'not-a-code']:
            raw=p()['raw6'];raw['hedimmi']=value
            self.assertFalse(strict6(raw))

    def test_event_after_horizon_not_six_year_case(self):
        x=p();visit(x,7)['mi']='no';visit(x,9).update(mi='yes',date_lower='2020-06-01',date_upper='2020-06-01')
        self.assertNotEqual(outcome(x['visits'],6,'mi'),'POSITIVE_REPORT')

    def test_interruption_consumed(self):
        with tempfile.TemporaryDirectory() as tmp:
            out=Path(tmp)/'new'
            with self.assertRaises(KeyboardInterrupt):
                with exclusive_output(out,False):raise KeyboardInterrupt()
            self.assertEqual(json.loads((out/'completion.private.json').read_text())['status'],'INTERRUPTED_NO_RETRY')

    def test_private_permissions(self):
        with tempfile.TemporaryDirectory() as tmp:
            parent=Path(tmp);parent.chmod(0o700);out=parent/'new'
            with exclusive_output(out):pass
            self.assertEqual(out.stat().st_mode & 0o777,0o700)
            self.assertEqual((out/'completion.private.json').stat().st_mode & 0o777,0o600)

    def test_input_descriptor_hash_changed(self):
        from local_execution import descriptor
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'INVENTED.json';path.write_text('{}')
            with self.assertRaisesRegex(Rejected,'BINDING'):descriptor({'path':str(path),'sha256':'0'*64})

    def test_no_identifier_or_rows_in_count_output(self):
        result=count(invented_people());text=json.dumps(result)
        self.assertNotIn('INVENTED_REASSESSMENT_',text);self.assertNotIn('person_token',text)

    def test_duplicate_ID_and_wave_rejected(self):
        x=p()
        with self.assertRaises(ValueError):count([x,x])
        x['visits'].append(copy.deepcopy(x['visits'][-1]))
        with self.assertRaises(ValueError):count([x])

    def test_future_since_wave_rejected(self):
        x=p();visit(x,7)['since_wave']=8
        with self.assertRaises(ValueError):count([x])

    def test_extra_model_or_test_payload_rejected(self):
        x=p();x['predictions']=[.1]
        with self.assertRaises(ValueError):count([x])

    def test_extra_raw_payload_rejected(self):
        x=p();x['raw6']['predictions']=[.1]
        with self.assertRaisesRegex(ValueError,'RAW_SCREEN'):count([x])

    def test_zero_eligible_population_is_not_a_feasibility_pass(self):
        people=invented_people()
        for x in people:
            for v in x['visits']:v['age']=49
        report=count(people)
        self.assertTrue(all(r['eligible_baseline']==0 for r in report['designs'].values()))
        self.assertEqual(report['independent_test_status'],'NOT_ESTABLISHED')

    def test_refreshment_after_baseline_cannot_enter(self):
        x=p();x['visits']=[v for v in x['visits'] if v['wave']>=7]
        self.assertFalse(baseline_eligible(x,'B','composite')[0])

    def test_wave_order_cannot_follow_dates_incorrectly(self):
        x=p();a,b=visit(x,4),visit(x,5);a['wave'],b['wave']=5,4
        with self.assertRaises(ValueError):count([x])

    def test_raw_INW_conflict_rejected(self):
        x=p();visit(x,4).update(kind='personal')
        with self.assertRaisesRegex(ValueError,'INW'):count([x])

    def test_A_B_C_outcome_accounting(self):
        result=count(invented_people())
        self.assertEqual(len(result['designs']),9)
        for r in result['designs'].values():self.assertEqual(r['eligible_baseline'],sum(r['outcome_states'].values()))

    def test_agent_rejected_before_private_config(self):
        env=dict(os.environ,CODEX_SESSION_ID='INVENTED_AGENT')
        r=subprocess.run([sys.executable,'-B',str(ROOT/'count_reassessment.py'),'--execute-local',
            '--config','/NOT_OPENED_INVENTED_CONFIG','--authorization','/NOT_OPENED_INVENTED_AUTH','--output','/NOT_CREATED_INVENTED_OUTPUT'],
            env=env,capture_output=True,text=True)
        self.assertEqual(r.returncode,2);self.assertNotIn('/NOT_OPENED',r.stdout+r.stderr)

    def test_output_exclusive_failure_no_retry(self):
        with tempfile.TemporaryDirectory() as tmp:
            out=Path(tmp)/'new'
            with self.assertRaises(ValueError):
                with exclusive_output(out,False):raise ValueError('INVENTED_SENSITIVE_CONTEXT')
            receipt=json.loads((out/'completion.private.json').read_text())
            self.assertTrue(receipt['attempt_consumed']);self.assertNotIn('SENSITIVE',json.dumps(receipt))
            with self.assertRaises(Rejected):
                with exclusive_output(out,False):pass

    def test_missing_mapping_and_wrong_release_fail_closed(self):
        from count_reassessment import validate_contract
        with self.assertRaises(Rejected):validate_contract({}, {}, {})


if __name__=='__main__':unittest.main()
