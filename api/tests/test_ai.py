import os

import pytest
from fastapi.testclient import TestClient

from api.ai.intent import Intent
from api.ai.service import GroundedAIService, LLMClient, LLMRequestError, MissingLLMCredentials
from api.main import app


class FakeLLM:
    def __init__(self, answer="Grounded answer"):
        self.answer_text = answer
        self.calls = []

    def complete(self, question, intent, data, filters):
        self.calls.append({"question": question, "intent": intent, "data": data, "filters": filters})
        return self.answer_text


def test_kpi_question_uses_actual_kpi_data():
    fake = FakeLLM()
    result = GroundedAIService(fake).answer("What is the total transaction count?", {"date_from": "2023-05-01", "date_to": "2023-05-31"})
    assert result["intent"] == Intent.KPI.value
    assert result["data"]["total_transactions"] == 7365
    assert fake.calls[0]["filters"]["date_to"] == "2023-05-31"


def test_merchant_category_question_is_grounded():
    fake = FakeLLM()
    result = GroundedAIService(fake).answer("Which merchant category has the highest spending?")
    assert result["intent"] == Intent.MERCHANT_CATEGORY.value
    assert result["data"]["results"]
    assert result["data"]["results"][0]["total_amount"] >= result["data"]["results"][1]["total_amount"]


def test_trend_question_is_grounded():
    result = GroundedAIService(FakeLLM()).answer("Explain the major spending trends.")
    assert result["intent"] == Intent.TREND.value
    assert result["data"]["monthly_trends"]


def test_anomaly_question_uses_actual_anomaly_data():
    result = GroundedAIService(FakeLLM()).answer("How many potential anomalies were detected?")
    assert result["intent"] == Intent.ANOMALY.value
    assert result["data"]["ml_anomaly_count"] == 5000


def test_segment_question_is_grounded():
    result = GroundedAIService(FakeLLM()).answer("Which customer segment has the highest spending?")
    assert result["intent"] == Intent.SEGMENT.value
    assert result["data"]["segments"]


def test_documentation_question_retrieves_local_methodology():
    fake = FakeLLM()
    result = GroundedAIService(fake).answer("How are potential anomalies identified?")
    assert result["intent"] == Intent.DOCUMENTATION.value
    excerpts = result["data"]["documentation"]
    assert excerpts
    assert all({"source", "section", "excerpt"} <= excerpt.keys() for excerpt in excerpts)
    assert result["source"] == "FinSight Project Documentation"
    assert fake.calls[0]["data"] == result["data"]


def test_documentation_metric_question_returns_dictionary_evidence():
    fake = FakeLLM()
    result = GroundedAIService(fake).answer("What does transaction_date mean in the data dictionary?")
    assert result["intent"] == Intent.DOCUMENTATION.value
    assert any(item["source"] == "data_dictionary.md" for item in result["data"]["documentation"])


def test_unsupported_question_does_not_call_llm():
    fake = FakeLLM()
    result = GroundedAIService(fake).answer("What is the weather today?")
    assert result["intent"] == Intent.UNSUPPORTED.value
    assert fake.calls == []


def test_missing_credentials_is_explicit(monkeypatch):
    monkeypatch.delenv("FINSIGHT_LLM_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    with pytest.raises(MissingLLMCredentials):
        LLMClient().complete("What is the total transaction value?", Intent.KPI, {"total_transactions": 1}, {})


def test_provider_failure_is_safe(monkeypatch):
    monkeypatch.setenv("FINSIGHT_LLM_API_KEY", "test-key")
    class FailedResponse:
        def raise_for_status(self):
            raise RuntimeError("provider failure")

    def request(*args, **kwargs):
        return FailedResponse()

    with pytest.raises(LLMRequestError):
        LLMClient(request=lambda *args, **kwargs: request()).complete("What is the total transaction value?", Intent.KPI, {}, {})


def test_ai_endpoint_validates_request_without_real_llm(monkeypatch):
    client = TestClient(app)
    monkeypatch.setattr("api.routers.ai.ai_service", GroundedAIService(FakeLLM()))
    response = client.post("/api/ai/query", json={"question": "What is the total transaction value?", "filters": {"merchant_category": "Amazon"}})
    assert response.status_code == 200
    body = response.json()
    assert body["intent"] == Intent.KPI.value
    assert body["data"]["total_transactions"] < 100000
