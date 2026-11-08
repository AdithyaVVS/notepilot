import logging
from datetime import date

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.auth import get_user_id
from app.config import settings
from app.database import get_db
from app.extraction import ExtractionError, analyze_note
from app.llm.base import LLMProvider, ProviderError
from app.llm.fake import FakeProvider
from app.providers import get_provider
from app.schemas import AnalysisResult, AnalyzeIn
from app.service import QuotaExceeded, run_analysis, used_today

logger = logging.getLogger("notepilot.ai")
router = APIRouter(prefix="/ai", tags=["ai"])


@router.post("/analyze", response_model=AnalysisResult)
def analyze(
    data: AnalyzeIn,
    user_id: int = Depends(get_user_id),
    db: Session = Depends(get_db),
    provider: LLMProvider = Depends(get_provider),
):
    today = data.today or date.today()

    if data.mode == "sample":
        result = analyze_note(data.note, FakeProvider(), today, 1)
        result.source = "sample"
        return result

    try:
        return run_analysis(db, user_id, data.note, today, provider)
    except QuotaExceeded as exc:
        if exc.scope == "global":
            raise HTTPException(
                status_code=503,
                detail="The shared AI allowance for today is used up. "
                "Try sample mode, or come back tomorrow.",
            )
        raise HTTPException(
            status_code=429,
            detail=f"You have used your {settings.user_daily_limit} AI analyses "
            "for today. Sample mode is still available.",
        )
    except (ExtractionError, ProviderError) as exc:
        logger.warning("analysis failed for user %s: %s", user_id, exc)
        raise HTTPException(
            status_code=502,
            detail="The AI could not produce a valid analysis. Please try again.",
        )


@router.get("/usage")
def usage(user_id: int = Depends(get_user_id), db: Session = Depends(get_db)):
    return {
        "used_today": used_today(db, user_id),
        "daily_limit": settings.user_daily_limit,
    }
