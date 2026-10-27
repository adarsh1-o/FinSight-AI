from __future__ import annotations

import json
import logging
import os
import tempfile
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import OneHotEncoder, StandardScaler

from api.pipeline.validation import DatasetValidationError, validate_transactions

logger = logging.getLogger(__name__)
NUMERIC_FEATURES = ["log_amount", "transaction_hour", "day_of_week", "amount_vs_customer_average", "customer_transaction_count", "customer_average_amount"]
CATEGORICAL_FEATURES = ["transaction_type", "merchant_category", "payment_method"]


def prepare_features(frame: pd.DataFrame) -> pd.DataFrame:
    result = frame.copy()
    for column in CATEGORICAL_FEATURES:
        result[column] = result[column].fillna("Unknown").astype(str)
    result["transaction_date"] = pd.to_datetime(result["transaction_date"], errors="raise")
    result["amount"] = pd.to_numeric(result["amount"], errors="raise")
    result["log_amount"] = np.log1p(result["amount"])
    result["transaction_hour"] = result["transaction_date"].dt.hour
    result["day_of_week"] = result["transaction_date"].dt.dayofweek
    result["transaction_month"] = result["transaction_date"].dt.month
    stats = result.groupby("customer_id")["amount"].agg(customer_transaction_count="count", customer_total_amount="sum", customer_average_amount="mean", customer_median_amount="median", customer_std_amount="std")
    stats["customer_std_amount"] = stats["customer_std_amount"].fillna(0)
    result = result.join(stats, on="customer_id")
    result["amount_vs_customer_average"] = result["amount"] / (result["customer_average_amount"] + 1e-6)
    result["amount_vs_customer_median"] = result["amount"] / (result["customer_median_amount"] + 1e-6)
    q1, q3 = result["amount"].quantile([.25, .75])
    spread = q3 - q1
    result["iqr_anomaly"] = ((result.amount < q1 - 1.5 * spread) | (result.amount > q3 + 1.5 * spread)).astype(int)
    return result


def score_transactions(frame: pd.DataFrame, random_state: int = 42, contamination: float = .05) -> pd.DataFrame:
    if not 0 < contamination <= .5:
        raise ValueError("contamination must be greater than 0 and at most 0.5")
    featured = prepare_features(frame)
    transformer = ColumnTransformer([("num", StandardScaler(), NUMERIC_FEATURES), ("cat", OneHotEncoder(handle_unknown="ignore", sparse_output=False), CATEGORICAL_FEATURES)])
    matrix = transformer.fit_transform(featured)
    model = IsolationForest(n_estimators=100, contamination=contamination, random_state=random_state)
    featured["isolation_prediction"] = model.fit_predict(matrix)
    featured["isolation_score"] = model.decision_function(matrix)
    featured["ml_anomaly"] = (featured["isolation_prediction"] == -1).astype(int)
    return featured


def _atomic_csv(frame: pd.DataFrame, output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", newline="", suffix=".tmp", dir=output_path.parent, delete=False) as stream:
        temporary = Path(stream.name)
    try:
        frame.to_csv(temporary, index=False)
        os.replace(temporary, output_path)
    finally:
        temporary.unlink(missing_ok=True)


def run_pipeline(input_path: str | Path, output_path: str | Path, report_path: str | Path | None = None,
                 customers_path: str | Path | None = None, random_state: int = 42, contamination: float = .05) -> dict:
    source, destination = Path(input_path), Path(output_path)
    if not source.is_file():
        raise FileNotFoundError(f"Transaction input file not found: {source}")
    logger.info("Reading transaction input %s", source)
    original = pd.read_csv(source)
    customers = pd.read_csv(customers_path) if customers_path and Path(customers_path).is_file() else None
    audit = validate_transactions(original, customers)
    clean = original.drop_duplicates().copy()
    remaining_duplicates = clean["transaction_id"].duplicated(keep=False)
    if remaining_duplicates.any():
        raise DatasetValidationError(f"{int(remaining_duplicates.sum())} rows still have duplicate transaction IDs after exact duplicate removal")
    scored = score_transactions(clean, random_state=random_state, contamination=contamination)
    _atomic_csv(scored, destination)
    flags = int(scored.ml_anomaly.sum())
    score_summary = scored.isolation_score.describe().to_dict()
    summary = {"status": "success", "input_path": str(source), "output_path": str(destination), "input_rows": len(original), "output_rows": len(scored),
               "rows_removed": len(original) - len(scored), "duplicate_rows": audit["duplicate_rows"], "missing_values": audit["missing_values"],
               "validation_warnings": audit["warnings"], "transactions_scored": len(scored), "anomalies_flagged": flags,
               "anomaly_percentage": flags / len(scored) * 100 if len(scored) else 0, "score_distribution": score_summary,
               "model": {"name": "IsolationForest", "contamination": contamination, "random_state": random_state},
               "label_note": "Model flags indicate potential anomalies, not confirmed fraud."}
    if report_path:
        report = Path(report_path)
        report.parent.mkdir(parents=True, exist_ok=True)
        summary["report_path"] = str(report)
        report.write_text(json.dumps(summary, indent=2, default=str), encoding="utf-8")
    logger.info("Pipeline completed: %s", summary)
    return summary
