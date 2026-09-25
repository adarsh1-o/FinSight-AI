import os
from typing import Any, Callable

import pandas as pd
import requests

from api.ai.intent import Intent, detect_intent
from api.ai.prompts import SYSTEM_PROMPT, build_user_prompt
from api.ai.rag import retrieve_documentation
from api.data_service import data_service
from api.routers.anomalies import get_anomalies_summary
from api.routers.customers import get_segments_summary
from api.routers.kpis import get_kpis


class AIServiceError(Exception):
    """Base error for the grounded AI service."""


class MissingLLMCredentials(AIServiceError):
    pass


class LLMRequestError(AIServiceError):
    pass


FILTER_KEYS = (
    "date_from",
    "date_to",
    "transaction_type",
    "merchant_category",
    "payment_method",
    "status",
    "location",
    "customer_id",
)

DEFINITIONS = {
    "iqr": "An IQR outlier is a transaction outside the interquartile-range bounds used to identify statistical outliers.",
    "isolation forest": "Isolation Forest is an unsupervised model that flags observations that are easier to isolate from the rest of the data.",
    "anomaly": "A potential anomaly is a statistical outlier or model-flagged transaction, not confirmed fraud.",
}


def _filters(values: dict[str, Any] | None) -> dict[str, str]:
    return {key: str(values[key]) for key in FILTER_KEYS if values and values.get(key) not in (None, "")}


def _filtered_transactions(filters: dict[str, str]) -> pd.DataFrame:
    return data_service.apply_filters(data_service.get_transactions(), **filters)


def _definition(question: str) -> dict[str, Any]:
    normalized = question.casefold()
    for term, explanation in DEFINITIONS.items():
        if term in normalized:
            return {"definition": explanation}
    return {}


def retrieve_verified_data(intent: Intent, filters: dict[str, str], question: str) -> dict[str, Any]:
    if intent is Intent.UNSUPPORTED:
        return {}
    if intent is Intent.DOCUMENTATION:
        return {"documentation": retrieve_documentation(question)}
    if intent is Intent.DEFINITION:
        return _definition(question)
    if intent is Intent.KPI:
        return get_kpis(**filters)
    if intent is Intent.ANOMALY:
        return get_anomalies_summary(**filters)
    if intent is Intent.SEGMENT:
        return {"segments": get_segments_summary(**filters)}
    if intent is Intent.TREND:
        frame = _filtered_transactions(filters)
        if frame.empty:
            return {"monthly_trends": []}
        frame = frame.copy()
        frame["month"] = frame["transaction_date"].dt.to_period("M").astype(str)
        trends = frame.groupby("month").agg(
            transaction_count=("transaction_id", "count"),
            transaction_amount=("amount", "sum"),
        ).reset_index()
        return {"monthly_trends": trends.to_dict(orient="records")}

    frame = _filtered_transactions(filters)
    if frame.empty:
        return {"results": []}
    dimension = {
        Intent.MERCHANT_CATEGORY: "merchant_category",
        Intent.TRANSACTION_TYPE: "transaction_type",
        Intent.PAYMENT_METHOD: "payment_method",
        Intent.STATUS: "status",
        Intent.LOCATION: "location",
    }.get(intent)
    if dimension:
        results = frame.groupby(dimension).agg(
            transaction_count=("transaction_id", "count"),
            total_amount=("amount", "sum"),
            average_amount=("amount", "mean"),
        ).reset_index().sort_values("total_amount", ascending=False)
        return {"results": results.to_dict(orient="records")}
    if intent is Intent.CUSTOMER:
        results = frame.groupby("customer_id").agg(
            transaction_count=("transaction_id", "count"),
            total_amount=("amount", "sum"),
        ).reset_index().sort_values("total_amount", ascending=False).head(10)
        return {"top_customers": results.to_dict(orient="records")}
    return {}


class LLMClient:
    def __init__(self, request: Callable[..., Any] | None = None):
        self.api_key = os.getenv("FINSIGHT_LLM_API_KEY") or os.getenv("OPENAI_API_KEY")
        self.model = os.getenv("FINSIGHT_LLM_MODEL", "gpt-4o-mini")
        self.base_url = os.getenv("FINSIGHT_LLM_BASE_URL", "https://api.openai.com/v1/chat/completions")
        self._request = request or requests.post

    def complete(self, question: str, intent: Intent, data: dict[str, Any], filters: dict[str, str]) -> str:
        if not self.api_key:
            raise MissingLLMCredentials("Set FINSIGHT_LLM_API_KEY or OPENAI_API_KEY to enable answers.")
        payload = {
            "model": self.model,
            "temperature": 0.1,
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": build_user_prompt(question, intent.value, data, filters)},
            ],
        }
        try:
            response = self._request(
                self.base_url,
                headers={"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"},
                json=payload,
                timeout=30,
            )
            response.raise_for_status()
            content = response.json().get("choices", [{}])[0].get("message", {}).get("content")
        except (requests.RequestException, RuntimeError, ValueError, IndexError, KeyError, TypeError) as error:
            raise LLMRequestError("The language model could not return a valid answer.") from error
        if not isinstance(content, str) or not content.strip():
            raise LLMRequestError("The language model returned an empty answer.")
        return content.strip()


class GroundedAIService:
    def __init__(self, llm_client: LLMClient | None = None):
        self.llm_client = llm_client or LLMClient()

    def answer(self, question: str, filters: dict[str, Any] | None = None) -> dict[str, Any]:
        if not question or not question.strip():
            raise AIServiceError("Enter a question about the FinSight data.")
        intent = detect_intent(question)
        clean_filters = _filters(filters)
        verified_data = retrieve_verified_data(intent, clean_filters, question)
        if intent is Intent.UNSUPPORTED:
            return {
                "answer": "I can answer questions about FinSight KPIs, trends, categories, payment methods, statuses, locations, anomalies, customers, and segments.",
                "intent": intent.value,
                "source": "FinSight Analytics",
                "data": {},
            }
        answer = self.llm_client.complete(question, intent, verified_data, clean_filters)
        return {
            "answer": answer,
            "intent": intent.value,
            "source": "FinSight Project Documentation" if intent in (Intent.DOCUMENTATION, Intent.DEFINITION) else "FinSight Analytics",
            "data": verified_data,
        }
