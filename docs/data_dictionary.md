# Data Dictionary - FinSight AI

## Overview
This document defines the planned data model for FinSight AI, outlining the schemas for customers, accounts, transactions, customer activity, and fraud labels. 

## Planned Scale of the Synthetic Dataset
- **Customers**: 10,000+
- **Accounts**: 10,000+
- **Transactions**: 100,000+
- **Customer Activity Records**: 10,000+

---

## Table Specifications

### 1. customers
**Purpose:** Stores foundational demographic and profile information for all users of the platform.

| Column Name | Data Type | Description | PK/FK | Example Value |
|-------------|-----------|-------------|-------|---------------|
| `customer_id` | VARCHAR | Unique identifier for the customer | PK | `c-00001` |
| `first_name` | VARCHAR | Customer's first name | | `Jane` |
| `last_name` | VARCHAR | Customer's last name | | `Doe` |
| `email` | VARCHAR | Primary contact email address | | `jane.doe@example.com` |
| `date_of_birth` | DATE | Customer's date of birth | | `1985-11-20` |
| `gender` | VARCHAR | Customer's gender identity | | `Female` |
| `country` | VARCHAR | Customer's country of residence | | `USA` |
| `city` | VARCHAR | Customer's city of residence | | `New York` |
| `occupation` | VARCHAR | Customer's current occupation | | `Engineer` |
| `annual_income` | DECIMAL(15,2) | Customer's estimated annual income | | `120500.00` |
| `account_type` | VARCHAR | Primary category of the customer's overarching account | | `Premium` |
| `onboarding_date` | TIMESTAMP | Date and time the customer joined the platform (UTC) | | `2024-01-15 08:30:00` |

### 2. accounts
**Purpose:** Stores information about financial accounts associated with customers.

| Column Name | Data Type | Description | PK/FK | Example Value |
|-------------|-----------|-------------|-------|---------------|
| `account_id` | VARCHAR | Unique identifier for the account | PK | `a-00001` |
| `customer_id` | VARCHAR | Identifier of the account owner | FK | `c-00001` |
| `account_type` | VARCHAR | Type of financial account (e.g., Checking, Savings) | | `Checking` |
| `opened_date` | TIMESTAMP | Date the account was officially opened (UTC) | | `2024-01-16 10:00:00` |
| `balance` | DECIMAL(15,2) | Current balance of the account | | `5432.50` |
| `currency` | VARCHAR(3) | ISO Currency code (e.g., USD, EUR) | | `USD` |
| `status` | VARCHAR | Current status of the account (Active, Suspended, Closed) | | `Active` |

### 3. transactions
**Purpose:** Records all financial movements (credits and debits) occurring on accounts.

| Column Name | Data Type | Description | PK/FK | Example Value |
|-------------|-----------|-------------|-------|---------------|
| `transaction_id` | VARCHAR | Unique identifier for the transaction | PK | `t-000001` |
| `customer_id` | VARCHAR | Customer who initiated the transaction | FK | `c-00001` |
| `account_id` | VARCHAR | Account involved in the transaction | FK | `a-00001` |
| `transaction_date` | TIMESTAMP | Exact date and time of the transaction (UTC) | | `2024-03-01 14:45:00` |
| `amount` | DECIMAL(15,2) | Value of the transaction (positive for deposit, negative for withdrawal) | | `-250.00` |
| `transaction_type` | VARCHAR | Type of transaction (e.g., Deposit, Withdrawal) | | `Transfer` |
| `merchant_category`| VARCHAR | Category of merchant (e.g., Groceries, Travel, Rent) | | `Groceries` |
| `payment_method` | VARCHAR | Method used for the transaction (e.g., Card, ACH) | | `Card` |
| `location` | VARCHAR | Geographic location of the transaction | | `New York, NY` |
| `status` | VARCHAR | Status of the transaction (Completed, Failed, Pending) | | `Completed` |

### 4. customer_activity
**Purpose:** An analytical aggregate/feature source (NOT raw session-event data). It aggregates the digital footprint of customers over their lifetime to power behavioral models.

| Column Name | Data Type | Description | PK/FK | Example Value |
|-------------|-----------|-------------|-------|---------------|
| `customer_id` | VARCHAR | Customer the activity aggregates belong to | PK/FK | `c-00001` |
| `login_frequency` | INT | Estimated average logins per month | | `15` |
| `avg_session_time` | DECIMAL(10,1) | Average time spent per session in seconds | | `345.5` |
| `last_login` | TIMESTAMP | Timestamp of the most recent login (UTC) | | `2024-03-01 14:00:00` |
| `days_since_last_login`| INT | Number of days since the most recent login | | `3` |
| `support_tickets` | INT | Total number of support tickets raised | | `1` |
| `failed_transactions` | INT | Total number of failed transactions | | `2` |
| `transaction_frequency`| INT | Estimated average transactions per month | | `10` |

### 5. fraud_labels
**Purpose:** Stores synthetic ground truth labels indicating whether a transaction was deemed fraudulent, for model-development purposes only.

| Column Name | Data Type | Description | PK/FK | Example Value |
|-------------|-----------|-------------|-------|---------------|
| `transaction_id` | VARCHAR | The transaction being labeled | PK/FK | `t-000001` |
| `is_fraud` | BOOLEAN | Indicates if the transaction is fraudulent (True/False) | | `True` |
| `resolution_date` | TIMESTAMP | Date and time when the fraud label was confirmed (UTC) | | `2024-03-05 10:00:00` |

---

## Relationships, Primary Keys, and Foreign Keys
- **`customers` (1) to `accounts` (N)**: A single customer can own multiple financial accounts.
- **`accounts` (1) to `transactions` (N)**: An account can have numerous transaction records.
- **`customers` (1) to `transactions` (N)**: A direct denormalized link exists between customers and transactions for faster analytical querying.
- **`customers` (1) to `customer_activity` (1)**: The activity table is a direct 1:1 aggregation per customer.
- **`transactions` (1) to `fraud_labels` (0 or 1)**: A transaction can have a corresponding fraud label indicating ground truth.

## Important Business Rules
1. **Balance Consistency:** The `balance` in the `accounts` table reflects the state of the account.
2. **Account Ownership:** Every account must be tied to a valid `customer_id`.
3. **Transaction Status:** High-risk or fraudulent transactions should trigger an account status change to 'Suspended'.
4. **Currency Handling:** Cross-currency transactions require standardization to a base currency for unified model training, while the original currency should still be logged.
5. **Data Privacy:** PII such as `first_name`, `last_name`, and `email` must be handled with appropriate masking.

## Expected Data Quality Issues (Intentionally Injected)
To accurately simulate a real-world data engineering environment, the following issues are explicitly generated and will require downstream cleaning:
- **Missing Values:** Small percentage of missing `date_of_birth` and `city` in customers.
- **Duplicate Records:** ~50 duplicate rows in `transactions`.
- **Formatting Inconsistencies:** Random lowercase `city` names in `customers`.
- **Invalid Values:** Occasional negative integer values (e.g., `-1` in `login_frequency`). 
*Note: Primary and Foreign keys remain uncorrupted to preserve structural integrity.*
