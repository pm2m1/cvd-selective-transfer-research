"""Pure supplementary operating-point summaries; never choose a test cutoff."""
import numpy as np
from frozen_metrics import analyze as reconcile,metrics,summarize
from local_execution import need

GRID = tuple(i/100 for i in range(5,51,5))
UNESTABLISHED = 'ORIGINAL_VALIDATION_OPTIMAL_THRESHOLD_NOT_ESTABLISHED'


def analyze(y, models, thresholds, refs, inventory, synthetic=False):
    # ALL requested models/draws must reconcile BEFORE any threshold report exists.
    baseline=reconcile(y,models,thresholds,refs,synthetic)
    need(set(models)=={m['model_id'] for m in inventory},'REQUESTED_MODEL_INVENTORY_MISMATCH')
    report={'schema':'frozen-mhas-threshold-sweep-private-v1',
        'analysis':'SYNTHETIC_ONLY' if synthetic else 'SUPPLEMENTARY_DESCRIPTIVE_FROZEN_TEST_THRESHOLD_SWEEP',
        'not_new_independent_confirmation':True,'test_threshold_selected':False,'threshold_grid':list(GRID),
        'distinct_test_participants':len(y),'positive_reports':int(np.sum(y)),
        'negative_observations':int(len(y)-np.sum(y)),'same_participants_across_draws':True,
        'probability_ensemble':False,'sd_ddof':1,'ranking_reconciliation':'ALL_REQUESTED_MODELS_AND_DRAWS_MATCHED',
        'absolute_tolerance':1e-8,'relative_tolerance':1e-8,
        'validation_status':UNESTABLISHED if all(t is None for t in thresholds.values()) else 'AUTHENTIC_ORIGINAL_VALIDATION_ONLY_POST_HOC',
        'models':{}}
    for m in inventory:
        name=m['model_id'];matrix=models[name];draws=m['draw_ids']
        need(matrix.shape==(len(draws),len(y)),'DRAW_SHAPE_MISMATCH')
        original=baseline['models'][name]['fixed_0_50']['per_draw']
        rows=[]
        for threshold in GRID:
            per_draw=[]
            for draw,p,reference in zip(draws,matrix,original):
                value=metrics(y,p,threshold)
                need(all(value[k]==reference[k] for k in ('ap','auroc','brier')),'RANKING_METRICS_CHANGED_WITH_THRESHOLD')
                per_draw.append({'draw_id':draw,**value})
            rows.append({'threshold':threshold,'per_draw':per_draw,
                         'summary':summarize([{k:v for k,v in p.items() if k!='draw_id'} for p in per_draw])})
        selected=None
        if thresholds.get(name) is not None:
            need(len(thresholds[name])==len(draws),'VALIDATION_THRESHOLD_DRAW_MISMATCH')
            per_draw=[{'draw_id':d,**metrics(y,p,t)} for d,p,t in zip(draws,matrix,thresholds[name])]
            selected={'threshold_origin':'POST_HOC_AUTHENTIC_ORIGINAL_VALIDATION_F1_ONLY',
                'rule':'maximum validation F1; ties highest threshold; no test-label optimization',
                'per_draw':per_draw,'summary':summarize([{k:v for k,v in p.items() if k!='draw_id'} for p in per_draw])}
        report['models'][name]={'draw_ids':draws,'draw_count':len(draws),
            'fixed_test_thresholds':rows,'validation_selected':selected,
            'validation_status':UNESTABLISHED if selected is None else 'AUTHENTIC_ORIGINAL_VALIDATION_ONLY_POST_HOC',
            'unchanged_ranking':{k:{'per_draw':[x[k] for x in original],
                'mean':float(np.mean([x[k] for x in original]))} for k in ('ap','auroc','brier')}}
    return report
