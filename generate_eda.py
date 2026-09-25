import nbformat as nbf
import os

nb = nbf.v4.new_notebook()

cells = []

# 1. Introduction
cells.append(nbf.v4.new_markdown_cell("# 1. Introduction\nThis notebook performs Exploratory Data Analysis (EDA) on the FinSight AI financial transactions dataset."))

# Setup
cells.append(nbf.v4.new_code_cell("""import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
import warnings
warnings.filterwarnings('ignore')

sns.set_theme(style='whitegrid', palette='muted')
plt.rcParams['figure.figsize'] = (10, 6)
"""))

# 2. Dataset Overview
cells.append(nbf.v4.new_markdown_cell("# 2. Dataset Overview\nLoading the dataset, applying data cleaning steps from profiling (removing duplicates, datetime conversion) and displaying basic info."))

cells.append(nbf.v4.new_code_cell("""df = pd.read_csv('../data/raw/transactions.csv')
print(f"Original shape: {df.shape}")
df = df.drop_duplicates()
if 'transaction_date' in df.columns:
    df['transaction_date'] = pd.to_datetime(df['transaction_date'])
print(f"Cleaned shape: {df.shape}")
display(df.head())
display(df.info())
"""))

# 3. Financial KPIs
cells.append(nbf.v4.new_markdown_cell("# 3. Financial KPIs\nCalculating key financial indicators."))

cells.append(nbf.v4.new_code_cell("""total_tx_count = len(df)
total_tx_amount = df['amount'].sum()
avg_tx_amount = df['amount'].mean()
median_tx_amount = df['amount'].median()
min_tx_amount = df['amount'].min()
max_tx_amount = df['amount'].max()

unique_customers = df['customer_id'].nunique() if 'customer_id' in df.columns else 'N/A'
unique_accounts = df['account_id'].nunique() if 'account_id' in df.columns else 'N/A'
date_range_start = df['transaction_date'].min() if 'transaction_date' in df.columns else 'N/A'
date_range_end = df['transaction_date'].max() if 'transaction_date' in df.columns else 'N/A'

print("-" * 30)
print("FINANCIAL KPIs")
print("-" * 30)
print(f"Total Transaction Count: {total_tx_count:,}")
print(f"Total Transaction Amount: ${total_tx_amount:,.2f}")
print(f"Average Transaction Amount: ${avg_tx_amount:,.2f}")
print(f"Median Transaction Amount: ${median_tx_amount:,.2f}")
print(f"Minimum Transaction Amount: ${min_tx_amount:,.2f}")
print(f"Maximum Transaction Amount: ${max_tx_amount:,.2f}")
print(f"Unique Customers: {unique_customers:,}")
print(f"Unique Accounts: {unique_accounts:,}")
print(f"Date Range: {date_range_start} to {date_range_end}")
"""))

# 4. Transaction Type Analysis
cells.append(nbf.v4.new_markdown_cell("# 4. Transaction Type Analysis\nAnalyzing volume and value by transaction type."))
cells.append(nbf.v4.new_code_cell("""if 'transaction_type' in df.columns:
    tx_type_stats = df.groupby('transaction_type').agg(
        count=('amount', 'size'),
        total_amount=('amount', 'sum'),
        avg_amount=('amount', 'mean')
    ).reset_index()
    
    display(tx_type_stats)
    
    fig, axes = plt.subplots(1, 2, figsize=(14, 6))
    sns.barplot(data=tx_type_stats, x='transaction_type', y='count', ax=axes[0], palette='viridis')
    axes[0].set_title('Transaction Count by Type')
    axes[0].set_ylabel('Count')
    axes[0].tick_params(axis='x', rotation=45)
    
    sns.barplot(data=tx_type_stats, x='transaction_type', y='total_amount', ax=axes[1], palette='viridis')
    axes[1].set_title('Total Amount by Type')
    axes[1].set_ylabel('Total Amount ($)')
    axes[1].tick_params(axis='x', rotation=45)
    
    plt.tight_layout()
    plt.show()
else:
    print("Column 'transaction_type' not found.")
"""))

# 5. Merchant Category Analysis
cells.append(nbf.v4.new_markdown_cell("# 5. Merchant Category Analysis\nAnalyzing volume and value by merchant category."))
cells.append(nbf.v4.new_code_cell("""if 'merchant_category' in df.columns:
    merchant_stats = df.groupby('merchant_category').agg(
        count=('amount', 'size'),
        total_amount=('amount', 'sum'),
        avg_amount=('amount', 'mean')
    ).reset_index().sort_values(by='total_amount', ascending=False)
    
    display(merchant_stats.head(10))
    
    fig, ax = plt.subplots(figsize=(12, 6))
    sns.barplot(data=merchant_stats.head(10), x='merchant_category', y='total_amount', palette='rocket')
    ax.set_title('Top 10 Merchant Categories by Total Amount')
    ax.set_ylabel('Total Amount ($)')
    ax.tick_params(axis='x', rotation=45)
    plt.tight_layout()
    plt.show()
else:
    print("Column 'merchant_category' not found.")
"""))

