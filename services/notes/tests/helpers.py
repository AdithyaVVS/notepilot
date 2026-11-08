from tests.conftest import auth_headers

BODY = "Priya will send the budget by Friday.\nRahul will fix the login bug."


def item(
    task="Send the budget",
    evidence="Priya will send the budget by Friday.",
    **overrides,
):
    start = BODY.index(evidence)
    data = {
        "task": task,
        "owner": "Priya",
        "deadline_text": "by Friday",
        "deadline": "2026-11-13",
        "priority": "medium",
        "evidence": evidence,
        "evidence_start": start,
        "evidence_end": start + len(evidence),
    }
    data.update(overrides)
    return data


def second_item(**overrides):
    base = {
        "task": "Fix the login bug",
        "evidence": "Rahul will fix the login bug.",
        "owner": "Rahul",
        "deadline_text": None,
        "deadline": None,
        "priority": "high",
    }
    base.update(overrides)
    return item(**base)


def create_note(client, user=1, title="Weekly sync", body=BODY):
    response = client.post(
        "/notes", json={"title": title, "body": body}, headers=auth_headers(user)
    )
    assert response.status_code == 201
    return response.json()


def save_plan(client, note_id, items, user=1, summary="Sync summary"):
    return client.put(
        f"/notes/{note_id}/plan",
        json={"summary": summary, "items": items},
        headers=auth_headers(user),
    )
