from datetime import date

from fastapi import APIRouter, Depends, HTTPException

from app.auth import get_user_id
from app.config import settings
from app.extraction import ExtractionError, analyze_note
from app.llm.base import LLMProvider, ProviderError
from app.providers import get_provider
from app.schemas import AnalysisResult, AnalyzeIn

router = APIRouter(prefix="/ai", tags=["ai"])


@router.post("/analyze", response_model=AnalysisResult)
def analyze(
    data: AnalyzeIn,
    user_id: int = Depends(get_user_id),
    provider: LLMProvider = Depends(get_provider),
):
    today = data.today or date.today()
    try:
        return analyze_note(data.note, provider, today, settings.max_attempts)
    except (ExtractionError, ProviderError):
        raise HTTPException(
            status_code=502,
            detail="The AI could not produce a valid analysis. Please try again.",
        )
