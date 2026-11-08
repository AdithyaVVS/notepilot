import hashlib
from datetime import date, datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.config import settings
from app.extraction import ExtractionError, build_result, extract_raw
from app.llm.base import LLMProvider, ProviderError
from app.models import AnalysisCache, UsageLog
from app.schemas import AnalysisResult, RawAnalysis


class QuotaExceeded(Exception):
    def __init__(self, scope: str):
        super().__init__(scope)
        self.scope = scope  # "user" or "global"


class CountingProvider:
    """Wraps a provider and counts how many real requests were made,
    including ones that failed."""

    def __init__(self, inner: LLMProvider):
        self.inner = inner
        self.calls = 0

    def generate(self, instructions: str, content: str) -> str:
        self.calls += 1
        return self.inner.generate(instructions, content)


def provider_label() -> str:
    if settings.llm_provider == "gemini":
        return f"gemini:{settings.gemini_model}"
    return settings.llm_provider


def cache_key(note: str) -> str:
    # The provider and model are part of the key, so switching models never reuses old answers.
    return hashlib.sha256(f"{provider_label()}\n{note}".encode()).hexdigest()


def used_today(db: Session, user_id: int | None = None) -> int:
    start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    query = select(func.coalesce(func.sum(UsageLog.requests), 0)).where(
        UsageLog.created_at >= start
    )
    if user_id is not None:
        query = query.where(UsageLog.user_id == user_id)
    return int(db.scalar(query))


def _record(db: Session, user_id: int, requests: int, outcome: str, note: str):
    db.add(
        UsageLog(
            user_id=user_id,
            requests=requests,
            outcome=outcome,
            provider=provider_label(),
            note_chars=len(note),
        )
    )
    db.commit()


def run_analysis(
    db: Session, user_id: int, note: str, today: date, provider: LLMProvider
) -> AnalysisResult:
    key = cache_key(note)
    cached = db.scalar(
        select(AnalysisCache).where(
            AnalysisCache.user_id == user_id, AnalysisCache.text_hash == key
        )
    )
    if cached is not None:
        raw = RawAnalysis.model_validate(cached.raw_json)
        _record(db, user_id, 0, "cache", note)
        result = build_result(raw, note, today, attempts=0)
        result.source = "cache"
        return result

    user_left = settings.user_daily_limit - used_today(db, user_id)
    global_left = settings.global_daily_limit - used_today(db)
    if global_left <= 0:
        raise QuotaExceeded("global")
    if user_left <= 0:
        raise QuotaExceeded("user")

    counter = CountingProvider(provider)
    allowed = min(settings.max_attempts, user_left, global_left)
    try:
        raw, attempts = extract_raw(note, counter, allowed)
    except ExtractionError:
        _record(db, user_id, counter.calls, "invalid", note)
        raise
    except ProviderError:
        _record(db, user_id, counter.calls, "provider_error", note)
        raise

    db.add(AnalysisCache(user_id=user_id, text_hash=key, raw_json=raw.model_dump()))
    try:
        db.commit()
    except IntegrityError:  # the same note was saved a moment ago by a parallel request
        db.rollback()
    _record(db, user_id, counter.calls, "ok", note)
    return build_result(raw, note, today, attempts)
