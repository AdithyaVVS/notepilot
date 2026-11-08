from datetime import datetime

from sqlalchemy import DateTime, String, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class AnalysisCache(Base):
    """The model's validated reply for a note, so repeating a note costs nothing."""

    __tablename__ = "analysis_cache"
    __table_args__ = (
        UniqueConstraint("user_id", "text_hash", name="uq_cache_user_hash"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(index=True)
    text_hash: Mapped[str] = mapped_column(String(64))
    raw_json: Mapped[dict] = mapped_column(JSONB)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class UsageLog(Base):
    """One row per analysis: who, how many real LLM requests, what happened.
    The note text is never stored here."""

    __tablename__ = "usage_log"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), index=True
    )
    requests: Mapped[int]
    outcome: Mapped[str] = mapped_column(String(20))
    provider: Mapped[str] = mapped_column(String(60))
    note_chars: Mapped[int]
