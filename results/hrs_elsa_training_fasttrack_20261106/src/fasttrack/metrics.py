"""Ranking/decision/calibration metrics and paired participant bootstrap."""
import numpy as np
from sklearn.metrics import average_precision_score,roc_auc_score,brier_score_loss
from sklearn.linear_model import LogisticRegression
from .contracts import need


def metrics(y,p,threshold=.5):
    y,p=np.asarray(y),np.asarray(p)
    need(y.shape==p.shape and y.ndim==1 and len(y)>0 and np.isin(y,[0,1]).all()
         and np.isfinite(p).all() and ((p>=0)&(p<=1)).all(),'INVALID_METRIC_INPUT')
    need(0<=threshold<=1,'INVALID_THRESHOLD')
    pred=p>=threshold
    tp=int(((y==1)&pred).sum());tn=int(((y==0)&~pred).sum());fp=int(((y==0)&pred).sum());fn=int(((y==1)&~pred).sum())
    divide=lambda a,b:float(a/b) if b else None
    both=len(np.unique(y))==2
    return {'n':len(y),'positive':int(y.sum()),'prevalence':float(y.mean()),'threshold':float(threshold),
        'tp':tp,'tn':tn,'fp':fp,'fn':fn,'positive_predictions':int(pred.sum()),
        'accuracy':float((tp+tn)/len(y)),'precision':divide(tp,tp+fp),'recall':divide(tp,tp+fn),'sensitivity':divide(tp,tp+fn),
        'specificity':divide(tn,tn+fp),'f1':divide(2*tp,2*tp+fp+fn),
        'ap':float(average_precision_score(y,p)) if both else None,
        'auroc':float(roc_auc_score(y,p)) if both else None,'brier':float(brier_score_loss(y,p)),
        'mean_prediction':float(p.mean()),'calibration_in_the_large_probability_difference':float(p.mean()-y.mean()),
        'fixed_decile_calibration':[{'lower':i/10,'upper':(i+1)/10,
            'n':int(((p>=i/10)&((p<(i+1)/10) if i<9 else (p<=1))).sum()),
            'mean_score':float(p[(p>=i/10)&((p<(i+1)/10) if i<9 else (p<=1))].mean())
               if ((p>=i/10)&((p<(i+1)/10) if i<9 else (p<=1))).any() else None,
            'observed_fraction':float(y[(p>=i/10)&((p<(i+1)/10) if i<9 else (p<=1))].mean())
               if ((p>=i/10)&((p<(i+1)/10) if i<9 else (p<=1))).any() else None} for i in range(10)],
        'confusion_matrix_actual_rows_predicted_columns':[[tn,fp],[fn,tp]]}


def logit(p):
    p=np.clip(p,1e-6,1-1e-6);return np.log(p/(1-p))[:,None]


class OperatingPoint:
    def fit(self,y,p,role):
        need(role=='target_calibration','CALIBRATION_ROLE_FORBIDDEN')
        self.platt=None;self.threshold=None
        counts=[int((y==v).sum()) for v in (0,1)]
        self.status='INSUFFICIENT_CALIBRATION_SUPPORT'
        if min(counts)>=10:
            model=LogisticRegression(C=1e6,max_iter=1000).fit(logit(p),y)
            if model.coef_[0,0]>0:self.platt=model;self.status='POSITIVE_SLOPE_PLATT_FIT'
            else:self.status='NONPOSITIVE_CALIBRATION_SLOPE_NOT_APPLIED'
        if min(counts)>=5:
            q=self.probability(p)
            options=np.unique(np.r_[0.,.5,1.,q])
            def objective(t):
                pred=q>=t;tp=int(((y==1)&pred).sum());fp=int(((y==0)&pred).sum());fn=int(((y==1)&~pred).sum())
                return (2*tp/(2*tp+fp+fn) if 2*tp+fp+fn else 0,t)
            self.threshold=float(max(options,key=objective))
        self.counts=counts
        return self

    def probability(self,p):
        return p if self.platt is None else self.platt.predict_proba(logit(p))[:,1]

    def report(self,y,p):
        return {'status':self.status,'training_side_class_counts':self.counts,'threshold':self.threshold,
                'metrics':None if self.threshold is None else metrics(y,self.probability(p),self.threshold),
                'source_weights_fixed_does_not_mean_zero_target_calibration_labels':True}


def paired_bootstrap(y,predictions,reps,seed):
    rng=np.random.default_rng(seed);samples={k:[] for k in predictions};difference=[];invalid=0
    for _ in range(reps):
        ix=rng.integers(len(y),size=len(y))
        if len(np.unique(y[ix]))<2:invalid+=1;continue
        scores={}
        for k,p in predictions.items():
            m=metrics(y[ix],p[ix]);samples[k].append([m['ap'],m['auroc'],m['brier']]);scores[k]=m['ap']
        if 'selective' in scores and 'full' in scores:difference.append(scores['selective']-scores['full'])
    interval=lambda values:None if len(values)<20 else np.quantile(values,[.025,.975],axis=0).tolist()
    return {'method_95_intervals_AP_AUROC_Brier':{k:interval(v) for k,v in samples.items()},
            'paired_selective_minus_full_AP_95_interval':interval(difference),
            'valid_resamples':reps-invalid,'single_class_resamples_unavailable':invalid,
            'interpretation':'CONDITIONAL_ON_FITTED_MODELS_AND_THIS_PARTICIPANT_SAMPLE_NOT_CLINICAL_VALIDATION'}
