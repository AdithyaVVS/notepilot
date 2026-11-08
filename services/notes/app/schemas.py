from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

MAX_BODY_CHARS = 6000


class NoteCreate(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    body: str = Field(min_length=1, max_length=MAX_BODY_CHARS)

    @field_validator("title")
    @classmethod
    def clean_title(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Title must not be blank")
        return value

    @field_validator("body")
    @classmethod
    def body_not_blank(cls, value: str) -> str:
        # Not trimmed on purpose: saved task positions point into this exact text.
        if not value.strip():
            raise ValueError("Note must not be blank")
        return value


class PlanItem(BaseModel):
    task: str = Field(min_length=3, max_length=300)
    owner: str | None = Field(default=None, max_length=100)
    deadline_text: str | None = Field(default=None, max_length=100)
    deadline: date | None = None
    priority: Literal["high", "medium", "low"] = "medium"
    evidence: str = Field(min_length=3, max_length=500)
    evidence_start: int = Field(ge=0)
    evidence_end: int = Field(gt=0)


class PlanIn(BaseModel):
    summary: str = Field(min_length=1, max_length=1000)
    items: list[PlanItem] = Field(max_length=30)


class TaskOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    note_id: int
    task: str
    owner: str | None
    deadline_text: str | None
    deadline: date | None
    priority: str
    evidence: str
    evidence_start: int
    evidence_end: int
    done: bool


class TaskWithNote(TaskOut):
    note_title: str


class TaskUpdate(BaseModel):
    done: bool


class NoteSummary(BaseModel):
    id: int
    title: str
    created_at: datetime
    updated_at: datetime
    has_plan: bool
    task_count: int
    done_count: int


class NoteDetail(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    body: str
    summary: str | None
    analyzed_at: datetime | None
    created_at: datetime
    updated_at: datetime
    tasks: list[TaskOut]
