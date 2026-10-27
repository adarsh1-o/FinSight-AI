import os

import pytest
import requests
from fastapi import HTTPException
from fastapi.testclient import TestClient

from api.ai.intent import Intent
from api.ai.prompts import SYSTEM_PROMPT
from api.ai.service import (
    GroundedAIService,
    LLMAuthenticationError,
    LLMClient,
    LLMRateLimitError,
    LLMRequestError,
    LLMUnsupportedModelError,
    MissingLLMCredentials,
    UnsupportedLLMProvider,
)
from api.assistant.schemas import AssistantRequest, AssistantResponse
from api.main import app
from api.routers.ai import query_ai


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
    assert any(item["source"].endswith("data_dictionary.md") for item in result["data"]["documentation"])


def test_unsupported_question_does_not_call_llm():
    fake = FakeLLM()
    result = GroundedAIService(fake).answer("What is the weather today?")
    assert result["intent"] == Intent.UNSUPPORTED.value
    assert fake.calls == []


def test_missing_credentials_is_explicit(monkeypatch):
    monkeypatch.delenv("FINSIGHT_LLM_PROVIDER", raising=False)
    monkeypatch.delenv("FINSIGHT_LLM_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    with pytest.raises(MissingLLMCredentials):
        LLMClient().complete("What is the total transaction value?", Intent.KPI, {"total_transactions": 1}, {})


def test_gemini_request_uses_gemini_environment_and_preserves_grounded_context(monkeypatch):
    monkeypatch.setenv("FINSIGHT_LLM_PROVIDER", "gemini")
    monkeypatch.setenv("GEMINI_API_KEY", "unit-test-key")
    monkeypatch.setenv("FINSIGHT_LLM_MODEL", "gemini-test-model")
    monkeypatch.delenv("FINSIGHT_LLM_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    captured = {}

    class Response:
        def raise_for_status(self):
            pass

        def json(self):
            return {"choices": [{"message": {"content": "Grounded Gemini answer"}}]}

    def request(url, **kwargs):
        captured.update(url=url, **kwargs)
        return Response()

    client = LLMClient(request=request)
    evidence = {"total_transactions": 8, "documentation": [{"source": "docs/test.md", "excerpt": "Evidence"}]}
    answer = client.complete("Summarize verified facts", Intent.KPI, evidence, {"date_from": "2024-01-01"})

    assert answer == "Grounded Gemini answer"
    assert captured["url"] == "https://generativelanguage.googleapis.com/v1beta/openai/chat/completions"
    assert captured["headers"]["Authorization"] == "Bearer unit-test-key"
    assert captured["json"]["model"] == "gemini-test-model"
    assert captured["json"]["messages"][0]["content"] == SYSTEM_PROMPT
    assert "total_transactions" in captured["json"]["messages"][1]["content"]
    assert "date_from" in captured["json"]["messages"][1]["content"]


def test_gemini_requires_its_key_without_falling_back_to_openai(monkeypatch):
    monkeypatch.setenv("FINSIGHT_LLM_PROVIDER", "gemini")
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.setenv("OPENAI_API_KEY", "openai-test-key")
    with pytest.raises(MissingLLMCredentials, match="GEMINI_API_KEY"):
        LLMClient().complete("question", Intent.KPI, {}, {})


def test_existing_openai_provider_configuration_remains_supported(monkeypatch):
    monkeypatch.delenv("FINSIGHT_LLM_PROVIDER", raising=False)
    monkeypatch.delenv("FINSIGHT_LLM_API_KEY", raising=False)
    monkeypatch.setenv("OPENAI_API_KEY", "openai-test-key")
    monkeypatch.delenv("FINSIGHT_LLM_MODEL", raising=False)
    captured = {}

    class Response:
        def raise_for_status(self):
            pass

        def json(self):
            return {"choices": [{"message": {"content": "OpenAI answer"}}]}

    def request(url, **kwargs):
        captured.update(url=url, **kwargs)
        return Response()

    assert LLMClient(request=request).complete("question", Intent.KPI, {}, {}) == "OpenAI answer"
    assert captured["url"] == "https://api.openai.com/v1/chat/completions"
    assert captured["headers"]["Authorization"] == "Bearer openai-test-key"
    assert captured["json"]["model"] == "gpt-4o-mini"


def test_unsupported_provider_is_rejected_without_credentials(monkeypatch):
    monkeypatch.setenv("FINSIGHT_LLM_PROVIDER", "unknown")
    with pytest.raises(UnsupportedLLMProvider):
        LLMClient().complete("question", Intent.KPI, {}, {})


@pytest.mark.parametrize(("status", "error_type"), [
    (401, LLMAuthenticationError),
    (403, LLMAuthenticationError),
    (429, LLMRateLimitError),
    (404, LLMUnsupportedModelError),
])
def test_provider_http_errors_are_classified_without_exposing_body(monkeypatch, status, error_type):
    monkeypatch.setenv("FINSIGHT_LLM_PROVIDER", "gemini")
    monkeypatch.setenv("GEMINI_API_KEY", "unit-test-key")

    class FailedResponse:
        status_code = status
        text = "sensitive provider details"

        def raise_for_status(self):
            raise requests.HTTPError("sensitive provider details", response=self)

    with pytest.raises(error_type) as caught:
        LLMClient(request=lambda *args, **kwargs: FailedResponse()).complete("question", Intent.KPI, {}, {})
    assert "sensitive provider details" not in str(caught.value)


def test_empty_provider_response_is_rejected(monkeypatch):
    monkeypatch.setenv("FINSIGHT_LLM_API_KEY", "unit-test-key")
    monkeypatch.delenv("FINSIGHT_LLM_PROVIDER", raising=False)

    class EmptyResponse:
        def raise_for_status(self):
            pass

        def json(self):
            return {"choices": [{"message": {"content": "   "}}]}

    with pytest.raises(LLMRequestError, match="empty answer"):
        LLMClient(request=lambda *args, **kwargs: EmptyResponse()).complete("question", Intent.KPI, {}, {})


def test_network_failure_is_sanitized(monkeypatch):
    monkeypatch.setenv("FINSIGHT_LLM_API_KEY", "unit-test-key")
    monkeypatch.setenv("FINSIGHT_LLM_PROVIDER", "openai")

    def fail_request(*args, **kwargs):
        raise requests.ConnectionError("network failure with unrelated private details")

    with pytest.raises(LLMRequestError, match="could not return a valid answer") as caught:
        LLMClient(request=fail_request).complete("question", Intent.KPI, {}, {})
    assert "private details" not in str(caught.value)


def test_provider_failure_is_safe(monkeypatch):
    monkeypatch.setenv("FINSIGHT_LLM_PROVIDER", "openai")
    monkeypatch.setenv("FINSIGHT_LLM_API_KEY", "test-key")
    class FailedResponse:
        def raise_for_status(self):
            raise RuntimeError("provider failure")

    def request(*args, **kwargs):
        return FailedResponse()

    with pytest.raises(LLMRequestError):
        LLMClient(request=lambda *args, **kwargs: request()).complete("What is the total transaction value?", Intent.KPI, {}, {})


@pytest.mark.parametrize(("error", "status"), [
    (LLMRateLimitError("The language model is rate limited. Try again later."), 429),
    (LLMAuthenticationError("The language model rejected the configured API key or its access."), 502),
    (LLMUnsupportedModelError("The configured language model was not found or is unsupported."), 502),
    (LLMRequestError("The language model could not return a valid answer."), 502),
    (MissingLLMCredentials("Set GEMINI_API_KEY to enable Gemini answers."), 503),
])
def test_ai_endpoint_maps_provider_errors_to_safe_status(monkeypatch, error, status):
    class FailingAssistant:
        def answer(self, request):
            raise error

    monkeypatch.setattr("api.routers.ai.assistant_service", FailingAssistant())
    with pytest.raises(HTTPException) as caught:
        query_ai(AssistantRequest(question="Summarize verified data"))
    assert caught.value.status_code == status
    assert "unit-test-key" not in str(caught.value.detail)


def test_ai_endpoint_delegates_to_assistant_service_and_preserves_filters(monkeypatch):
    client = TestClient(app)
    filters = {
        "date_from": "2023-01-01",
        "date_to": "2023-01-31",
        "transaction_type": "purchase",
        "merchant_category": "Amazon",
        "payment_method": "card",
        "status": "completed",
        "location": "Boston",
        "customer_id": "customer-1",
    }
    calls = []

    class FakeAssistantService:
        def answer(self, request):
            calls.append(request)
            return AssistantResponse(
                answer="Assistant service placeholder",
                intent="placeholder",
                source="FinSight Assistant Service",
                data={"filters": request.filters},
            )

    monkeypatch.setattr("api.routers.ai.assistant_service", FakeAssistantService())
    response = client.post("/api/ai/query", json={"question": "What is the total transaction value?", "filters": filters})

    assert response.status_code == 200
    body = response.json()
    assert body == {
        "answer": "Assistant service placeholder",
        "intent": "placeholder",
        "source": "FinSight Assistant Service",
        "data": {"filters": filters},
    }
    assert len(calls) == 1
    assert calls[0].question == "What is the total transaction value?"
    assert calls[0].filters == filters


def test_ai_endpoint_validates_question():
    response = TestClient(app).post("/api/ai/query", json={"question": "", "filters": {}})

    assert response.status_code == 422
