"""Metrics for imbalanced classification (exoplanet detection).

Never accuracy alone: precision, recall, F1, ROC-AUC, PR-AUC.
"""
from __future__ import annotations

import numpy as np
from sklearn.metrics import (precision_score, recall_score, f1_score,
                             roc_auc_score, average_precision_score)


def evaluate(y_true: np.ndarray, y_score: np.ndarray, threshold: float = 0.5) -> dict:
    """All metrics from labels + predicted probabilities."""
    y_pred = (y_score >= threshold).astype(int)
    return {
        "precision": precision_score(y_true, y_pred, zero_division=0),
        "recall": recall_score(y_true, y_pred, zero_division=0),
        "f1": f1_score(y_true, y_pred, zero_division=0),
        "roc_auc": roc_auc_score(y_true, y_score),
        "pr_auc": average_precision_score(y_true, y_score),
    }


def summarize(fold_scores: list[dict]) -> dict:
    """Mean +/- std over CV folds for every metric."""
    keys = fold_scores[0].keys()
    out = {}
    for k in keys:
        vals = np.array([s[k] for s in fold_scores])
        out[k] = f"{vals.mean():.3f} +/- {vals.std():.3f}"
        out[k + "_mean"] = float(vals.mean())
    return out
