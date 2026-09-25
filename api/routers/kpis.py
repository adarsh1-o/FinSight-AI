from fastapi import APIRouter, Query
from api.data_service import data_service

router = APIRouter(prefix="/api/kpis", tags=["kpis"])

@router.get("/")
def get_kpis(
    date_from: str | None = None,
    date_to: str | None = None,
    transaction_type: str | None = None,
    merchant_category: str | None = None,
    payment_method: str | None = None,
    status: str | None = None,
    location: str | None = None,
    customer_id: str | None = None,
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
    total_amount = df['amount'].sum()
    avg_amount = df['amount'].mean()
    median_amount = df['amount'].median()
    unique_customers = df['customer_id'].nunique() if 'customer_id' in df.columns else 0
    unique_accounts = df['account_id'].nunique() if 'account_id' in df.columns else 0
    potential_anomalies = int(df['ml_anomaly'].sum()) if 'ml_anomaly' in df.columns else 0
    anomaly_percentage = (potential_anomalies / total_transactions) * 100 if total_transactions > 0 else 0
    return {
        "total_transactions": total_transactions,
        "total_transaction_amount": total_amount,
        "average_transaction_amount": avg_amount,
        "median_transaction_amount": median_amount,
        "unique_customers": unique_customers,
        "unique_accounts": unique_accounts,
        "potential_anomalies": potential_anomalies,
        "anomaly_percentage": anomaly_percentage,
    }
