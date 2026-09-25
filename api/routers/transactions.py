from fastapi import APIRouter, Query, HTTPException
from typing import Optional
from api.data_service import data_service
import pandas as pd

router = APIRouter(prefix="/api", tags=["transactions"])

def filter_transactions(df, limit, date_from, date_to, transaction_type, merchant_category, payment_method, status, location, customer_id):
    # Centralized filtering via DataService.apply_filters
    return data_service.apply_filters(
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

@router.get("/transactions")
def get_transactions(
    limit: int = Query(100, ge=1, le=1000),
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    transaction_type: Optional[str] = None,
    merchant_category: Optional[str] = None,
    payment_method: Optional[str] = None,
    status: Optional[str] = None,
    location: Optional[str] = None,
    customer_id: Optional[str] = None
):
    df = data_service.get_transactions()
    filtered = filter_transactions(df, limit, date_from, date_to, transaction_type, merchant_category, payment_method, status, location, customer_id)
    
    if filtered.empty:
        return []
        
    # convert datetime to string
    if 'transaction_date' in filtered.columns:
        filtered['transaction_date'] = filtered['transaction_date'].dt.strftime('%Y-%m-%dT%H:%M:%S')
        
    return filtered.head(limit).to_dict(orient="records")

@router.get("/transactions/recent")
def get_recent_transactions(limit: int = Query(10, ge=1, le=100)):
    df = data_service.get_transactions()
    if df.empty:
        return []
    
    sorted_df = df.sort_values(by="transaction_date", ascending=False).head(limit)
    if 'transaction_date' in sorted_df.columns:
        sorted_df['transaction_date'] = sorted_df['transaction_date'].dt.strftime('%Y-%m-%dT%H:%M:%S')
    return sorted_df.to_dict(orient="records")

@router.get("/trends/monthly")
def get_monthly_trends(
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
    if df.empty or 'transaction_date' not in df.columns:
        return []
    df['month'] = df['transaction_date'].dt.to_period('M').astype(str)
    trends = df.groupby('month').agg(
        transaction_count=('transaction_id', 'count'),
        transaction_amount=('amount', 'sum')
    ).reset_index()
    return trends.to_dict(orient="records")
