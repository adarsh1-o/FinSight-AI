import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import random
from typing import Tuple

# ==========================================
# CONFIGURATION
# ==========================================
NUM_CUSTOMERS = 10000
NUM_TRANSACTIONS = 100000
START_DATE = datetime(2023, 1, 1)
END_DATE = datetime(2024, 3, 1)
RANDOM_SEED = 42

# Initialize random seeds for exact reproducibility
np.random.seed(RANDOM_SEED)
random.seed(RANDOM_SEED)

def format_datetime(dt: datetime) -> str:
    """Format datetime to standard string."""
    return dt.strftime("%Y-%m-%d %H:%M:%S")

def random_dates(start: datetime, end: datetime, n: int) -> pd.Series:
    """Generate n random datetimes between start and end."""
    start_u = start.timestamp()
    end_u = end.timestamp()
    timestamps = np.random.uniform(start_u, end_u, n)
    return pd.Series([datetime.fromtimestamp(ts) for ts in timestamps])

def generate_customers(num_customers: int) -> pd.DataFrame:
    """Generates the customers dataset."""
    print(f"Generating {num_customers} customers...")
    customer_ids = [f"c-{i:05d}" for i in range(1, num_customers + 1)]
    
    first_names = ["James", "Mary", "John", "Patricia", "Robert", "Jennifer", "Michael", "Linda", "William", "Elizabeth"]
    last_names = ["Smith", "Johnson", "Williams", "Brown", "Jones", "Garcia", "Miller", "Davis", "Rodriguez", "Martinez"]
    
    fnames = np.random.choice(first_names, size=num_customers)
    lnames = np.random.choice(last_names, size=num_customers)
    emails = [f"{f.lower()}.{l.lower()}@example.com" for f, l in zip(fnames, lnames)]
    
    # Age distributed normally around 38, converted back to date of birth
    ages = np.random.normal(loc=38, scale=12, size=num_customers).clip(18, 90)
    dobs = [START_DATE - timedelta(days=int(age * 365.25)) for age in ages]
    
    genders = np.random.choice(["Male", "Female", "Non-binary", "Other"], size=num_customers, p=[0.48, 0.48, 0.03, 0.01])
    countries = np.random.choice(["USA", "UK", "Canada", "Australia"], size=num_customers, p=[0.7, 0.1, 0.1, 0.1])
    cities = np.random.choice(["New York", "London", "Toronto", "Sydney", "Miami", "Austin", "Seattle"], size=num_customers)
    occupations = np.random.choice(["Engineer", "Teacher", "Doctor", "Artist", "Manager", "Student", "Retired", "Sales"], size=num_customers)
    
    # Log-normal distribution for income
    incomes = np.random.lognormal(mean=11.0, sigma=0.6, size=num_customers).round(2)
    account_types = np.random.choice(["Basic", "Premium", "VIP"], size=num_customers, p=[0.6, 0.3, 0.1])
    onboarding_dates = random_dates(START_DATE, END_DATE - timedelta(days=30), num_customers)
    
    df = pd.DataFrame({
        "customer_id": customer_ids,
        "first_name": fnames,
        "last_name": lnames,
        "email": emails,
        "date_of_birth": [format_datetime(d) for d in dobs],
        "gender": genders,
        "country": countries,
        "city": cities,
        "occupation": occupations,
        "annual_income": incomes,
        "account_type": account_types,
        "onboarding_date": onboarding_dates.apply(format_datetime)
    })
    
    return df

def generate_accounts(customers_df: pd.DataFrame) -> pd.DataFrame:
    """Generates the accounts dataset linked to customers."""
    print("Generating accounts...")
    accounts_list = []
    
    account_counter = 1
    for _, customer in customers_df.iterrows():
        # 1 to 3 accounts per customer
        num_accounts = np.random.choice([1, 2, 3], p=[0.7, 0.2, 0.1])
        
        onboarding_dt = datetime.strptime(customer["onboarding_date"], "%Y-%m-%d %H:%M:%S")
        
        for _ in range(num_accounts):
            acc_type = np.random.choice(["Checking", "Savings", "Credit"])
            balance = np.random.uniform(0, 50000) if acc_type != "Credit" else np.random.uniform(-5000, 0)
            
            opened_dt = onboarding_dt + timedelta(days=np.random.randint(0, 10))
            
            accounts_list.append({
                "account_id": f"a-{account_counter:05d}",
                "customer_id": customer["customer_id"],
                "account_type": acc_type,
                "opened_date": format_datetime(opened_dt),
                "balance": round(balance, 2),
                "currency": "USD",
                "status": np.random.choice(["Active", "Suspended", "Closed"], p=[0.9, 0.05, 0.05])
            })
            account_counter += 1
            
    return pd.DataFrame(accounts_list)

