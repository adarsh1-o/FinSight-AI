import sqlite3

from api.ai.service import GroundedAIService

from .schemas import AssistantRequest, AssistantResponse


class AssistantServiceUnavailable(Exception):
    """Raised when document retrieval cannot be used by the assistant."""


class AssistantService:
    """Adapt the existing grounded analytics and documentation service to the API schema."""

    def __init__(self, grounded_service: GroundedAIService | None = None):
        self.grounded_service = grounded_service or GroundedAIService()

    def answer(self, request: AssistantRequest) -> AssistantResponse:
        """Run the existing grounded assistant and preserve the response contract."""
        try:
            result = self.grounded_service.answer(request.question, request.filters)
        except (OSError, ValueError, RuntimeError, sqlite3.Error) as error:
            raise AssistantServiceUnavailable(
                "The documentation retrieval service is temporarily unavailable."
            ) from error
        data = dict(result.get("data") or {})
        # Keep all dashboard filters in the response for API compatibility. Only
        # the allow-listed filter keys are passed to analytics calculations.
        data["filters"] = request.filters
        return AssistantResponse(
            answer=result["answer"],
            intent=result["intent"],
            source=result["source"],
            data=data,
        )
