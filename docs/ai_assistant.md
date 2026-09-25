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
documentation questions to `api/ai/rag.py`. The documentation retriever searches relevant
Markdown sections in `docs/ai_assistant.md` and `docs/data_dictionary.md` using a small,
transparent lexical ranker. It returns up to three excerpts with source filenames and
section headings. It runs locally and adds no package or external vector database.

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

Set `FINSIGHT_LLM_API_KEY` or `OPENAI_API_KEY`. The model defaults to `gpt-4o-mini`; set
`FINSIGHT_LLM_MODEL` and `FINSIGHT_LLM_BASE_URL` for a compatible provider when needed.

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
