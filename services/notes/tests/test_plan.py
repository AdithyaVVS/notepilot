from sqlalchemy import func, select

from app.models import Task
from tests.conftest import TestSession, auth_headers
from tests.helpers import BODY, create_note, item, save_plan, second_item


def test_save_plan_stores_tasks_in_order(client):
    note = create_note(client)
    response = save_plan(client, note["id"], [item(), second_item()])
    assert response.status_code == 200
    body = response.json()
    assert body["summary"] == "Sync summary"
    assert body["analyzed_at"] is not None
    assert [t["task"] for t in body["tasks"]] == ["Send the budget", "Fix the login bug"]
    assert body["tasks"][0]["deadline"] == "2026-11-13"
    assert body["tasks"][0]["done"] is False


def test_saving_again_replaces_tasks(client):
    note = create_note(client)
    save_plan(client, note["id"], [item(), second_item()])
    response = save_plan(client, note["id"], [item()])
    assert len(response.json()["tasks"]) == 1
    with TestSession() as db:
        assert db.scalar(select(func.count()).select_from(Task)) == 1


def test_evidence_that_does_not_match_is_rejected(client):
    note = create_note(client)
    wrong = item(evidence_start=5)
    assert save_plan(client, note["id"], [wrong]).status_code == 422
    saved = client.get(f"/notes/{note['id']}", headers=auth_headers()).json()
    assert saved["summary"] is None
    assert saved["tasks"] == []


def test_evidence_outside_the_note_is_rejected(client):
    note = create_note(client)
    outside = item(evidence_start=1000, evidence_end=1040)
    assert save_plan(client, note["id"], [outside]).status_code == 422


def test_editing_the_body_clears_the_plan(client):
    note = create_note(client)
    save_plan(client, note["id"], [item()])
    client.put(
        f"/notes/{note['id']}",
        json={"title": "Weekly sync", "body": "Completely new text for this note."},
        headers=auth_headers(),
    )
    saved = client.get(f"/notes/{note['id']}", headers=auth_headers()).json()
    assert saved["summary"] is None
    assert saved["tasks"] == []


def test_editing_only_the_title_keeps_the_plan(client):
    note = create_note(client)
    save_plan(client, note["id"], [item()])
    client.put(
        f"/notes/{note['id']}",
        json={"title": "New title", "body": BODY},
        headers=auth_headers(),
    )
    saved = client.get(f"/notes/{note['id']}", headers=auth_headers()).json()
    assert saved["title"] == "New title"
    assert saved["summary"] == "Sync summary"
    assert len(saved["tasks"]) == 1


def test_list_shows_task_counts(client):
    note = create_note(client)
    saved = save_plan(client, note["id"], [item(), second_item()]).json()
    client.patch(
        f"/tasks/{saved['tasks'][0]['id']}", json={"done": True}, headers=auth_headers()
    )
    [row] = client.get("/notes", headers=auth_headers()).json()
    assert row["has_plan"] is True
    assert row["task_count"] == 2
    assert row["done_count"] == 1
