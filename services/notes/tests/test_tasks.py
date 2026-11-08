from tests.conftest import auth_headers
from tests.helpers import create_note, item, save_plan, second_item


def test_toggling_done_moves_a_task_between_lists(client):
    note = create_note(client)
    saved = save_plan(client, note["id"], [item(), second_item()]).json()
    task_id = saved["tasks"][0]["id"]

    toggled = client.patch(
        f"/tasks/{task_id}", json={"done": True}, headers=auth_headers()
    )
    assert toggled.status_code == 200
    assert toggled.json()["done"] is True

    open_tasks = client.get("/tasks", headers=auth_headers()).json()
    done_tasks = client.get("/tasks?status=done", headers=auth_headers()).json()
    all_tasks = client.get("/tasks?status=all", headers=auth_headers()).json()
    assert len(open_tasks) == 1
    assert [t["id"] for t in done_tasks] == [task_id]
    assert len(all_tasks) == 2


def test_open_tasks_are_sorted_by_deadline_with_note_title(client):
    first = create_note(client, title="First note")
    save_plan(client, first["id"], [second_item(), item()])  # no deadline, then 13 Nov
    second = create_note(client, title="Second note")
    save_plan(client, second["id"], [item(deadline="2026-11-10")])

    tasks = client.get("/tasks", headers=auth_headers()).json()
    assert [t["deadline"] for t in tasks] == ["2026-11-10", "2026-11-13", None]
    assert tasks[0]["note_title"] == "Second note"
    assert tasks[1]["note_title"] == "First note"


def test_invalid_status_is_rejected(client):
    response = client.get("/tasks?status=bogus", headers=auth_headers())
    assert response.status_code == 422


def test_patch_requires_the_done_field(client):
    note = create_note(client)
    saved = save_plan(client, note["id"], [item()]).json()
    response = client.patch(
        f"/tasks/{saved['tasks'][0]['id']}", json={}, headers=auth_headers()
    )
    assert response.status_code == 422