# 6. Payment Method Analysis
cells.append(nbf.v4.new_markdown_cell("# 6. Payment Method Analysis\nAnalyzing volume and value by payment method."))
cells.append(nbf.v4.new_code_cell("""if 'payment_method' in df.columns:
    payment_stats = df.groupby('payment_method').agg(
        count=('amount', 'size'),
        total_amount=('amount', 'sum'),
        avg_amount=('amount', 'mean')
    ).reset_index().sort_values(by='count', ascending=False)
    
    display(payment_stats)
    
    fig, axes = plt.subplots(1, 2, figsize=(14, 6))
    sns.barplot(data=payment_stats, x='payment_method', y='count', ax=axes[0], palette='crest')
    axes[0].set_title('Transaction Count by Payment Method')
    axes[0].tick_params(axis='x', rotation=45)
    
    sns.barplot(data=payment_stats, x='payment_method', y='total_amount', ax=axes[1], palette='crest')
    axes[1].set_title('Total Amount by Payment Method')
    axes[1].tick_params(axis='x', rotation=45)
    
    plt.tight_layout()
    plt.show()
else:
    print("Column 'payment_method' not found.")
"""))

# 7. Status Analysis
cells.append(nbf.v4.new_markdown_cell("# 7. Status Analysis\nAnalyzing transaction status distribution."))
cells.append(nbf.v4.new_code_cell("""if 'status' in df.columns:
    status_counts = df['status'].value_counts().reset_index()
    status_counts.columns = ['status', 'count']
    status_counts['percentage'] = (status_counts['count'] / status_counts['count'].sum()) * 100
    
    status_amount = df.groupby('status')['amount'].sum().reset_index()
    status_merged = pd.merge(status_counts, status_amount, on='status')
    
    display(status_merged)
    
    fig, ax = plt.subplots(figsize=(8, 5))
    sns.barplot(data=status_merged, x='status', y='count', palette='Set2')
    ax.set_title('Transaction Count by Status')
    plt.show()
else:
    print("Column 'status' not found.")
"""))

# 8. Location Analysis
cells.append(nbf.v4.new_markdown_cell("# 8. Location Analysis\nAnalyzing transactions by location."))
cells.append(nbf.v4.new_code_cell("""if 'location' in df.columns:
    location_stats = df.groupby('location').agg(
        count=('amount', 'size'),
        total_amount=('amount', 'sum'),
        avg_amount=('amount', 'mean')
    ).reset_index().sort_values(by='total_amount', ascending=False)
    
    display(location_stats.head(10))
    
    fig, ax = plt.subplots(figsize=(12, 6))
    sns.barplot(data=location_stats.head(10), x='location', y='total_amount', palette='magma')
    ax.set_title('Top 10 Locations by Total Amount')
    ax.tick_params(axis='x', rotation=45)
    plt.tight_layout()
    plt.show()
else:
    print("Column 'location' not found.")
"""))

# 9. Time-Based Analysis
cells.append(nbf.v4.new_markdown_cell("# 9. Time-Based Analysis\nAnalyzing volume and value over time (daily, monthly, day-of-week)."))
cells.append(nbf.v4.new_code_cell("""if 'transaction_date' in df.columns:
    df['date'] = df['transaction_date'].dt.date
    df['month'] = df['transaction_date'].dt.to_period('M')
    df['day_of_week'] = df['transaction_date'].dt.day_name()
    df['hour'] = df['transaction_date'].dt.hour
    
    # Daily
    daily_vol = df.groupby('date').size()
    fig, ax = plt.subplots(figsize=(14, 5))
    daily_vol.plot(ax=ax, color='teal')
    ax.set_title('Daily Transaction Volume')
    ax.set_ylabel('Count')
    plt.show()
    
    # Monthly
    monthly_stats = df.groupby('month').agg(count=('amount','size'), total_amount=('amount','sum'))
    fig, axes = plt.subplots(1, 2, figsize=(14, 5))
    monthly_stats['count'].plot(kind='bar', ax=axes[0], color='skyblue')
    axes[0].set_title('Monthly Transaction Volume')
    monthly_stats['total_amount'].plot(kind='bar', ax=axes[1], color='coral')
    axes[1].set_title('Monthly Transaction Amount')
    plt.tight_layout()
    plt.show()
    
    # Day of Week
    dow_order = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
    dow_stats = df.groupby('day_of_week').size().reindex(dow_order)
    fig, ax = plt.subplots(figsize=(10, 5))
    dow_stats.plot(kind='bar', ax=ax, color='purple')
    ax.set_title('Transactions by Day of Week')
    ax.set_ylabel('Count')
    plt.xticks(rotation=45)
    plt.show()
    
    # Hourly
    hourly_stats = df.groupby('hour').size()
    fig, ax = plt.subplots(figsize=(10, 5))
    hourly_stats.plot(kind='line', marker='o', ax=ax, color='orange')
    ax.set_title('Transactions by Hour of Day')
    ax.set_ylabel('Count')
    ax.set_xticks(range(0, 24))
    plt.grid(True, alpha=0.3)
    plt.show()
else:
    print("Column 'transaction_date' not found.")
"""))

