"""Build CSV evidence matrices from public metadata and sanitized aggregate files."""
from pathlib import Path
import csv,json
ROOT=Path(__file__).resolve().parent
H='https://hrsdata.isr.umich.edu/data-products/rand-hrs-longitudinal-file-2022'
E='https://doc.ukdataservice.ac.uk/doc/5050/mrdoc/pdf/5050_gateway_harmonized_elsa_h_2002-2023.pdf'
G='https://hrsdata.isr.umich.edu/sites/default/files/documentation/other/1694551378/Harmonized%20HRS%20D%201992-2021.pdf'


def write_csv(name,rows):
    with (ROOT/name).open('x',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)


def main():
    fields=[
      ('age','r11agey_e','r6agey','years','derived interview age','age50+; match landmark, not future age','high','background','present; baseline timing still required'),
      ('sex','ragender','indsex (Core6); ragender auxiliary','category','reported/longitudinal derived','use baseline-available report; all-wave first-nonmissing may use later information','high conditional','background','present; do not silently backfill from future'),
      ('education','raedyrs; raeduc','raeducl','years / country qualification / three-tier','self-reported educational attainment','review US qualifications versus ISCED3 tiers; establish baseline availability','moderate','background optional','present; lifetime derived first-nonmissing needs temporal audit'),
      ('bmi_measured','r11mbmi (Gateway D)','r6mbmi','kg/m2','physical/nurse anthropometry','same definition; distinguish estimated weight, invalid measurement and skipped nurse visit','moderate-high conditional','metabolic','present; nurse/exam landmark unresolved'),
      ('hypertension_reported','r11hibpe','r6hibpe','binary','ever doctor diagnosis','not equivalent to elevated measured BP; preserve unknown','moderate','comorbidity','present; diagnosis/care-access differences'),
      ('sbp_measured','r11systo (Gateway D)','r6systo','mmHg','physical/nurse readings','check valid readings and protocol; ELSA mean2/3 fallback1/2; no future-wave substitution','moderate-high conditional','haemodynamic','present; actual measurement dates unresolved'),
      ('dbp_measured','r11diasto (Gateway D)','r6diasto','mmHg','physical/nurse readings','same timing/protocol checks as SBP','moderate-high conditional','haemodynamic','present; actual measurement dates unresolved'),
      ('diabetes','r11diabe','r6diabe','binary','ever doctor diagnosis','do not equate diagnosis absence with normal HbA1c; all-condition-none recipe restricts variation','moderate','comorbidity','present'),
      ('smoking','r11smokev + r11smoken','r6smokev + r6smoken','never/former/current','self-report','derive only with documented ever/current skip rules; missing is not never','moderate-high','behaviour','present'),
      ('bp_treatment','r11rxhibp (Gateway D)','r6rxhibp','binary','reported medication','preserve medication/nonapplicable routing; not interchangeable with measured hypertension','moderate','comorbidity/medication','present'),
      ('alcohol','r11drink; finer quantity not validated','r6drink; r6drinkd_e; r6drinkwn_e','binary / days / units','self-report; ELSA self-completion','ever/current/reference periods differ; standard drinks and UK units not automatically equivalent','low-moderate','behaviour optional','r6drink present; detailed quantities documented not selected-file validated'),
      ('physical_activity','r11vgactx','r6vgactx_e; r6mdactx_e','ordered frequency','self-report','HRS daily category and ELSA no-daily category differ; coarsen only by explicit map','moderate','behaviour optional','vigorous fields present; modified ELSA scale'),
      ('total_cholesterol','NOT_ESTABLISHED_IN_SELECTED_EIGHT_ROLE_SOURCES','NOT_ESTABLISHED_RAW_ASSAY_FIELD','mg/dL or mmol/L','HRS biomarker assay versus ELSA blood assay','verify assay platform/sample, fasting/medications/date; conversion1mmol/L=38.67mg/dL not assay equivalence','unresolved','metabolic optional','additional biomarker products/fields required'),
      ('hdl','NOT_ESTABLISHED_IN_SELECTED_EIGHT_ROLE_SOURCES','NOT_ESTABLISHED_RAW_ASSAY_FIELD','mg/dL or mmol/L','biomarker assay','same assay/timing restrictions as total cholesterol','unresolved','metabolic optional','not invented to restore original ten-feature architecture'),
      ('general_health','r11shlt','r6shlt','ordered1-5','self-report','retain order; cultural response differences; no claim of measurement invariance','moderate','optional revised view','present'),
      ('functional_limitations','EXACT_STUB_NOT_ESTABLISHED; r11adla absent','r6adla plus missing-count companion','count of activities','self-reported functional difficulties','verify identical component list and missing-item construction before comparing counts','unresolved-moderate','optional revised view','ELSA five-item definition documented; source field not substituted'),
      ('income_wealth','NOT_ESTABLISHED_WAVE_SPECIFIC_PUBLIC_FIELD','NOT_ESTABLISHED_WAVE_SPECIFIC_PUBLIC_FIELD','currency / purchasing power','survey amounts/imputations','year/country prices, PPP and imputations require explicit mapping; not direct currency conversion alone','unresolved','background optional','not populated from guesswork'),
      ('family_history','NO_COMMON_VALIDATED_FIELD_ESTABLISHED','NO_COMMON_VALIDATED_FIELD_ESTABLISHED','condition-specific','family report if available','require same relatives/condition/reference period; no invented common variable','unresolved','optional','not required in current eight-role contract'),
    ]
    rows=[]
    for role,hrs,elsa,unit,method,transform,reliability,view,status in fields:
        rows.append({'predictor':role,'HRS_field':hrs,'ELSA_field':elsa,'baseline_waves':'HRS2012/w11; ELSAW6/2012-13',
            'unit':unit,'measurement':method,'missing_codes':'Harmonized Stata tags and plain missing; Core ELSA -1/-8/-9 and W8 -4; field-specific documentation required',
            'transformation':transform,'comparability':reliability,'view_role':view,'availability_status':status,
            'pre_outcome_requirement':'measured AND available by validated prediction landmark; no future-wave fills','source_urls':H+' ; '+G+' ; '+E})
    write_csv('FEATURE_HARMONIZATION_MATRIX.csv',rows)
    screen=json.loads((ROOT/'LOCAL_SOURCE_SCREEN.json').read_text());bounds=json.loads((ROOT/'TARGET_EVENT_UPPER_BOUNDS.json').read_text())
    counts=[]
    for r in screen['cohort_screens']:
        counts.append({'study':r['study'],'baseline':'HRS2012 or ELSAW6','endpoint':r['endpoint'],'horizon_years':r['horizon_years'],
          'metric':r['metric'],'value':r['value'],'status':r['status'],'interpretation':r['limitation']})
    for r in bounds['rows']:
        counts.append({'study':'ELSA','baseline':r['population'],'endpoint':r['endpoint'],'horizon_years':r['nominal_horizon_years'],
            'metric':'ROUNDED_UP_UPPER_BOUND_NOT_ACTUAL_EVENT_COUNT','value':r['conservative_rounded_up_max_qualifying_events'],
            'status':'MATHEMATICAL_UPPER_BOUND_FROM_AUTHORIZED_REAL_SCREEN','interpretation':r['interpretation']})
    metrics=['prior_endpoint_exclusions','sufficient_followup','ascertainable_incident_outcomes','missing_outcomes',
             'retained_after_predictors_and_timing','incident_mi','incident_stroke','unique_incident_composite',
             'adequately_observed_nonevents','incident_report_fraction','events_by_age','events_by_sex',
             'source_training_events','source_validation_events','target_adaptation_events','target_calibration_events','independent_target_test_events']
    for study in ['HRS','ELSA']:
        for endpoint in ['strict_composite','strict_mi','strict_stroke']:
            for horizon in [4,6,8]:
                for metric in metrics:
                    counts.append({'study':study,'baseline':'HRS2012 or ELSAW6','endpoint':endpoint,'horizon_years':horizon,
                        'metric':metric,'value':'NOT_COMPUTABLE_ROUTE_TIMING_BLOCKED',
                        'status':'FINAL_INCIDENT_COHORT_NOT_CERTIFIED',
                        'interpretation':'Access was granted, but full raw-route/calendar/measurement evidence is incomplete; not numeric zero and not denial of existing downloads.'})
    write_csv('ELIGIBILITY_AND_EVENT_COUNTS.csv',counts)
    write_csv('MISSINGNESS_SCREEN.csv',screen['missingness_screens'])


if __name__=='__main__':main()
