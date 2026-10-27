from __future__ import annotations

import pandas as pd
from sklearn.metrics import confusion_matrix, f1_score, precision_score, recall_score


def evaluate_anomalies(frame: pd.DataFrame, label_column: str = "is_fraud", prediction_column: str = "isolation_prediction") -> dict:
    if frame.empty:
        return {"status": "unavailable", "reason": "No joined label and prediction rows are available.", "rows_evaluated": 0}
    if label_column not in frame or prediction_column not in frame:
        return {"status": "unavailable", "reason": "Ground-truth labels or model predictions are missing.", "rows_evaluated": 0}
    subset = frame[[label_column, prediction_column]].dropna()
    if subset.empty:
        return {"status": "unavailable", "reason": "No complete label and prediction rows are available.", "rows_evaluated": 0}
    labels = subset[label_column].astype(int)
    if not set(labels.unique()).issubset({0, 1}):
        return {"status": "unavailable", "reason": "Ground-truth labels must contain only binary values 0 and 1.", "rows_evaluated": 0}
    # Notebook convention: Isolation Forest -1 means anomaly; map it to positive class 1.
    predictions = (pd.to_numeric(subset[prediction_column]) == -1).astype(int)
    if not set(pd.to_numeric(subset[prediction_column]).unique()).issubset({-1, 1}):
        return {"status": "unavailable", "reason": "Isolation Forest predictions must use -1 for anomaly and 1 for normal.", "rows_evaluated": 0}
    tn, fp, fn, tp = confusion_matrix(labels, predictions, labels=[0, 1]).ravel()
    return {"status": "synthetic_benchmark", "rows_evaluated": len(subset), "label_mapping": "is_fraud: false=0/true=1; isolation_prediction: -1=anomaly(1), 1=normal(0)",
            "precision": float(precision_score(labels, predictions, zero_division=0)),
            "recall": float(recall_score(labels, predictions, zero_division=0)),
            "f1_score": float(f1_score(labels, predictions, zero_division=0)),
            "confusion_matrix": {"true_negative": int(tn), "false_positive": int(fp), "false_negative": int(fn), "true_positive": int(tp)},
            "false_positive_rate": float(fp / (fp + tn)) if fp + tn else 0.0,
            "true_positive_rate": float(tp / (tp + fn)) if tp + fn else 0.0,
            "transactions_flagged": int(predictions.sum()), "flagged_percentage": float(predictions.mean() * 100),
            "label_caveat": "Generator-created probabilistic heuristic labels; metrics are a synthetic benchmark and do not measure real-world fraud detection."}
