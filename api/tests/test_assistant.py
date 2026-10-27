from api.assistant.schemas import AssistantRequest
from api.assistant.service import AssistantService


class FakeGroundedService:
    def __init__(self, result=None):
        self.result = result or {
            "answer": "The grounded answer",
            "intent": "kpi",
            "source": "FinSight Analytics",
            "data": {"total_transactions": 12},
        }
        self.calls = []

    def answer(self, question, filters):
        self.calls.append((question, filters))
        return self.result


def test_answer_delegates_to_grounded_service_and_preserves_response_shape():
    grounded = FakeGroundedService()
    response = AssistantService(grounded).answer(AssistantRequest(question="Summarize spending"))

    assert response.intent == "kpi"
    assert response.source == "FinSight Analytics"
    assert response.answer == "The grounded answer"
    assert response.data["total_transactions"] == 12
    assert response.data["filters"] == {}
    assert grounded.calls == [("Summarize spending", {})]


def test_answer_preserves_all_filter_fields():
    filters = {
        "date_from": "2023-01-01",
        "date_to": "2023-01-31",
        "transaction_type": "purchase",
        "merchant_category": "Amazon",
        "payment_method": "card",
        "status": "completed",
        "location": "Boston",
        "customer_id": "customer-1",
        "future_filter": "preserved",
    }
    response = AssistantService(FakeGroundedService()).answer(AssistantRequest(question="Summarize this data", filters=filters))

    assert response.data["filters"] == filters