def generate_transactions(accounts_df: pd.DataFrame, num_transactions: int) -> pd.DataFrame:
    """Generates transactions linked to accounts and customers."""
    print(f"Generating {num_transactions} transactions...")
    
    # Sample accounts safely for reproducibility
    sampled_accounts = accounts_df.sample(n=num_transactions, replace=True, random_state=RANDOM_SEED).reset_index(drop=True)
    
    transaction_ids = [f"t-{i:06d}" for i in range(1, num_transactions + 1)]
    transaction_dates = random_dates(START_DATE, END_DATE, num_transactions)
    
    merchants = ["Grocery", "Amazon", "Uber", "Gas", "Restaurant", "Airlines", "TechStore"]
    merchant_categories = np.random.choice(merchants, size=num_transactions)
    
    amounts = np.random.lognormal(mean=3.5, sigma=1.2, size=num_transactions)
    transaction_types = np.random.choice(["Purchase", "Transfer", "Withdrawal"], size=num_transactions, p=[0.7, 0.2, 0.1])
    payment_methods = np.random.choice(["Card", "ACH", "Wire", "Wallet"], size=num_transactions, p=[0.6, 0.2, 0.05, 0.15])
    
    df = pd.DataFrame({
        "transaction_id": transaction_ids,
        "customer_id": sampled_accounts["customer_id"],
        "account_id": sampled_accounts["account_id"],
        "transaction_date": transaction_dates,
        "amount": amounts.round(2),
        "transaction_type": transaction_types,
        "merchant_category": merchant_categories,
        "payment_method": payment_methods,
        "location": np.random.choice(["Local", "Foreign"], size=num_transactions, p=[0.9, 0.1]),
        "status": np.random.choice(["Completed", "Failed", "Pending"], size=num_transactions, p=[0.9, 0.08, 0.02])
    })
    
    return df

def generate_fraud_labels(transactions_df: pd.DataFrame) -> pd.DataFrame:
    """Generates fraud labels corresponding to transactions based on risk patterns."""
    print("Generating fraud labels...")
    
    # Extract hour for risk calculation
    hour = transactions_df["transaction_date"].dt.hour
    
    risk_score = np.zeros(len(transactions_df))
    risk_score += np.where(transactions_df["amount"] > 1500, 2, 0)
    risk_score += np.where(transactions_df["location"] == "Foreign", 3, 0)
    risk_score += np.where((hour >= 0) & (hour <= 5), 2, 0)
    risk_score += np.where((transactions_df["merchant_category"] == "TechStore") & (transactions_df["amount"] > 500), 2, 0)
    risk_score += np.where(transactions_df["status"] == "Failed", 1, 0)
    
    # Avoid single obvious thresholds by using a sigmoid mapping
    prob_fraud = 1 / (1 + np.exp(-(risk_score - 5.5))) 
    is_fraud = np.random.binomial(1, prob_fraud)
    
    fraud_mask = is_fraud.astype(bool)
    
    # Provide resolution dates only for labeled rows (or keep the same size as transactions)
    # The requirement is that fraud labels exist for transactions. Let's create it for all, or just the fraudulent?
    # Usually labels are provided for a subset or all reviewed transactions. We will create a label for all for simplicity.
    resolution_dates = transactions_df["transaction_date"] + pd.to_timedelta(np.random.randint(1, 10, size=len(transactions_df)), unit='d')
    
    fraud_df = pd.DataFrame({
        "transaction_id": transactions_df["transaction_id"],
        "is_fraud": fraud_mask,
        "resolution_date": resolution_dates.apply(format_datetime)
    })
    
    # Convert transaction_date back to string in transactions_df
    transactions_df["transaction_date"] = transactions_df["transaction_date"].apply(format_datetime)
    
    return fraud_df

