from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

from api.pipeline.validation import CATEGORICAL_COLUMNS


def _inspect_csv(path: Path) -> dict:
    if not path.is_file():
        return {"available": False}
    frame = pd.read_csv(path)
    details = {"available": True, "rows": len(frame), "columns_count": len(frame.columns), "columns": list(frame.columns),
               "dtypes": {k: str(v) for k, v in frame.dtypes.items()}, "missing_by_column": {str(k): int(v) for k, v in frame.isna().sum().items() if v},
               "duplicate_rows": int(frame.duplicated().sum())}
    if "transaction_id" in frame:
        details["duplicate_transaction_ids"] = int(frame.transaction_id.duplicated().sum())
        details["missing_or_blank_transaction_ids"] = int(frame.transaction_id.isna().sum() + frame.transaction_id.astype("string").str.strip().eq("").sum())
    if "amount" in frame:
        amount = pd.to_numeric(frame.amount, errors="coerce")
        details["invalid_amounts"] = int((~np.isfinite(amount) | (amount <= 0)).sum())
        details["amount_summary"] = amount.describe().to_dict()
    if "transaction_date" in frame:
        dates = pd.to_datetime(frame.transaction_date, errors="coerce")
        details["invalid_timestamps"] = int(dates.isna().sum())
        details["timestamp_range"] = {"min": str(dates.min()), "max": str(dates.max())}
    unexpected = {}
    for col, allowed in CATEGORICAL_COLUMNS.items():
        if col in frame:
            unexpected[col] = sorted(set(frame[col].dropna().astype(str)) - allowed)
    details["unexpected_categories"] = {k: v for k, v in unexpected.items() if v}
    return details


def build_audit(root: Path) -> dict:
    raw_path = root / "data/raw/transactions.csv"
    processed_path = root / "data/processed/transactions_with_anomalies.csv"
    labels_path = root / "data/raw/fraud_labels.csv"
    customers_path = root / "data/raw/customers.csv"
    accounts_path = root / "data/raw/accounts.csv"
    report = {"raw_transactions": _inspect_csv(raw_path), "processed_transactions": _inspect_csv(processed_path)}
    raw = pd.read_csv(raw_path) if raw_path.is_file() else pd.DataFrame()
    labels = pd.read_csv(labels_path) if labels_path.is_file() else pd.DataFrame()
    customers = pd.read_csv(customers_path) if customers_path.is_file() else pd.DataFrame()
    accounts = pd.read_csv(accounts_path) if accounts_path.is_file() else pd.DataFrame()
    if not raw.empty:
        report["cross_references"] = {
            "unknown_customer_references": int((~raw.customer_id.isin(set(customers.customer_id))).sum()) if "customer_id" in raw and "customer_id" in customers else None,
            "unknown_account_references": int((~raw.account_id.isin(set(accounts.account_id))).sum()) if "account_id" in raw and "account_id" in accounts else None,
        }
    processed = pd.read_csv(processed_path) if processed_path.is_file() else pd.DataFrame()
    report["schema_comparison"] = {"processed_extra_columns": sorted(set(processed.columns) - set(raw.columns)) if not processed.empty and not raw.empty else [],
                                   "processed_missing_raw_columns": sorted(set(raw.columns) - set(processed.columns)) if not processed.empty and not raw.empty else []}
    if not labels.empty:
        label_counts = labels.is_fraud.value_counts(dropna=False)
        raw_ids = set(raw.transaction_id.dropna()) if "transaction_id" in raw else set()
        label_ids = set(labels.transaction_id.dropna()) if "transaction_id" in labels else set()
        report["fraud_labels"] = {"available": True, "rows": len(labels), "columns": list(labels.columns),
            "missing_by_column": {str(k): int(v) for k, v in labels.isna().sum().items() if v},
            "duplicate_rows": int(labels.duplicated().sum()), "duplicate_transaction_ids": int(labels.transaction_id.duplicated().sum()),
            "invalid_is_fraud_values": sorted(set(labels.is_fraud.dropna().astype(str)) - {"True", "False", "1", "0"}) if "is_fraud" in labels else None,
            "distribution": {str(k): int(v) for k, v in label_counts.items()}, "unmatched_label_ids": len(label_ids - raw_ids),
            "transactions_without_labels": len(raw_ids - label_ids),
            "provenance": "Synthetic probabilistic rule labels generated from amount, location, hour, merchant category and status. Not independently verified fraud ground truth."}
    else:
        report["fraud_labels"] = {"available": False, "note": "No label data available; supervised metrics cannot be calculated."}
    scored = processed
    if not scored.empty and {"ml_anomaly", "isolation_score"}.issubset(scored.columns):
        flagged = scored.ml_anomaly.astype(int)
        report["anomaly_output"] = {"transactions_scored": len(scored), "flagged": int(flagged.sum()),
            "flagged_percentage": float(flagged.mean() * 100), "prediction_encoding": {"-1": "potential anomaly", "1": "normal"},
            "isolation_score_summary": scored.isolation_score.describe().to_dict(),
            "interpretation": "Unsupervised output only; this score is not a fraud probability."}
    return report


def main() -> None:
    root = Path(__file__).resolve().parents[2]
    report = build_audit(root)
    target = root / "docs/stage07_dataset_audit.json"
    target.write_text(json.dumps(report, indent=2, default=str), encoding="utf-8")
    print(f"Audit report written to {target.relative_to(root)}")
    print(json.dumps({"raw_rows": report["raw_transactions"].get("rows"), "raw_duplicates": report["raw_transactions"].get("duplicate_rows"),
        "label_rows": report["fraud_labels"].get("rows"), "label_distribution": report["fraud_labels"].get("distribution"),
        "flagged": report.get("anomaly_output", {}).get("flagged")}, indent=2))


if __name__ == "__main__":
    main()
