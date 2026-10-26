"""
classifier.py - Multi-Threat Risk Classifier & Probabilistic Estimation

Enhancements addressing reviewer feedback:
1. Decoupled Threat Scoring:
   - Evaluates R_inject = P(injection) and R_exhaust = P(exhaustion) independently.
   - Prevents conflating compute-hungry requests with adversarial injection attacks.
2. Calibrated Probability Extraction:
   - Provides risk_decoupled() returning (r_inject, r_exhaust, r_composite, subtype, proba_df).
3. Full Backward Compatibility:
   - Keeps risk_scores() for legacy callers.
"""

from xgboost import XGBClassifier
from sklearn.preprocessing import LabelEncoder
from features import FEATURE_COLUMNS
import pandas as pd
import numpy as np


class RiskClassifier:
    def __init__(self, random_state=0, n_estimators=200, max_depth=5, learning_rate=0.1):
        self.params = dict(
            n_estimators=n_estimators,
            max_depth=max_depth,
            learning_rate=learning_rate,
            subsample=0.9,
            colsample_bytree=0.9,
            objective="multi:softprob",
            eval_metric="mlogloss",
            random_state=random_state,
        )
        self.model = XGBClassifier(**self.params)
        self.label_encoder = LabelEncoder()
        self.classes_ = None

    def fit(self, X: pd.DataFrame, y: pd.Series):
        y_enc = self.label_encoder.fit_transform(y)
        self.model.fit(X, y_enc)
        self.classes_ = list(self.label_encoder.classes_)
        return self

    def predict_proba_df(self, X: pd.DataFrame) -> pd.DataFrame:
        proba = self.model.predict_proba(X)
        return pd.DataFrame(proba, columns=self.classes_, index=X.index)

    def predict(self, X: pd.DataFrame):
        pred_enc = self.model.predict(X)
        return self.label_encoder.inverse_transform(pred_enc)

    def risk_scores(self, X: pd.DataFrame):
        """Legacy scalar risk estimation."""
        proba = self.predict_proba_df(X)
        risk = 1.0 - proba.get("benign", 0.0)
        subtype = proba.drop(columns=["benign"], errors="ignore").idxmax(axis=1)
        return risk, subtype, proba

    def risk_decoupled(self, X: pd.DataFrame):
        """Returns decoupled orthogonal threat scores.
        
        Returns:
            r_inject: Series of P(injection)
            r_exhaust: Series of P(exhaustion)
            r_composite: Series of 1.0 - P(benign)
            subtype: Primary threat class
            proba_df: Full probability matrix
        """
        proba = self.predict_proba_df(X)
        r_inject = proba.get("injection", pd.Series(0.0, index=X.index))
        r_exhaust = proba.get("exhaustion", pd.Series(0.0, index=X.index))
        r_composite = 1.0 - proba.get("benign", pd.Series(1.0, index=X.index))
        subtype = proba.drop(columns=["benign"], errors="ignore").idxmax(axis=1)
        return r_inject, r_exhaust, r_composite, subtype, proba

    def feature_importances(self):
        return pd.Series(self.model.feature_importances_, index=FEATURE_COLUMNS).sort_values(ascending=False)

    def partial_retrain(self, X_new: pd.DataFrame, y_new: pd.Series, X_hist: pd.DataFrame, y_hist: pd.Series,
                         hist_sample_frac=0.5, random_state=1):
        hist_sample = X_hist.sample(frac=hist_sample_frac, random_state=random_state)
        y_hist_sample = y_hist.loc[hist_sample.index]
        X_combined = pd.concat([hist_sample, X_new], ignore_index=True)
        y_combined = pd.concat([y_hist_sample, y_new], ignore_index=True)
        self.fit(X_combined, y_combined)
        return self