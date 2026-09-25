from fastapi import APIRouter, Query
from typing import Optional
from api.data_service import data_service

router = APIRouter(prefix="/api/anomalies", tags=["anomalies"])

@router.get("/")
def get_anomalies(
    limit: int = Query(100, ge=1, le=1000),
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    transaction_type: Optional[str] = None,
    merchant_category: Optional[str] = None,
    payment_method: Optional[str] = None,
    status: Optional[str] = None,
    location: Optional[str] = None,
    customer_id: Optional[str] = None,
):
    df = data_service.get_transactions()
    df = data_service.apply_filters(
        df,
        date_from=date_from,
        date_to=date_to,
        transaction_type=transaction_type,
        merchant_category=merchant_category,
        payment_method=payment_method,
        status=status,
        location=location,
        customer_id=customer_id,
    )
    if df.empty or 'ml_anomaly' not in df.columns:
        return []
    anomalies = df[df['ml_anomaly'] == 1].copy()
    if 'isolation_score' in anomalies.columns:
        anomalies = anomalies.sort_values(by="isolation_score", ascending=True)
    if 'transaction_date' in anomalies.columns:
        anomalies['transaction_date'] = anomalies['transaction_date'].dt.strftime('%Y-%m-%dT%H:%M:%S')
    return anomalies.head(limit).to_dict(orient="records")

@router.get("/summary")
def get_anomalies_summary(
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    transaction_type: Optional[str] = None,
    merchant_category: Optional[str] = None,
    payment_method: Optional[str] = None,
    status: Optional[str] = None,
    location: Optional[str] = None,
    customer_id: Optional[str] = None,
):
    df = data_service.get_transactions()
    df = data_service.apply_filters(
        df,
        date_from=date_from,
        date_to=date_to,
        transaction_type=transaction_type,
        merchant_category=merchant_category,
        payment_method=payment_method,
        status=status,
        location=location,
        customer_id=customer_id,
    )
    if df.empty:
        return {}
    total_transactions = len(df)
    iqr_count = int(df['iqr_anomaly'].sum()) if 'iqr_anomaly' in df.columns else 0
    ml_count = int(df['ml_anomaly'].sum()) if 'ml_anomaly' in df.columns else 0
    overlap = (
        int(((df['iqr_anomaly'] == 1) & (df['ml_anomaly'] == 1)).sum())
        if 'iqr_anomaly' in df.columns and 'ml_anomaly' in df.columns
        else 0
    )
    anomaly_percentage = (ml_count / total_transactions) * 100 if total_transactions > 0 else 0
    return {
        "iqr_anomaly_count": iqr_count,
        "ml_anomaly_count": ml_count,
        "overlap_count": overlap,
        "anomaly_percentage": anomaly_percentage,
        "terminology_note": "These are potential anomalies, statistical outliers, or model-flagged transactions. They are NOT confirmed fraud.",
    }
