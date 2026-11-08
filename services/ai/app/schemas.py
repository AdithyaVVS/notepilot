from datetime import date
from typing import Literal

from pydantic import BaseModel, Field, field_validator

MAX_NOTE_CHARS = 6000
Priority = Literal["high", "medium", "low"]


class RawActionItem(BaseModel):
    """What the model is asked to return. Anything else fails validation."""

    task: str = Field(min_length=3, max_length=300)
    owner: str | None = Field(default=None, max_length=100)
    deadline_text: str | None = Field(default=None, max_length=100)
    priority: Priority = "medium"
    evidence: str = Field(min_length=3, max_length=500)


class RawAnalysis(BaseModel):
    summary: str = Field(min_length=1, max_length=1000)
    action_items: list[RawActionItem] = Field(max_length=30)


class ActionItem(BaseModel):
    task: str
    owner: str | None
    deadline_text: str | None
    deadline: date | None
    priority: Priority
    evidence: str
    evidence_start: int
    evidence_end: int


class AnalysisResult(BaseModel):
    summary: str
    action_items: list[ActionItem]
    dropped_items: int
    attempts: int
    source: Literal["ai", "cache", "sample"] = "ai"


class AnalyzeIn(BaseModel):
    note: str = Field(min_length=10, max_length=MAX_NOTE_CHARS)
    today: date | None = None
    mode: Literal["ai", "sample"] = "ai"

    @field_validator("note")
    @classmethod
    def not_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("Note must not be blank")
        return value