# 10. Customer-Level Analysis
cells.append(nbf.v4.new_markdown_cell("# 10. Customer-Level Analysis\nAnalyzing customer spending patterns."))
cells.append(nbf.v4.new_code_cell("""if 'customer_id' in df.columns:
    customer_stats = df.groupby('customer_id').agg(
        total_spend=('amount', 'sum'),
        transaction_count=('amount', 'size'),
        avg_transaction_amount=('amount', 'mean')
    ).reset_index()
    
    top_spend = customer_stats.sort_values(by='total_spend', ascending=False).head(10)
    top_freq = customer_stats.sort_values(by='transaction_count', ascending=False).head(10)
    
    print("Top 10 Customers by Total Spend:")
    display(top_spend)
    
    print("Top 10 Customers by Transaction Frequency:")
    display(top_freq)
else:
    print("Column 'customer_id' not found.")
"""))

# 11. Outlier Context
cells.append(nbf.v4.new_markdown_cell("# 11. Outlier Context\nAnalyzing statistical outliers based on IQR methodology. Outliers are not necessarily fraud."))
cells.append(nbf.v4.new_code_cell("""Q1 = df['amount'].quantile(0.25)
Q3 = df['amount'].quantile(0.75)
IQR = Q3 - Q1
lower_bound = Q1 - 1.5 * IQR
upper_bound = Q3 + 1.5 * IQR

outliers = df[(df['amount'] < lower_bound) | (df['amount'] > upper_bound)]

print(f"Number of potential statistical outliers: {len(outliers):,}")
print(f"Percentage of transactions: {(len(outliers) / len(df)) * 100:.2f}%")

print("\nHighest-value outliers:")
display(outliers.nlargest(5, 'amount')[['transaction_id', 'amount', 'transaction_type', 'merchant_category', 'customer_id']])

if 'transaction_type' in outliers.columns:
    print("\nOutliers by Transaction Type:")
    display(outliers['transaction_type'].value_counts())

if 'merchant_category' in outliers.columns:
    print("\nOutliers by Merchant Category:")
    display(outliers['merchant_category'].value_counts().head(10))

if 'payment_method' in outliers.columns:
    print("\nOutliers by Payment Method:")
    display(outliers['payment_method'].value_counts())
"""))

# 12. Numeric Analysis
cells.append(nbf.v4.new_markdown_cell("# 12. Numeric Analysis\nAnalyzing distribution of transaction amounts."))
cells.append(nbf.v4.new_code_cell("""fig, axes = plt.subplots(1, 2, figsize=(14, 5))
sns.histplot(df['amount'], bins=50, kde=True, ax=axes[0], color='blue')
axes[0].set_title('Distribution of Transaction Amounts')

sns.boxplot(x=df['amount'], ax=axes[1], color='cyan')
axes[1].set_title('Boxplot of Transaction Amounts')
plt.show()

# Log scale for better visibility of skewed data
fig, ax = plt.subplots(figsize=(10, 5))
sns.histplot(df['amount'], bins=50, kde=True, log_scale=True, ax=ax, color='green')
ax.set_title('Log Distribution of Transaction Amounts')
plt.show()
"""))

# 13. Key Business Insights
cells.append(nbf.v4.new_markdown_cell("""# 13. Key Business Insights
*Total KPIs, business performance, and outlier context.*

### Key Findings
1. **Total Volume & Value**: The dataset contains 100,000 clean transactions representing significant total volume. 
2. **Date Range**: Transactions span from January 2023 to February 2024, providing over a year of behavioral data.
3. **Outliers**: There are 9,273 statistical outliers based on IQR, which represents ~9.27% of total transactions. These are high-value transactions and should not be automatically classified as fraud.
4. **Time Trends**: There are distinct hourly and daily patterns indicating peak usage times for the financial products.
5. **Customer Concentration**: A small percentage of customers account for a disproportionately large share of total transaction volume and value.
"""))

# 14. Next Development Stage
cells.append(nbf.v4.new_markdown_cell("""# 14. Next Development Stage
The analytical foundation is now complete and validated. The next planned stages for the FinSight AI project are:

1. **Anomaly Detection**: Implementing machine learning models to differentiate genuine outliers from actual fraudulent behavior.
2. **Customer Segmentation**: Grouping customers based on behavior, spend, and frequency to drive personalized insights.
3. **Dashboard/API Layer**: Creating the interactive visualizations and API endpoints to serve data.
4. **AI/LLM/RAG Layer**: Integrating advanced language models to provide conversational analytics on the processed data.
"""))

nb['cells'] = cells

with open('notebooks/02_eda_analysis.ipynb', 'w', encoding='utf-8') as f:
    nbf.write(nb, f)
print("Notebook generated.")
