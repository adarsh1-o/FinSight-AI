import pandas as pd
from pathlib import Path

class DataService:
    def __init__(self):
        # Resolve the project root (FinSight-AI directory) relative to this file
        base_dir = Path(__file__).resolve().parents[1]
        processed_dir = base_dir / 'data' / 'processed'

        # Paths to processed files
        self.transactions_path = processed_dir / 'transactions_with_anomalies.csv'
        # Fallback to cleaned if anomalies file does not exist
        if not self.transactions_path.is_file():
            self.transactions_path = processed_dir / 'transactions_cleaned.csv'

        self.segments_path = processed_dir / 'customer_segments.csv'

        # Load data into memory
        self._load_data()

    def _load_data(self):
        try:
            self.df_transactions = pd.read_csv(self.transactions_path)
            if 'transaction_date' in self.df_transactions.columns:
                self.df_transactions['transaction_date'] = pd.to_datetime(self.df_transactions['transaction_date'])
        except Exception as e:
            print(f"Error loading transactions: {e}")
            self.df_transactions = pd.DataFrame()

        try:
            self.df_segments = pd.read_csv(self.segments_path)
        except Exception as e:
            print(f"Error loading segments: {e}")
            self.df_segments = pd.DataFrame()

    def get_transactions(self) -> pd.DataFrame:
        return self.df_transactions

    def get_segments(self) -> pd.DataFrame:
        return self.df_segments

    def apply_filters(
        self,
        df: pd.DataFrame,
        date_from: str | None = None,
        date_to: str | None = None,
        transaction_type: str | None = None,
        merchant_category: str | None = None,
        payment_method: str | None = None,
        status: str | None = None,
        location: str | None = None,
        customer_id: str | None = None,
    ) -> pd.DataFrame:
        """Return a filtered view of *df* according to optional parameters.
        Empty strings or None are ignored. The function never mutates the original
        DataFrame.
        """
        if df.empty:
            return df
        filtered = df.copy()
        if date_from:
            filtered = filtered[filtered['transaction_date'] >= pd.to_datetime(date_from)]
        if date_to:
            end_date = pd.to_datetime(date_to) + pd.Timedelta(days=1)
            filtered = filtered[filtered['transaction_date'] < end_date]
        if transaction_type:
            filtered = filtered[filtered['transaction_type'] == transaction_type]
        if merchant_category:
            filtered = filtered[filtered['merchant_category'] == merchant_category]
        if payment_method:
            filtered = filtered[filtered['payment_method'] == payment_method]
        if status:
            filtered = filtered[filtered['status'] == status]
        if location:
            filtered = filtered[filtered['location'] == location]
        if customer_id:
            filtered = filtered[filtered['customer_id'] == customer_id]
        return filtered

    def get_transaction_date_range(self) -> tuple[pd.Timestamp | None, pd.Timestamp | None]:
        """Return the available transaction dates for dashboard defaults."""
        if self.df_transactions.empty or 'transaction_date' not in self.df_transactions.columns:
            return None, None
        return self.df_transactions['transaction_date'].min(), self.df_transactions['transaction_date'].max()


    # Helper merge methods for compatibility
    def merge_anomalies(self, df: pd.DataFrame) -> pd.DataFrame:
        """Return dataframe unchanged; anomaly columns already present."""
        return df

    def merge_segments(self, df: pd.DataFrame) -> pd.DataFrame:
        """Left‑join segment information onto transaction dataframe."""
        if self.df_segments.empty:
            return df
        seg_cols = self.df_segments[['customer_id', 'segment_name']]
        return df.merge(seg_cols, on='customer_id', how='left')

# Singleton instance for the application
data_service = DataService()
