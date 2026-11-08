from sqlalchemy import func, select

from app.models import Task
from tests.conftest import TestSession, auth_headers
from tests.helpers import BODY, create_note, item, save_plan


def test_create_note(client):
    note = create_note(client)
    assert note["title"] == "Weekly sync"
    assert note["body"] == BODY
    assert note["summary"] is None
    assert note["tasks"] == []


def test_create_requires_token(client):
    response = client.post("/notes", json={"title": "a", "body": "b"})
    assert response.status_code == 401


def test_blank_title_or_body_rejected(client):
    headers = auth_headers()
    blank_title = client.post(
        "/notes", json={"title": "   ", "body": BODY}, headers=headers
    )
    blank_body = client.post(
        "/notes", json={"title": "Ok", "body": "   "}, headers=headers
    )
    assert blank_title.status_code == 422
    assert blank_body.status_code == 422


def test_body_too_long_rejected(client):
    response = client.post(
        "/notes", json={"title": "Big", "body": "x" * 6001}, headers=auth_headers()
    )
    assert response.status_code == 422


def test_title_is_trimmed_but_body_is_untouched(client):
    note = create_note(client, title="  Weekly sync  ", body="  indented note text  ")
    assert note["title"] == "Weekly sync"
    assert note["body"] == "  indented note text  "


def test_list_returns_newest_first(client):
    first = create_note(client, title="First")
    second = create_note(client, title="Second")
    response = client.get("/notes", headers=auth_headers())
    assert [n["id"] for n in response.json()] == [second["id"], first["id"]]
    assert response.json()[0]["has_plan"] is False


def test_get_note_returns_detail(client):
    note = create_note(client)
    response = client.get(f"/notes/{note['id']}", headers=auth_headers())
    assert response.status_code == 200
    assert response.json()["body"] == BODY


def test_update_note(client):
    note = create_note(client)
    response = client.put(
        f"/notes/{note['id']}",
        json={"title": "Renamed", "body": "A different body of text."},
        headers=auth_headers(),
    )
    assert response.status_code == 200
    assert response.json()["title"] == "Renamed"
    assert response.json()["body"] == "A different body of text."


def test_delete_note(client):
    note = create_note(client)
    assert client.delete(f"/notes/{note['id']}", headers=auth_headers()).status_code == 204
    assert client.get(f"/notes/{note['id']}", headers=auth_headers()).status_code == 404


def test_delete_cascades_to_tasks(client):
    note = create_note(client)
    save_plan(client, note["id"], [item()])
    client.delete(f"/notes/{note['id']}", headers=auth_headers())
    with TestSession() as db:
        assert db.scalar(select(func.count()).select_from(Task)) == 0


def test_unknown_note_returns_404(client):
    assert client.get("/notes/999", headers=auth_headers()).status_code == 404
