from fastapi import APIRouter
from typing import Optional
from api.data_service import data_service
import pandas as pd

router = APIRouter(prefix="/api", tags=["customers"])

@router.get("/customers/top")
def get_top_customers(
    limit: int = 10,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    transaction_type: Optional[str] = None,
    merchant_category: Optional[str] = None,
    payment_method: Optional[str] = None,
    status: Optional[str] = None,
    location: Optional[str] = None,
    customer_id: Optional[str] = None,
):
    df_tx = data_service.apply_filters(
        data_service.get_transactions(), date_from, date_to, transaction_type,
        merchant_category, payment_method, status, location, customer_id
    )
    if df_tx.empty:
        return []
    df_tx = data_service.merge_segments(df_tx)
    top_customers = df_tx.groupby(['customer_id', 'segment_name']).agg(
        total_spend=('amount', 'sum'),
        transaction_count=('transaction_id', 'count'),
        anomaly_rate=('ml_anomaly', 'mean'),
    ).reset_index()
    return top_customers.sort_values(by="total_spend", ascending=False).head(limit).to_dict(orient="records")

@router.get("/segments")
def get_segments(
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    transaction_type: Optional[str] = None,
    merchant_category: Optional[str] = None,
    payment_method: Optional[str] = None,
    status: Optional[str] = None,
    location: Optional[str] = None,
    customer_id: Optional[str] = None,
):
    df_segments = data_service.get_segments()
    if df_segments.empty:
        return []
    # Apply filters on transactions and recompute segments if any filter is provided
    if any([date_from, date_to, transaction_type, merchant_category, payment_method, status, location, customer_id]):
        df_tx = data_service.get_transactions()
        df_tx = data_service.apply_filters(
            df_tx,
            date_from=date_from,
            date_to=date_to,
            transaction_type=transaction_type,
            merchant_category=merchant_category,
            payment_method=payment_method,
            status=status,
            location=location,
            customer_id=customer_id,
        )
        if df_tx.empty:
            return []
        # Merge anomalies and segments information
        df_tx = data_service.merge_anomalies(df_tx)
        df_tx = data_service.merge_segments(df_tx)
        # Recompute segment aggregates
        df_segments = df_tx.groupby('segment_name').agg(
            customer_id=('customer_id', 'first'),
            total_spend=('amount', 'sum'),
            transaction_count=('transaction_id', 'count'),
            anomaly_rate=('ml_anomaly', 'mean')
        ).reset_index()
    return df_segments.to_dict(orient="records")

@router.get("/segments/summary")
def get_segments_summary(
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    transaction_type: Optional[str] = None,
    merchant_category: Optional[str] = None,
    payment_method: Optional[str] = None,
    status: Optional[str] = None,
    location: Optional[str] = None,
    customer_id: Optional[str] = None,
):
    # Compute summary based on filtered transactions
    df_tx = data_service.get_transactions()
    df_tx = data_service.apply_filters(
        df_tx,
        date_from=date_from,
        date_to=date_to,
        transaction_type=transaction_type,
        merchant_category=merchant_category,
        payment_method=payment_method,
        status=status,
        location=location,
        customer_id=customer_id,
    )
    if df_tx.empty:
        return []
    df_tx = data_service.merge_anomalies(df_tx)
    df_tx = data_service.merge_segments(df_tx)
    if 'segment_name' not in df_tx.columns:
        return []
    customer_metrics = df_tx.groupby(['segment_name', 'customer_id']).agg(
        total_spend=('amount', 'sum'),
        transaction_count=('transaction_id', 'count'),
        anomaly_rate=('ml_anomaly', 'mean'),
    ).reset_index()
    summary = customer_metrics.groupby('segment_name').agg(
        customer_count=('customer_id', 'nunique'),
        total_spend=('total_spend', 'sum'),
        average_transaction_count=('transaction_count', 'mean'),
        average_anomaly_rate=('anomaly_rate', 'mean'),
    ).reset_index()
    total_customers = summary['customer_count'].sum()
    summary['percentage_of_customers'] = (summary['customer_count'] / total_customers) * 100
    return summary.where(pd.notna(summary), None).to_dict(orient="records")
