from datetime import datetime, timezone
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.auth import get_user_id
from app.database import get_db
from app.models import Note, Task
from app.schemas import (
    NoteCreate,
    NoteDetail,
    NoteSummary,
    PlanIn,
    TaskOut,
    TaskUpdate,
    TaskWithNote,
)

router = APIRouter()


def get_owned_note(db: Session, user_id: int, note_id: int) -> Note:
    # Filtering by user_id too means someone else's note looks the same as a missing one.
    note = db.scalar(select(Note).where(Note.id == note_id, Note.user_id == user_id))
    if note is None:
        raise HTTPException(status_code=404, detail="Note not found")
    return note


@router.post("/notes", response_model=NoteDetail, status_code=201)
def create_note(
    data: NoteCreate,
    user_id: int = Depends(get_user_id),
    db: Session = Depends(get_db),
):
    note = Note(user_id=user_id, title=data.title, body=data.body)
    db.add(note)
    db.commit()
    db.refresh(note)
    return NoteDetail.model_validate(note)


@router.get("/notes", response_model=list[NoteSummary])
def list_notes(user_id: int = Depends(get_user_id), db: Session = Depends(get_db)):
    counts = (
        select(
            Task.note_id.label("note_id"),
            func.count().label("total"),
            func.count().filter(Task.done.is_(True)).label("done"),
        )
        .where(Task.user_id == user_id)
        .group_by(Task.note_id)
        .subquery()
    )
    query = (
        select(
            Note,
            func.coalesce(counts.c.total, 0),
            func.coalesce(counts.c.done, 0),
        )
        .outerjoin(counts, counts.c.note_id == Note.id)
        .where(Note.user_id == user_id)
        .order_by(Note.updated_at.desc(), Note.id.desc())
        .limit(100)
    )
    return [
        NoteSummary(
            id=note.id,
            title=note.title,
            created_at=note.created_at,
            updated_at=note.updated_at,
            has_plan=note.summary is not None,
            task_count=total,
            done_count=done,
        )
        for note, total, done in db.execute(query).all()
    ]


@router.get("/notes/{note_id}", response_model=NoteDetail)
def get_note(
    note_id: int,
    user_id: int = Depends(get_user_id),
    db: Session = Depends(get_db),
):
    return NoteDetail.model_validate(get_owned_note(db, user_id, note_id))


@router.put("/notes/{note_id}", response_model=NoteDetail)
def update_note(
    note_id: int,
    data: NoteCreate,
    user_id: int = Depends(get_user_id),
    db: Session = Depends(get_db),
):
    note = get_owned_note(db, user_id, note_id)
    if data.body != note.body:
        # Saved task positions point into the old text, so the plan is no longer valid.
        note.tasks.clear()
        note.summary = None
        note.analyzed_at = None
    note.title = data.title
    note.body = data.body
    db.commit()
    db.refresh(note)
    return NoteDetail.model_validate(note)


@router.delete("/notes/{note_id}", status_code=204)
def delete_note(
    note_id: int,
    user_id: int = Depends(get_user_id),
    db: Session = Depends(get_db),
):
    note = get_owned_note(db, user_id, note_id)
    db.delete(note)
    db.commit()
    return Response(status_code=204)


@router.put("/notes/{note_id}/plan", response_model=NoteDetail)
def save_plan(
    note_id: int,
    data: PlanIn,
    user_id: int = Depends(get_user_id),
    db: Session = Depends(get_db),
):
    note = get_owned_note(db, user_id, note_id)
    for item in data.items:
        # Don't trust the browser: each quote must really be at that position in the note.
        if note.body[item.evidence_start : item.evidence_end] != item.evidence:
            raise HTTPException(
                status_code=422, detail="Evidence does not match the note text"
            )
    note.tasks.clear()
    db.flush()
    for position, item in enumerate(data.items):
        note.tasks.append(Task(user_id=user_id, position=position, **item.model_dump()))
    note.summary = data.summary
    note.analyzed_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(note)
    return NoteDetail.model_validate(note)


@router.get("/tasks", response_model=list[TaskWithNote])
def list_tasks(
    status: Literal["open", "done", "all"] = "open",
    user_id: int = Depends(get_user_id),
    db: Session = Depends(get_db),
):
    query = (
        select(Task, Note.title)
        .join(Note, Note.id == Task.note_id)
        .where(Task.user_id == user_id)
    )
    if status == "open":
        query = query.where(Task.done.is_(False))
    elif status == "done":
        query = query.where(Task.done.is_(True))
    query = query.order_by(Task.deadline.asc().nulls_last(), Task.id).limit(500)
    return [
        TaskWithNote(**TaskOut.model_validate(task).model_dump(), note_title=title)
        for task, title in db.execute(query).all()
    ]


@router.patch("/tasks/{task_id}", response_model=TaskOut)
def update_task(
    task_id: int,
    data: TaskUpdate,
    user_id: int = Depends(get_user_id),
    db: Session = Depends(get_db),
):
    task = db.scalar(select(Task).where(Task.id == task_id, Task.user_id == user_id))
    if task is None:
        raise HTTPException(status_code=404, detail="Task not found")
    task.done = data.done
    db.commit()
    db.refresh(task)
    return TaskOut.model_validate(task)
