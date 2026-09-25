from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from api.ai.service import AIServiceError, GroundedAIService, LLMRequestError, MissingLLMCredentials


router = APIRouter(prefix="/api/ai", tags=["ai"])
ai_service = GroundedAIService()


class AIQueryRequest(BaseModel):
    question: str = Field(..., min_length=1, max_length=2000)
    filters: dict[str, Any] = Field(default_factory=dict)


class AIQueryResponse(BaseModel):
    answer: str
    intent: str
    source: str
    data: dict[str, Any]


@router.post(
    "/query",
    responses={
        400: {"description": "Invalid or empty question"},
        502: {"description": "Language model request failed"},
        503: {"description": "Language model credentials are missing"},
    },
)
def query_ai(request: AIQueryRequest) -> AIQueryResponse:
    try:
        return ai_service.answer(request.question, request.filters)
    except MissingLLMCredentials as error:
        raise HTTPException(status_code=503, detail=str(error)) from error
    except LLMRequestError as error:
        raise HTTPException(status_code=502, detail=str(error)) from error
    except AIServiceError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error