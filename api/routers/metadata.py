from fastapi import APIRouter
from api.data_service import data_service

router = APIRouter(prefix="/api", tags=["metadata"])

@router.get("/categories")
def get_categories():
    df = data_service.get_transactions()
    if df.empty or 'merchant_category' not in df.columns:
        return []
    return sorted(df['merchant_category'].dropna().unique().tolist())

@router.get("/payment-methods")
def get_payment_methods():
    df = data_service.get_transactions()
    if df.empty or 'payment_method' not in df.columns:
        return []
    return sorted(df['payment_method'].dropna().unique().tolist())

@router.get("/locations")
def get_locations():
    df = data_service.get_transactions()
    if df.empty or 'location' not in df.columns:
        return []
    return sorted(df['location'].dropna().unique().tolist())

@router.get("/transaction-types")
def get_transaction_types():
    df = data_service.get_transactions()
    if df.empty or 'transaction_type' not in df.columns:
        return []
    return sorted(df['transaction_type'].dropna().unique().tolist())

@router.get("/statuses")
def get_statuses():
    df = data_service.get_transactions()
    if df.empty or 'status' not in df.columns:
        return []
    return sorted(df['status'].dropna().unique().tolist())

@router.get("/date-range")
def get_date_range():
    min_date, max_date = data_service.get_transaction_date_range()
    if min_date is None or max_date is None:
        return {}
    return {
        "min_date": min_date.date().isoformat(),
        "max_date": max_date.date().isoformat(),
    }
