from __future__ import annotations

from datetime import date
from io import StringIO

import pandas as pd
from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import Response

from api.data_service import data_service
from api.pipeline.evaluation import evaluate_anomalies
from api.pipeline.validation import DatasetValidationError, validate_transactions

router = APIRouter(prefix="/api", tags=["stage-07"])
FILTERS = {"date_from", "date_to", "transaction_type", "merchant_category", "payment_method", "status", "location", "customer_id"}


def _filtered(params: dict, anomaly_status: str = "all", transaction_id: str | None = None,
              amount_min: float | None = None, amount_max: float | None = None) -> pd.DataFrame:
    df = data_service.get_transactions()
    if df.empty:
        return df.copy()
    df = data_service.apply_filters(df, **{key: params.get(key) for key in FILTERS})
    if anomaly_status == "flagged" and "ml_anomaly" in df:
        df = df[df.ml_anomaly == 1]
    elif anomaly_status == "normal" and "ml_anomaly" in df:
        df = df[df.ml_anomaly == 0]
    if transaction_id:
        df = df[df.transaction_id.astype(str).str.contains(transaction_id, case=False, regex=False)]
    if amount_min is not None:
        df = df[df.amount >= amount_min]
    if amount_max is not None:
        df = df[df.amount <= amount_max]
    return df


@router.get("/quality/summary")
def quality_summary():
    raw = data_service.read_optional_csv(data_service.raw_transactions_path)
    processed = data_service.get_transactions()
    if raw.empty and processed.empty:
        return {"status": "unavailable", "reason": "Transaction data is unavailable."}
    source = raw if not raw.empty else processed
    customers = data_service.read_optional_csv(data_service.customers_path)
    try:
        audit = validate_transactions(source, customers if not customers.empty else None)
        status = "needs_cleaning" if audit["warnings"] else "ok"
    except DatasetValidationError as exc:
        audit = {"status": "validation_failed", "message": str(exc), "row_count": len(source), "column_count": len(source.columns),
                 "columns": list(source.columns), "missing_values": {str(k): int(v) for k, v in source.isna().sum().items() if v},
                 "duplicate_rows": int(source.duplicated().sum()), "duplicate_transaction_ids": int(source.transaction_id.duplicated().sum()) if "transaction_id" in source else None}
        status = "validation_failed"
    labels = data_service.read_optional_csv(data_service.fraud_labels_path)
    if not labels.empty and "is_fraud" in labels:
        audit["synthetic_label_availability"] = {"available": True, "rows": len(labels), "positive": int(labels.is_fraud.astype(bool).sum()),
            "negative": int((~labels.is_fraud.astype(bool)).sum()), "note": "Generator-created heuristic labels; synthetic benchmark only."}
    else:
        audit["synthetic_label_availability"] = {"available": False, "note": "No usable fraud-label file is available."}
    audit.update({"status": status, "processed_rows": len(processed), "anomaly_columns_available": all(c in processed for c in ("isolation_prediction", "isolation_score", "ml_anomaly"))})
    return audit


@router.get("/anomalies/evaluation")
def anomaly_evaluation():
    transactions = data_service.get_transactions()
    labels = data_service.read_optional_csv(data_service.fraud_labels_path)
    if transactions.empty:
        return {"status": "unavailable", "reason": "Processed transactions are unavailable.", "rows_evaluated": 0}
    if labels.empty or not {"transaction_id", "is_fraud"}.issubset(labels.columns):
        return {"status": "unavailable", "reason": "Usable synthetic ground-truth labels are unavailable.", "rows_evaluated": 0}
    joined = transactions.merge(labels[["transaction_id", "is_fraud"]], on="transaction_id", how="inner", validate="one_to_one")
    return evaluate_anomalies(joined)


def _params(date_from: date | None, date_to: date | None, transaction_type: str | None,
            merchant_category: str | None, payment_method: str | None, status: str | None,
            location: str | None, customer_id: str | None) -> dict:
    if date_from and date_to and date_from > date_to:
        raise HTTPException(status_code=422, detail="date_from must be on or before date_to")
    return {"date_from": date_from.isoformat() if date_from else None, "date_to": date_to.isoformat() if date_to else None,
            "transaction_type": transaction_type, "merchant_category": merchant_category, "payment_method": payment_method,
            "status": status, "location": location, "customer_id": customer_id}


