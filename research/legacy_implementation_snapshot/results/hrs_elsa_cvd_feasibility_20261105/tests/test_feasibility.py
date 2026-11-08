"""All participant fixtures are invented; no file-input clinical pathway exists."""
import copy
from dataclasses import replace
from datetime import date,timedelta
from pathlib import Path
import sys
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from feasibility import *

D=date(2012,6,1)


def person(pid='INVENTED_001'):
    features={'age':Feature(60,D,D,'years'),'sex':Feature('female',D,D),'bmi':Feature(25,D,D,'kg/m2')}
    return [Visit('HRS',pid,11,D,scope='lifetime',features=features)]+[
        Visit('HRS',pid,11+i,add_years(D,2*i),interval_start=add_years(D,2*(i-1))) for i in [1,2,3]]


def evaluate(rows,endpoint='composite',**kw):return audit(rows,{'HRS':11,'ELSA':6},endpoint,**kw)


class EndpointTests(unittest.TestCase):
    def test_previous_mi_excludes_composite_not_stroke_population(self):
        r=person();r[0]=replace(r[0],mi='positive')
        self.assertEqual(evaluate(r)['flow'].get('retained',0),0)
        self.assertEqual(evaluate(r,'stroke')['flow']['retained'],1)

    def test_previous_stroke_excludes_composite_not_mi_population(self):
        r=person();r[0]=replace(r[0],stroke='positive')
        self.assertEqual(evaluate(r)['flow'].get('retained',0),0)
        self.assertEqual(evaluate(r,'mi')['flow']['retained'],1)

    def test_first_event(self):
        r=person();r[1]=replace(r[1],mi='positive')
        self.assertEqual(evaluate(r)['flow']['positive'],1)

    def test_missing_outcome_is_not_negative(self):
        r=person();r[-1]=replace(r[-1],mi='unknown')
        self.assertEqual(evaluate(r)['outcome_states']['UNKNOWN'],1)

    def test_tia_is_not_stroke(self):
        r=person();r[-1]=replace(r[-1],stroke='tia')
        self.assertEqual(evaluate(r,'stroke')['outcome_states']['UNKNOWN'],1)

    def test_death_without_event_censored(self):
        r=person()[:2];r.append(Visit('HRS','INVENTED_001',13,add_years(D,3),kind='dead'))
        self.assertEqual(evaluate(r)['outcome_states']['CENSORED_DEATH'],1)

    def test_event_survives_later_death(self):
        r=person()[:2];r[1]=replace(r[1],mi='positive')
        r.append(Visit('HRS','INVENTED_001',13,add_years(D,3),kind='dead'))
        self.assertEqual(evaluate(r)['flow']['positive'],1)

    def test_repeated_event_report_counts_person_once(self):
        r=person();r=[r[0]]+[replace(x,mi='positive') for x in r[1:]]
        self.assertEqual(evaluate(r)['retained_mi_reports'],1)

    def test_proxy_not_negative_or_positive(self):
        for state in ['positive','negative']:
            r=person();r[-1]=replace(r[-1],kind='proxy',mi=state,stroke=state)
            self.assertEqual(evaluate(r)['outcome_states']['UNKNOWN'],1)

    def test_exit_does_not_supply_personal_outcome(self):
        r=person();r[-1]=replace(r[-1],kind='exit',mi='positive')
        self.assertEqual(evaluate(r)['outcome_states']['UNKNOWN'],1)

    def test_refreshment_not_added_to_baseline(self):
        self.assertEqual(evaluate(person()[1:])['flow']['excluded_not_at_primary_baseline'],1)

    def test_similar_identifiers_remain_distinct(self):
        report=evaluate(person('INVENTED_01')+person('INVENTED_001'))
        self.assertEqual(report['flow']['total_unique'],2)

    def test_duplicate_person_wave_rejected(self):
        r=person()
        with self.assertRaisesRegex(ValueError,'DUPLICATE_PERSON_WAVE'):evaluate(r+[r[0]])

    def test_multiple_waves_one_person(self):self.assertEqual(evaluate(person())['flow']['retained'],1)

    def test_horizon_too_early_insufficient(self):
        r=person();r[-1]=replace(r[-1],when=add_years(D,6)-timedelta(days=20))
        self.assertEqual(evaluate(r)['outcome_states']['UNKNOWN'],1)

    def test_horizon_too_late_excluded(self):
        r=person();r[-1]=replace(r[-1],when=add_years(D,6)+timedelta(days=184))
        self.assertEqual(evaluate(r)['outcome_states']['UNKNOWN'],1)

    def test_late_undated_positive_straddling_horizon_unknown(self):
        r=person();r[-1]=replace(r[-1],when=add_years(D,6)+timedelta(days=20),mi='positive')
        self.assertEqual(evaluate(r,'mi')['outcome_states']['UNKNOWN'],1)

    def test_dated_event_before_target_from_later_interview(self):
        r=person();r[-1]=replace(r[-1],when=add_years(D,6)+timedelta(days=20),mi='positive',mi_date=add_years(D,5))
        self.assertEqual(evaluate(r,'mi')['flow']['positive'],1)

    def test_dispute_not_negative(self):
        r=person();r[-1]=replace(r[-1],mi='disputed')
        self.assertEqual(evaluate(r,'mi')['outcome_states']['DISPUTED'],1)

    def test_lifetime_retraction_after_known_positive_is_disputed(self):
        r=person();r[1]=replace(r[1],mi='positive');r[-1]=replace(r[-1],mi='negative',scope='lifetime')
        self.assertEqual(evaluate(r,'mi')['outcome_states']['DISPUTED'],1)

    def test_personal_interview_after_recorded_death_rejected(self):
        r=person();r[1]=replace(r[1],kind='dead')
        with self.assertRaisesRegex(ValueError,'AFTER_RECORDED_DEATH'):evaluate(r)

    def test_lifetime_positive_not_automatically_incident(self):
        r=person();r[-1]=replace(r[-1],scope='lifetime',mi='positive')
        self.assertEqual(evaluate(r,'mi')['outcome_states']['UNKNOWN'],1)

    def test_unknown_baseline_not_disease_free(self):
        r=person();r[0]=replace(r[0],mi='unknown')
        self.assertEqual(evaluate(r)['flow']['excluded_unknown_baseline_history'],1)

    def test_positive_component_survives_unknown_other(self):
        r=person();r[1]=replace(r[1],mi='positive');r[-1]=replace(r[-1],stroke='unknown')
        self.assertEqual(evaluate(r)['flow']['positive'],1)

    def test_both_components_unique_union(self):
        r=person();r[1]=replace(r[1],mi='positive',stroke='positive')
        report=evaluate(r)
        self.assertEqual(report['retained_composite_people'],1)
        self.assertEqual(report['retained_mi_reports']+report['retained_stroke_reports'],2)

    def test_missing_predictor_separate_from_unknown_outcome(self):
        r=person();r[0]=replace(r[0],features={})
        report=evaluate(r)
        self.assertEqual(report['flow']['outcome_ascertainable'],1)
        self.assertEqual(report['flow']['excluded_missing_predictors'],1)

    def test_future_measurement_and_future_availability_rejected(self):
        for field in ['measured','available']:
            r=person();features=dict(r[0].features)
            features['bmi']=replace(features['bmi'],**{field:D+timedelta(days=1)})
            r[0]=replace(r[0],features=features)
            with self.assertRaisesRegex(ValueError,'LEAKAGE'):evaluate(r)

    def test_zero_eligible_no_fraction(self):
        r=person();r[0]=replace(r[0],mi='positive')
        self.assertIsNone(evaluate(r)['event_fraction'])

    def test_cross_country_same_id_not_merged(self):
        r=person();e=[replace(x,study='ELSA',wave=x.wave-5) for x in r]
        self.assertEqual(evaluate(r+e)['flow']['total_unique'],2)

    def test_four_eight_years_not_assumed_from_wave_number(self):
        self.assertEqual(evaluate(person(),years=4)['flow']['retained'],1)
        self.assertEqual(evaluate(person(),years=8)['outcome_states']['UNKNOWN'],1)


