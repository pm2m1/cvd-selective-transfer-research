"""Inactive training-only median/mode benchmark, NOT multiple imputation.

Eight roles retained; optional missing indicators expand model parameters.
No feature, outcome, interview, timing or baseline eligibility is derived here.
Structural absence of an examination is rejected, not treated as an ordinary
missing numeric cell. Real deployment needs its own reviewed feature domains.
"""
from __future__ import annotations

import numpy as np
from .contracts import FEATURES, Role


class MixedTrainingImputer:
    def __init__(self, categorical_levels, *, add_indicators=True):
        expected={"sex","smoking","diabetes","bp_treatment"}
        if set(categorical_levels)!=expected or type(add_indicators) is not bool:
            raise ValueError("EXPLICIT_CATEGORICAL_DOMAINS_REQUIRED")
        self.levels={}
        for k,values in categorical_levels.items():
            if not values or len(set(values))!=len(values) or any(type(v) not in (int,float) or not np.isfinite(v) for v in values):
                raise ValueError("INVALID_CATEGORICAL_DOMAIN")
            self.levels[k]=tuple(sorted(values))
        self.add_indicators=add_indicators;self.fill_=None;self.fit_role=None

    def _check(self, values, feature_names, role, measurement_eligibility_verified, structural_missing):
        if role not in set(Role) or role==Role.TARGET_TEST: raise PermissionError("TARGET_TEST_OR_UNKNOWN_ROLE_FORBIDDEN")
        if tuple(feature_names)!=FEATURES or measurement_eligibility_verified is not True:
            raise ValueError("FEATURE_OR_MEASUREMENT_CONTRACT_UNRESOLVED")
        x=np.asarray(values)
        if x.ndim!=2 or x.shape[1]!=len(FEATURES) or x.dtype.kind not in "iuf" or np.isinf(x).any():
            raise ValueError("NUMERIC_MISSING_CELLS_ONLY_NO_COERCION")
        mask=np.asarray(structural_missing)
        if mask.shape!=x.shape or mask.dtype.kind!="b" or mask.any():
            raise ValueError("STRUCTURAL_MEASUREMENT_ABSENCE_NOT_IMPUTABLE_HERE")
        for k,levels in self.levels.items():
            col=x[:,FEATURES.index(k)];observed=col[~np.isnan(col)]
            if not np.isin(observed,levels).all(): raise ValueError("UNREVIEWED_CATEGORY_NOT_COERCED")
        return x.astype(float)

    def fit(self, values, feature_names, role, *, measurement_eligibility_verified, structural_missing):
        if self.fill_ is not None: raise ValueError("IMPUTER_ALREADY_FITTED")
        if role not in {Role.SOURCE_TRAIN,Role.TARGET_ADAPTATION}: raise PermissionError("TRAINING_ONLY_FIT_REQUIRED")
        x=self._check(values,feature_names,role,measurement_eligibility_verified,structural_missing)
        if not len(x): raise ValueError("EMPTY_TRAINING_POOL")
        fill=[]
        for j,name in enumerate(FEATURES):
            observed=x[:,j][~np.isnan(x[:,j])]
            if not len(observed): raise ValueError("ENTIRE_TRAINING_PREDICTOR_UNIDENTIFIED")
            if name in self.levels:
                levels=self.levels[name]; fill.append(max(levels,key=lambda v:int(np.sum(observed==v))))
            else:fill.append(float(np.median(observed)))
        self.fill_=np.asarray(fill);self.fit_role=role;return self

    def transform(self, values, feature_names, role, *, measurement_eligibility_verified, structural_missing):
        if self.fill_ is None: raise ValueError("IMPUTER_NOT_FITTED")
        x=self._check(values,feature_names,role,measurement_eligibility_verified,structural_missing)
        missing=np.isnan(x);imputed=np.where(missing,self.fill_,x)
        return np.column_stack((imputed,missing.astype(float))) if self.add_indicators else imputed