def _serialize(frame: pd.DataFrame) -> list[dict]:
    frame = frame.copy()
    if "transaction_date" in frame:
        frame["transaction_date"] = pd.to_datetime(frame.transaction_date, errors="coerce").dt.strftime("%Y-%m-%dT%H:%M:%S")
    return frame.where(pd.notna(frame), None).to_dict(orient="records")


def _attach_synthetic_labels(frame: pd.DataFrame) -> pd.DataFrame:
    labels = data_service.read_optional_csv(data_service.fraud_labels_path)
    if not labels.empty and {"transaction_id", "is_fraud"}.issubset(labels.columns):
        label_map = labels.drop_duplicates("transaction_id").set_index("transaction_id").is_fraud
        frame = frame.copy()
        frame["synthetic_fraud_label"] = frame.transaction_id.map(label_map)
    return frame


def _query_params(date_from, date_to, transaction_type, merchant_category, payment_method, status, location, customer_id):
    return _params(date_from, date_to, transaction_type, merchant_category, payment_method, status, location, customer_id)


@router.get("/investigations")
def investigations(page: int = Query(1, ge=1), page_size: int = Query(100, ge=1, le=500),
                   anomaly_status: str = Query("all", pattern="^(all|flagged|normal)$"), transaction_id: str | None = None,
                   amount_min: float | None = Query(None, ge=0), amount_max: float | None = Query(None, ge=0),
                   date_from: date | None = None, date_to: date | None = None,
                   transaction_type: str | None = None, merchant_category: str | None = None, payment_method: str | None = None,
                   status: str | None = None, location: str | None = None, customer_id: str | None = None,
                   sort_by: str = Query("score", pattern="^(score|date|amount)$"), order: str = Query("asc", pattern="^(asc|desc)$")):
    if amount_min is not None and amount_max is not None and amount_min > amount_max:
        raise HTTPException(status_code=422, detail="amount_min must be less than or equal to amount_max")
    params = _query_params(date_from, date_to, transaction_type, merchant_category, payment_method, status, location, customer_id)
    frame = _attach_synthetic_labels(_filtered(params, anomaly_status, transaction_id, amount_min, amount_max))
    column = {"score": "isolation_score", "date": "transaction_date", "amount": "amount"}[sort_by]
    if column in frame:
        frame = frame.sort_values(column, ascending=order == "asc", na_position="last")
    total = len(frame)
    start = (page - 1) * page_size
    return {"items": _serialize(frame.iloc[start:start + page_size]), "total": total, "page": page,
            "page_size": page_size, "pages": (total + page_size - 1) // page_size,
            "score_note": "Isolation Forest decision score; lower scores are more anomalous. This is not a fraud probability."}


@router.get("/investigations/export")
def export_investigations(anomaly_status: str = Query("all", pattern="^(all|flagged|normal)$"), transaction_id: str | None = None,
                          amount_min: float | None = Query(None, ge=0), amount_max: float | None = Query(None, ge=0),
                          date_from: date | None = None, date_to: date | None = None,
                          transaction_type: str | None = None, merchant_category: str | None = None, payment_method: str | None = None,
                          status: str | None = None, location: str | None = None, customer_id: str | None = None,
                          sort_by: str = Query("score", pattern="^(score|date|amount)$"), order: str = Query("asc", pattern="^(asc|desc)$")):
    if amount_min is not None and amount_max is not None and amount_min > amount_max:
        raise HTTPException(status_code=422, detail="amount_min must be less than or equal to amount_max")
    params = _query_params(date_from, date_to, transaction_type, merchant_category, payment_method, status, location, customer_id)
    frame = _filtered(params, anomaly_status, transaction_id, amount_min, amount_max)
    if frame.empty:
        raise HTTPException(status_code=404, detail="No transactions match the selected filters")
    if len(frame) > 100_000:
        raise HTTPException(status_code=413, detail="Export exceeds the 100,000-row safety limit; narrow the filters")
    frame = _attach_synthetic_labels(frame)
    column = {"score": "isolation_score", "date": "transaction_date", "amount": "amount"}[sort_by]
    if column in frame:
        frame = frame.sort_values(column, ascending=order == "asc", na_position="last")
    csv = StringIO()
    frame.to_csv(csv, index=False)
    csv.seek(0)
    return Response(content=csv.getvalue(), media_type="text/csv", headers={"Content-Disposition": "attachment; filename=finsight_investigations.csv"})