class MappingTests(unittest.TestCase):
    def test_original_core_mi_does_not_invent_tia_code(self):
        self.assertEqual(hrs_direct(2,'interval',True,'mi'),'unknown')
        self.assertEqual(hrs_direct(2,'interval',True,'stroke'),'tia')

    def test_suppression_family_prevents_complement_recovery(self):
        from downloaded_source_audit import suppress_family
        values=suppress_family([{'metric':'a','value':100},{'metric':'b','value':3}])
        self.assertTrue(all(r['value']=='SUPPRESSED_FAMILY' for r in values))

    def test_selected_column_reader_with_invented_stata_zip(self):
        from downloaded_source_audit import read_member,key
        from zipfile import ZipFile
        import pandas as pd
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);frame=pd.DataFrame({'id':[1,2],'observed':[0,1],'not_requested':[100,200]})
            path=root/'invented.dta';frame.to_stata(path,write_index=False)
            archive=root/'invented.zip'
            with ZipFile(archive,'x') as z:z.write(path,'invented.dta')
            data,metadata=read_member(archive,'invented.dta',['id','observed','absent'])
            self.assertEqual(list(data.columns),['id','observed'])
            self.assertEqual(metadata['required_absent'],['absent'])
            self.assertEqual(key(data,'id',3).tolist(),['001','002'])

    def test_shrinkage_and_binomial_planning_arithmetic(self):
        from planning_calculations import sensitivity_events,shrinkage_criterion,independent_test_size
        self.assertEqual(sensitivity_events(),246)
        self.assertEqual(sensitivity_events(.5),385)
        self.assertGreater(shrinkage_criterion(16,.1),shrinkage_criterion(8,.1))
        self.assertEqual(independent_test_size(.05)['target_total_n_expected'],7000)
    def test_upper_bound_rounds_up_without_small_cell_disclosure(self):
        from target_ceiling import public_upper_bound
        for n in [0,1,9,10,11,19,20,201]:
            self.assertGreaterEqual(public_upper_bound(n),n)
            self.assertEqual(public_upper_bound(n)%10,0)
        self.assertEqual(public_upper_bound(0),public_upper_bound(9))
    def test_stata_missing_values(self):
        for code in [None,float('nan'),'.','.d','.r','.m','.p','<missing>',-8,-9,-1]:
            self.assertEqual(hrs_mi_interval(code,True),'unknown')

    def test_unknown_raw_values_fail_closed(self):
        for value in [999,1.5,True]:
            # Bool must never masquerade as a documented response.
            self.assertEqual(hrs_mi_interval(value,True),'unknown')

    def test_direct_no_distinguished_from_assumed_zero(self):
        self.assertEqual(hrs_mi_interval(5,True),'negative')
        self.assertEqual(harmonized_mi(0,'screening_assumed'),'unknown')
        self.assertEqual(harmonized_mi(0,'direct_observed'),'negative')

    def test_rand_stroke_q2_only_interval(self):
        self.assertEqual(rand_stroke(1,2),'positive')
        self.assertEqual(rand_stroke(0,2),'negative')
        for q in [1,3,4,5,None]:self.assertEqual(rand_stroke(1,q),'unknown')
        self.assertEqual(rand_stroke(2,2),'tia')

    def test_rand_baseline_negative_needs_additional_history_proof(self):
        self.assertEqual(rand_stroke(0,2,baseline=True),'unknown')
        self.assertEqual(rand_stroke(0,2,baseline=True,history_verified=True),'negative')
        self.assertEqual(rand_stroke(5,2),'disputed')

    def test_elsa_none_requires_history_and_route(self):
        args=dict(personal=True,scope='interval',prior_negative_proven=True,branch_clear=True,explicit_completed_list=True)
        self.assertEqual(elsa_component(0,**args),'negative')
        for field in ['personal','prior_negative_proven','branch_clear','explicit_completed_list']:
            self.assertEqual(elsa_component(0,**{**args,field:False}),'unknown')

    def test_elsa_wave9_absent_confirmation_not_zero(self):
        args=dict(personal=True,scope='interval',prior_negative_proven=True,branch_clear=False,explicit_completed_list=True)
        self.assertEqual(elsa_component(0,confirmation=None,**args),'unknown')

    def test_elsa_confirmation_and_dispute_not_new_events(self):
        args=dict(personal=True,scope='interval',prior_negative_proven=True,branch_clear=True,explicit_completed_list=True)
        self.assertEqual(elsa_component(0,confirmation=1,**args),'unknown')
        for reason in [1,2,3,4]:self.assertEqual(elsa_component(0,dispute_reason=reason,**args),'disputed')

    def test_elsa_not_read_confirmation_is_unknown_not_denial(self):
        args=dict(personal=True,scope='interval',prior_negative_proven=True,branch_clear=True,explicit_completed_list=True)
        self.assertEqual(elsa_component(0,confirmation=3,**args),'unknown')

    def test_elsa_first_personal_proof_not_inw_alone(self):
        self.assertTrue(first_personal_lifetime_none([0,0,0,0,0,1],11,0,1,0,0))
        for flags,status,proxy in [([1,0,0,0,0,1],11,0),([0]*5+[1],12,0),([0]*5+[1],11,1)]:
            self.assertFalse(first_personal_lifetime_none(flags,status,proxy,1,0,0))

    def test_units(self):
        self.assertAlmostEqual(convert_unit(5,'mmol/L','total_cholesterol'),193.35)
        self.assertAlmostEqual(convert_unit(16,'kPa','sbp'),120.00986928)
        with self.assertRaises(ValueError):convert_unit(5,'unknown','total_cholesterol')

    def test_partition_blind_deterministic_nonoverlap(self):
        ids=[f'INVENTED_{i:03}' for i in range(101)]
        a=partition(ids);self.assertEqual(a,partition(ids));self.assertEqual(sum(map(len,a)),101)
        self.assertEqual(len(set(x for part in a for x in part)),101)
        with self.assertRaises(ValueError):partition(ids+ids[:1])


if __name__=='__main__':unittest.main()
