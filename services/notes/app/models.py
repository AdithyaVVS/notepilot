from datetime import date, datetime

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    String,
    Text,
    func,
    text,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class Note(Base):
    __tablename__ = "notes"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(index=True)
    title: Mapped[str] = mapped_column(String(200))
    body: Mapped[str] = mapped_column(Text)
    summary: Mapped[str | None] = mapped_column(Text, default=None)
    analyzed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), default=None
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    tasks: Mapped[list["Task"]] = relationship(
        back_populates="note",
        cascade="all, delete-orphan",
        passive_deletes=True,
        order_by="Task.position",
    )


class Task(Base):
    __tablename__ = "tasks"
    __table_args__ = (
        CheckConstraint(
            "priority IN ('high', 'medium', 'low')", name="ck_tasks_priority"
        ),
        CheckConstraint("evidence_end > evidence_start", name="ck_tasks_evidence_span"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    note_id: Mapped[int] = mapped_column(
        ForeignKey("notes.id", ondelete="CASCADE"), index=True
    )
    user_id: Mapped[int] = mapped_column(index=True)
    position: Mapped[int]
    task: Mapped[str] = mapped_column(String(300))
    owner: Mapped[str | None] = mapped_column(String(100))
    deadline_text: Mapped[str | None] = mapped_column(String(100))
    deadline: Mapped[date | None] = mapped_column(Date)
    priority: Mapped[str] = mapped_column(String(10))
    evidence: Mapped[str] = mapped_column(String(500))
    evidence_start: Mapped[int]
    evidence_end: Mapped[int]
    done: Mapped[bool] = mapped_column(
        Boolean, default=False, server_default=text("false")
    )

    note: Mapped[Note] = relationship(back_populates="tasks")
