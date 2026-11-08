import pytest

from tests.conftest import auth_headers
from tests.helpers import create_note, item, save_plan


def owner_note_with_task(client):
    note = create_note(client, user=1)
    saved = save_plan(client, note["id"], [item()], user=1).json()
    return note["id"], saved["tasks"][0]["id"]


@pytest.mark.parametrize(
    "method, suffix, body",
    [
        ("get", "", None),
        ("put", "", {"title": "Hacked", "body": "changed by someone else"}),
        ("delete", "", None),
        ("put", "/plan", {"summary": "x", "items": []}),
    ],
)
def test_other_user_cannot_touch_a_note(client, method, suffix, body):
    note_id, _ = owner_note_with_task(client)
    kwargs = {"headers": auth_headers(2)}
    if body is not None:
        kwargs["json"] = body
    response = getattr(client, method)(f"/notes/{note_id}{suffix}", **kwargs)
    assert response.status_code == 404

    intact = client.get(f"/notes/{note_id}", headers=auth_headers(1)).json()
    assert intact["title"] == "Weekly sync"
    assert len(intact["tasks"]) == 1


def test_other_user_cannot_update_a_task(client):
    note_id, task_id = owner_note_with_task(client)
    response = client.patch(
        f"/tasks/{task_id}", json={"done": True}, headers=auth_headers(2)
    )
    assert response.status_code == 404
    intact = client.get(f"/notes/{note_id}", headers=auth_headers(1)).json()
    assert intact["tasks"][0]["done"] is False


def test_other_user_sees_nothing_in_lists(client):
    owner_note_with_task(client)
    assert client.get("/notes", headers=auth_headers(2)).json() == []
    assert client.get("/tasks?status=all", headers=auth_headers(2)).json() == []


@pytest.mark.parametrize(
    "method, path, body",
    [
        ("get", "/notes", None),
        ("post", "/notes", {"title": "a", "body": "b"}),
        ("get", "/notes/1", None),
        ("put", "/notes/1", {"title": "a", "body": "b"}),
        ("delete", "/notes/1", None),
        ("put", "/notes/1/plan", {"summary": "s", "items": []}),
        ("get", "/tasks", None),
        ("patch", "/tasks/1", {"done": True}),
    ],
)
def test_every_endpoint_requires_a_token(client, method, path, body):
    response = client.request(method.upper(), path, json=body)
    assert response.status_code == 401
