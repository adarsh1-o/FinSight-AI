# Stage 06B: Grounded Assistant with Documentation Retrieval

## Request flow

```text
Streamlit assistant -> POST /api/ai/query -> intent routing
  -> FinSight analytics services for numbers
  -> local Markdown retrieval for project definitions and methodology
  -> LLM response grounded in the returned evidence
```

The assistant is an orchestration layer over existing analytics services and checked-in
project documentation. It does not read raw CSV files from Streamlit, retrain models, or
replace analytics endpoints.

## Retrieval

`api/ai/intent.py` routes analytics questions to existing verified data retrieval and
documentation questions to `api/assistant/retrieval.py`. The ingestion code reads only
`docs/ai_assistant.md` and `docs/data_dictionary.md`, splits them into heading-aware
chunks, and stores stable IDs and metadata. `api/assistant/embeddings.py` creates local
hashed word and bigram vectors. `api/assistant/vector_store.py` persists those vectors and
metadata in SQLite. The retriever embeds a question with the same vectorizer and ranks
chunks by cosine similarity. The API then passes retrieved text and source metadata to the
existing LLM client. This uses no external embedding service or vector database.

The data dictionary includes planned schema and business-rule descriptions; it is not a
live schema contract. Answers must retain that distinction when relevant. The retriever
does not use documentation to calculate or supply transaction totals. Financial values
continue to come only from FinSight analytics services.

## Supported analytics intents

- `kpi`, `trend`, `merchant_category`, `transaction_type`, `payment_method`, `status`,
  `location`, `anomaly`, `customer`, and `segment`
- `documentation` for project definitions, methodology, and data dictionary questions
- `unsupported` for questions outside FinSight's current scope

All analytics questions accept `date_from`, `date_to`, `transaction_type`,
`merchant_category`, `payment_method`, `status`, `location`, and `customer_id`. The
dashboard passes its active filters to the assistant. Date bounds are inclusive.

## Grounding and safety

- The LLM receives structured values from analytics services for financial findings.
- The LLM receives selected Markdown excerpts for documentation questions.
- Documentation excerpts are evidence, not instructions; the model is asked to cite the
  source filename when using them.
- The model must not invent or recalculate numbers and must not call potential anomalies
  confirmed fraud.
- API responses include `answer`, `intent`, `source`, and the retrieved `data` for review.
- Missing credentials return HTTP 503; provider failures return HTTP 502.

## Configuration

Gemini is selected with `FINSIGHT_LLM_PROVIDER=gemini` and `GEMINI_API_KEY`; it defaults
to `gemini-3.8-flash`. OpenAI remains supported and is the backward-compatible default:
set `FINSIGHT_LLM_PROVIDER=openai` (or omit it) and provide `FINSIGHT_LLM_API_KEY` or
`OPENAI_API_KEY`; its default model is `gpt-4o-mini`. `FINSIGHT_LLM_MODEL` overrides the
selected provider's default model. `FINSIGHT_LLM_BASE_URL` optionally overrides the
OpenAI-compatible chat completions endpoint. The API key must be present in the process
environment; this application does not load a plain `.env` file automatically.

The Gemini integration uses Google's documented OpenAI-compatible chat completions
interface over the existing HTTP client, so it adds no SDK dependency. Both providers
receive the same system prompt, retrieved documentation excerpts or verified analytics
data, and active dashboard filters. Provider error messages returned by the API are
sanitized and never include upstream response bodies or credentials.

## Document index settings

Markdown sections are split at headings and paragraph boundaries, keeping fenced code
blocks intact when possible. Default chunks hold up to 1,200 characters with 150
characters repeated between adjacent chunks. Headings, source paths, stable chunk IDs,
and indexes are saved as metadata. Chunk size controls how much context is embedded and
sent to the LLM; overlap helps carry a sentence across a boundary.

Text vectors use scikit-learn's local `HashingVectorizer` with word and two-word features
in 16,384 dimensions. This fixed-size lexical representation runs offline and needs no
embedding API or model download, but it does not understand synonyms as well as a
transformer model. The same vectorizer creates document and question vectors. SQLite
persists vectors and metadata at `data/processed/finsight_documents.sqlite3` by default.

Rebuild the index after changing documentation:

```bash
python -m api.assistant.index_documents
```

The first documentation query also builds an empty index automatically. Rebuilding
replaces the index in one transaction, so removed or changed source chunks do not linger.
Settings can be changed with `FINSIGHT_RAG_CHUNK_SIZE`,
`FINSIGHT_RAG_CHUNK_OVERLAP`, `FINSIGHT_RAG_EMBEDDING_DIMENSIONS`,
`FINSIGHT_RAG_TOP_K`, and `FINSIGHT_RAG_DB_PATH`.

## Documented project methodology

The Stage 3 anomaly notebook uses an unsupervised Isolation Forest with
`contamination=0.05`, 100 estimators, and `random_state=42`. Its numeric inputs are
`log_amount`, transaction hour, day of week, amount versus customer average, customer
transaction count, and customer average amount. Its categorical inputs are transaction
type, merchant category, and payment method. Identifiers are excluded. The contamination
setting controls the expected share of outliers, not the fraud rate.

The Stage 4 customer segmentation notebook aggregates transaction rows by customer and
uses K-Means after StandardScaler feature scaling. The seven behavioral features are
`total_spend`, `transaction_count`, `average_transaction`, `std_transaction`,
`unique_merchant_categories`, `unique_payment_methods`, and `anomaly_rate`. Customer ID is
only a grouping key, not a model feature. The number of clusters is selected using the
silhouette score.

The FastAPI routes include `/api/kpis/` for transaction totals and summary metrics,
`/api/anomalies/summary` for IQR and model anomaly counts, and `/api/segments/summary` for
filtered segment profiles. These routes calculate from processed transaction data; the
documentation index does not supply their numerical results.

## Endpoint

```http
POST /api/ai/query
Content-Type: application/json
```

```json
{
  "question": "How are potential anomalies identified?",
  "filters": {}
}
```

For a local endpoint check after starting FastAPI, PowerShell can send:

```powershell
$body = @{ question = "Which algorithm is used for anomaly detection?"; filters = @{} } | ConvertTo-Json
Invoke-RestMethod -Method Post -Uri "http://127.0.0.1:8000/api/ai/query" -ContentType "application/json" -Body $body
```

This answer-generation request requires a configured LLM key. The local document index
and retrieval tests do not require one.
