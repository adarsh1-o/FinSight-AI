from typing import Any

from pydantic import BaseModel, Field


class AssistantRequest(BaseModel):
    question: str = Field(..., min_length=1, max_length=2000, description="The user's question to the AI assistant")
    filters: dict[str, Any] = Field(default_factory=dict, description="Current dashboard filters")


class AssistantResponse(BaseModel):
    """Response shape used by the existing ``POST /api/ai/query`` contract."""

    answer: str
    intent: str
    source: str
    data: dict[str, Any] = Field(default_factory=dict)
