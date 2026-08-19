"""Classical ML baselines for transit classification (Stage 2)."""
from __future__ import annotations

from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import RandomForestClassifier
from sklearn.svm import SVC
from xgboost import XGBClassifier


def make_models(seed: int = 42) -> dict:
    return {
        "LogisticRegression": LogisticRegression(max_iter=2000, random_state=seed),
        "RandomForest": RandomForestClassifier(n_estimators=200, random_state=seed),
        "SVM": SVC(probability=True, random_state=seed),
        "XGBoost": XGBClassifier(n_estimators=200, eval_metric="logloss",
                                 random_state=seed, verbosity=0),
    }
