"""Source-training-only median/mode imputation; explicit missing indicators."""
import numpy as np
from .contracts import VIEWS,need


class BaselinePreprocessor:
    def __init__(self):
        self.fill=None

    def fit(self,x,role):
        need(role=='source_train' and self.fill is None,'PREPROCESSOR_FIT_ROLE_OR_REFIT_FORBIDDEN')
        x=np.asarray(x,dtype=float)
        need(x.ndim==2 and x.shape[1]==8 and np.isfinite(x).any(axis=0).all(),'WHOLLY_MISSING_TRAINING_FEATURE')
        self.fill=np.zeros(8)
        for j in range(8):
            observed=x[np.isfinite(x[:,j]),j]
            if j in (1,5,6,7):
                values,counts=np.unique(observed,return_counts=True);self.fill[j]=values[np.argmax(counts)]
            else:self.fill[j]=np.median(observed)
        filled=np.where(np.isnan(x),self.fill,x)
        self.mean=filled.mean(0);self.scale=filled.std(0);self.scale[self.scale<1e-8]=1.
        return self

    def transform(self,x):
        need(self.fill is not None,'PREPROCESSOR_NOT_FIT')
        x=np.asarray(x,dtype=float);missing=np.isnan(x);filled=np.where(missing,self.fill,x)
        result={}
        for name,indices in VIEWS.items():
            pieces=[]
            for j in indices:
                if j==5:
                    pieces.append((filled[:,j,None]==np.arange(3)).astype(float))
                elif j in (1,6,7):pieces.append(filled[:,j,None])
                else:pieces.append((filled[:,j,None]-self.mean[j])/self.scale[j])
                pieces.append(missing[:,j,None].astype(float))
            result[name]=np.concatenate(pieces,axis=1).astype('float32')
        need(all(np.isfinite(v).all() for v in result.values()),'NONFINITE_TRANSFORM')
        return result


def flat(views):
    return np.concatenate(list(views.values()),axis=1)
