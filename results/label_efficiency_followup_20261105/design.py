"""Outcome-blind participant folds and nested label acquisition."""
import numpy as np
from local_execution import need


def outer_splits(ids, folds, seeds):
    need(folds in (3,5) and len(set(ids.tolist())) == len(ids) and len(ids) >= folds, 'OUTER_DESIGN_INVALID')
    canonical = np.argsort(ids,kind='stable')
    for seed in seeds:
        permutation = np.random.default_rng(seed).permutation(canonical)
        heldouts = np.array_split(permutation,folds)
        for fold,test in enumerate(heldouts):
            train = np.concatenate([x for i,x in enumerate(heldouts) if i != fold])
            order = np.random.default_rng(seed+1000*(fold+1)).permutation(train)
            need(not set(train)&set(test) and set(train)|set(test)==set(range(len(ids))), 'OUTER_MEMBERSHIP_INVALID')
            yield {'repeat_seed':seed,'fold':fold,'outer':test,'ordered_training':order}


def budget_roles(split, fraction, cycle=('fit','fit','fit','stop','calibration')):
    need(fraction in (.10,.25,.50,.75,1.), 'UNREGISTERED_LABEL_BUDGET')
    order=split['ordered_training']; n=int(np.floor(len(order)*fraction))
    selected=order[:n]
    roles={name:np.array([x for i,x in enumerate(selected) if cycle[i%len(cycle)]==name],dtype=np.int64)
           for name in ['fit','stop','calibration']}
    need(sum(len(x) for x in roles.values())==n and len(set(selected.tolist()))==n
         and not set(selected)&set(split['outer']), 'BUDGET_LEAKAGE')
    return {**roles,'selected':selected,'budget_n':n,'outer_training_n':len(order),'fraction':fraction}


def threshold_from_calibration(y,probabilities,protocol,select):
    # Never inspect an outer label. No fallback/redraw when class support fails.
    y=np.asarray(y)
    positives=int(y.sum()); negatives=len(y)-positives
    if positives < protocol['calibration_min_positive'] or negatives < protocol['calibration_min_negative']:
        return {'status':'INSUFFICIENT_CALIBRATION_CLASS_SUPPORT','threshold':None,
                'positive':positives,'negative':negatives}
    return {'status':'EXPLORATORY_TRAINING_SIDE_F1_THRESHOLD','threshold':select(y,probabilities),
            'positive':positives,'negative':negatives,'precision_guarantee':False}
