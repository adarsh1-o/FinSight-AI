from __future__ import annotations

import numpy as np
import pandas as pd


REQUIRED_COLUMNS = {
    "transaction_id", "customer_id", "account_id", "transaction_date", "amount",
    "transaction_type", "merchant_category", "payment_method", "location", "status",
}
CATEGORICAL_COLUMNS = {
    "transaction_type": {"Purchase", "Transfer", "Withdrawal"},
    "merchant_category": {"Airlines", "Amazon", "Gas", "Grocery", "Restaurant", "TechStore", "Uber"},
    "payment_method": {"ACH", "Card", "Wallet", "Wire"},
    "location": {"Foreign", "Local"},
    "status": {"Completed", "Failed", "Pending"},
}


class DatasetValidationError(ValueError):
    """Raised when transaction rows cannot safely enter the scoring pipeline."""


def validate_transactions(frame: pd.DataFrame, customers: pd.DataFrame | None = None) -> dict:
    missing_columns = sorted(REQUIRED_COLUMNS - set(frame.columns))
    if missing_columns:
        raise DatasetValidationError(f"Missing required transaction columns: {', '.join(missing_columns)}")
    errors: list[str] = []
    warnings: list[str] = []
    missing = {str(k): int(v) for k, v in frame.isna().sum().items() if v}
    for column in ("transaction_id", "transaction_date", "amount"):
        if frame[column].isna().any():
            errors.append(f"{column} contains {int(frame[column].isna().sum())} missing value(s)")
    if frame["transaction_id"].astype("string").str.strip().eq("").any():
        errors.append("transaction_id contains blank identifiers")
    duplicate_ids = int(frame["transaction_id"].duplicated(keep=False).sum())
    if duplicate_ids:
        warnings.append(f"{duplicate_ids} rows participate in duplicated transaction IDs")
    amounts = pd.to_numeric(frame["amount"], errors="coerce")
    invalid_amounts = int((~np.isfinite(amounts) | (amounts <= 0)).sum())
    if invalid_amounts:
        errors.append(f"amount contains {invalid_amounts} non-numeric, non-finite, or non-positive value(s)")
    timestamps = pd.to_datetime(frame["transaction_date"], errors="coerce")
    invalid_dates = int(timestamps.isna().sum())
    if invalid_dates:
        errors.append(f"transaction_date contains {invalid_dates} invalid timestamp(s)")
    for column, allowed in CATEGORICAL_COLUMNS.items():
        if column not in frame:
            continue
        unexpected = sorted(set(frame[column].dropna().astype(str)) - allowed)
        if unexpected:
            warnings.append(f"Unexpected {column} value(s): {', '.join(unexpected[:10])}")
    if missing:
        warnings.append("Missing values by column: " + ", ".join(f"{k}={v}" for k, v in missing.items()))
    if customers is not None and "customer_id" in customers:
        unknown = int((~frame.customer_id.isin(set(customers.customer_id.dropna()))).sum())
        if unknown:
            warnings.append(f"{unknown} transaction row(s) reference unknown customers")
    if errors:
        raise DatasetValidationError("; ".join(errors))
    return {"row_count": len(frame), "column_count": len(frame.columns), "columns": list(frame.columns),
            "dtypes": {k: str(v) for k, v in frame.dtypes.items()}, "missing_values": missing,
            "duplicate_rows": int(frame.duplicated().sum()), "duplicate_transaction_ids": duplicate_ids,
            "warnings": warnings, "errors": errors}
