from fastapi import APIRouter, HTTPException

from api.ai.service import AIServiceError, LLMRequestError, MissingLLMCredentials
from api.assistant.schemas import AssistantRequest, AssistantResponse
from api.assistant.service import AssistantService, AssistantServiceUnavailable


router = APIRouter(prefix="/api/ai", tags=["ai"])
assistant_service = AssistantService()


@router.post(
    "/query",
    response_model=AssistantResponse,
    responses={400: {"description": "Invalid question"}, 502: {"description": "LLM provider failed"}, 503: {"description": "LLM credentials or retrieval service unavailable"}},
)
def query_ai(request: AssistantRequest) -> AssistantResponse:
    """Validate the request and delegate assistant orchestration to the service."""
    try:
        return assistant_service.answer(request)
    except MissingLLMCredentials as error:
        raise HTTPException(status_code=503, detail=str(error)) from error
    except LLMRequestError as error:
        raise HTTPException(status_code=502, detail="The language model could not return a valid answer.") from error
    except AIServiceError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    except AssistantServiceUnavailable as error:
        raise HTTPException(status_code=503, detail=str(error)) from error
