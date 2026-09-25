# FinSight AI

FinSight AI is a financial transaction analytics project, implementing stages from data profiling up to full AI analytics.

## Current Stage: Stage 06B (Grounded AI Assistant with Documentation Retrieval)

This project currently implements a full **FastAPI** backend and **Streamlit** dashboard over the processed data.

### Architecture

```
Streamlit Dashboard (Frontend)
        ↓ (HTTP/REST)
FastAPI REST API (Backend)
        ↓
Data Service / Analytics Service
        ↓
Processed FinSight AI Datasets (CSV)
```

**Technology Stack:**
- **Backend**: FastAPI, Uvicorn, Pandas
- **Frontend/Dashboard**: Streamlit, Plotly
- **Data Source**: Validated outputs from Stages 1-4 (`transactions_cleaned.csv`, `transactions_with_anomalies.csv`, `customer_segments.csv`)
- **Testing**: Pytest, HTTPX

### Local Startup Instructions

*Important: The dashboard relies entirely on the API. The API must be running first.*

#### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

#### 2. Start the FastAPI Backend
```bash
# From the root directory (FinSight-AI)
uvicorn api.main:app --reload
```
The API will be available at `http://localhost:8000`. You can view the swagger documentation at `http://localhost:8000/docs`.

#### 3. Start the Streamlit Dashboard
```bash
# In a new terminal window, from the root directory
streamlit run dashboard/app.py
```
The dashboard will open in your browser, typically at `http://localhost:8501`.

### API Endpoints

- `GET /health`: System health check
- `GET /api/kpis/`: High-level metrics
- `GET /api/transactions`: Filterable transaction list
- `GET /api/transactions/recent`: Most recent transactions
- `GET /api/trends/monthly`: Time-series aggregations
- `GET /api/anomalies/`: List of flagged anomalies
- `GET /api/anomalies/summary`: Statistics on detection overlap
- `GET /api/customers/top`: Highest value customers
- `GET /api/segments`: Customer clustering output
- `GET /api/segments/summary`: Segment profiles
- `GET /api/categories`, `/api/payment-methods`, `/api/locations`: Metadata for filters
- `POST /api/ai/query`: Grounded natural-language FinSight analytics

Example request:
```json
{
        "question": "Which merchant category has the highest spending?",
        "filters": {"date_from": "2023-01-01", "date_to": "2024-02-29"}
}
```

### AI Assistant Setup

The dashboard AI Assistant retrieves verified FinSight analytics for numerical questions and relevant local Markdown documentation for methodology and definition questions. It respects the active dashboard filters for analytics and does not read raw CSV files from Streamlit. Documentation retrieval currently uses local lexical search over `docs/ai_assistant.md` and `docs/data_dictionary.md`.

1. Copy `.env.example` to `.env` or set the variables in your shell.
2. Set `FINSIGHT_LLM_API_KEY` (or `OPENAI_API_KEY`) to a valid provider key.
3. Optionally set `FINSIGHT_LLM_MODEL` and `FINSIGHT_LLM_BASE_URL` for a compatible provider.
4. Start FastAPI, then start Streamlit using the commands above.

Without credentials, analytics APIs and the rest of the dashboard continue to work, while AI queries return a configuration message instead of a fabricated answer.

### Testing Instructions

Run the automated test suite to verify the API logic:
```bash
# From the root directory
pytest api/tests/
```

### Current Limitations
- The underlying anomalies are *potential anomalies* (unsupervised ML). They are NOT verified fraud.
- Data is currently loaded from static CSV files (Stage 1-4 outputs).

Financial numbers continue to come from FinSight analytics services. See [docs/ai_assistant.md](docs/ai_assistant.md) for retrieval behavior and grounding rules.

See [docs/ai_assistant.md](docs/ai_assistant.md) for the Stage 06A architecture and grounding rules.