def generate_customer_activity(customers_df: pd.DataFrame) -> pd.DataFrame:
    """Generates aggregated customer activity with overlapping realistic churn signals."""
    print("Generating customer activity...")
    num_customers = len(customers_df)
    
    # Hidden propensity score (0 to 1), where higher means higher risk of churn/inactivity
    propensity = np.random.beta(a=2, b=5, size=num_customers)
    
    # Generate overlapping, realistic distributions instead of strict separations
    # Higher propensity = lower login frequency, higher days since login, higher support tickets
    
    login_freq_base = np.random.poisson(lam=15, size=num_customers)
    login_frequency = np.maximum(0, login_freq_base - np.random.poisson(lam=propensity * 12)).astype(int)
    
    avg_session_time = np.random.normal(loc=300 - (propensity * 150), scale=60, size=num_customers).clip(30, 900)
    
    days_since_last_login = np.random.poisson(lam=2 + (propensity * 45), size=num_customers)
    
    support_tickets = np.random.poisson(lam=0.5 + (propensity * 3.5), size=num_customers)
    failed_transactions = np.random.poisson(lam=0.2 + (propensity * 2), size=num_customers)
    
    transaction_frequency = np.random.poisson(lam=10, size=num_customers)
    transaction_frequency = np.maximum(0, transaction_frequency - np.random.poisson(lam=propensity * 8)).astype(int)
    
    # Calculate last_login date based on days_since_last_login
    last_logins = [END_DATE - timedelta(days=int(d)) for d in days_since_last_login]

    activity_df = pd.DataFrame({
        "customer_id": customers_df["customer_id"],
        "login_frequency": login_frequency,
        "avg_session_time": avg_session_time.round(1),
        "last_login": [format_datetime(d) for d in last_logins],
        "days_since_last_login": days_since_last_login,
        "support_tickets": support_tickets,
        "failed_transactions": failed_transactions,
        "transaction_frequency": transaction_frequency
    })
    
    return activity_df

def introduce_data_quality_issues(
    customers: pd.DataFrame, 
    accounts: pd.DataFrame, 
    transactions: pd.DataFrame, 
    activity: pd.DataFrame
) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Introduces detectable data quality issues without breaking relational integrity."""
    print("Introducing controlled data quality issues...")
    
    # 1. Missing values (DOB and city in customers)
    mask_dob = np.random.rand(len(customers)) < 0.05
    customers.loc[mask_dob, "date_of_birth"] = np.nan
    
    mask_city = np.random.rand(len(customers)) < 0.02
    customers.loc[mask_city, "city"] = np.nan
    
    # 2. Inconsistent categorical formatting (Lowercase some cities)
    idx_format = np.random.choice(customers.index, size=int(len(customers)*0.03), replace=False)
    # Only apply lower() to strings, avoiding NaNs
    customers.loc[idx_format, "city"] = customers.loc[idx_format, "city"].apply(
        lambda x: x.lower() if isinstance(x, str) else x
    )
    
    # 3. Duplicate transaction records (Copy 50 rows)
    if len(transactions) > 50:
        duplicates = transactions.sample(n=50, random_state=RANDOM_SEED)
        transactions = pd.concat([transactions, duplicates], ignore_index=True)
        
    # 4. A small number of invalid values (Negative login frequency)
    idx_invalid = np.random.choice(activity.index, size=20, replace=False)
    activity.loc[idx_invalid, "login_frequency"] = -1
    
    return customers, accounts, transactions, activity

def main():
    print("--- Starting FinSight AI Synthetic Data Generation ---")
    
    customers = generate_customers(NUM_CUSTOMERS)
    accounts = generate_accounts(customers)
    transactions = generate_transactions(accounts, NUM_TRANSACTIONS)
    fraud = generate_fraud_labels(transactions)
    activity = generate_customer_activity(customers)
    
    customers, accounts, transactions, activity = introduce_data_quality_issues(
        customers, accounts, transactions, activity
    )
    
    print("Saving datasets to data/raw/ ...")
    customers.to_csv("data/raw/customers.csv", index=False)
    accounts.to_csv("data/raw/accounts.csv", index=False)
    transactions.to_csv("data/raw/transactions.csv", index=False)
    activity.to_csv("data/raw/customer_activity.csv", index=False)
    fraud.to_csv("data/raw/fraud_labels.csv", index=False)
    
    print("\n================ GENERATION SUMMARY ================")
    print(f"Date Range:              {START_DATE.strftime('%Y-%m-%d')} to {END_DATE.strftime('%Y-%m-%d')} (UTC)")
    print(f"Customers Generated:     {len(customers)} unique users")
    print(f"Accounts Generated:      {len(accounts)} total accounts")
    print(f"Transactions Generated:  {len(transactions)} (includes duplicates)")
    print(f"Activity Records:        {len(activity)} total records")
    print(f"Fraud Labels:            {fraud['is_fraud'].sum()} fraudulent cases")
    print("====================================================")
    print("Done! Data is ready for cleaning in the next phase.")

if __name__ == "__main__":
    main()
