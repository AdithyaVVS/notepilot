from app.llm.fake import FakeProvider
from app.main import app
from app.providers import get_provider
from tests.conftest import SAMPLE_NOTE, BrokenLLM, auth_headers


def test_analyze_requires_token(client):
    response = client.post("/ai/analyze", json={"note": SAMPLE_NOTE})
    assert response.status_code == 401


def test_analyze_returns_checked_items(client):
    app.dependency_overrides[get_provider] = lambda: FakeProvider()
    response = client.post(
        "/ai/analyze",
        json={"note": SAMPLE_NOTE, "today": "2026-11-04"},
        headers=auth_headers(),
    )
    assert response.status_code == 200
    items = response.json()["action_items"]
    assert [i["owner"] for i in items] == ["Priya", "Rahul", "Ananya"]
    assert items[0]["deadline"] == "2026-11-06"


def test_note_too_short_rejected(client):
    response = client.post("/ai/analyze", json={"note": "hi"}, headers=auth_headers())
    assert response.status_code == 422


def test_note_too_long_rejected(client):
    response = client.post(
        "/ai/analyze", json={"note": "x" * 6001}, headers=auth_headers()
    )
    assert response.status_code == 422


def test_provider_failure_returns_502(client):
    app.dependency_overrides[get_provider] = lambda: BrokenLLM()
    response = client.post(
        "/ai/analyze", json={"note": SAMPLE_NOTE}, headers=auth_headers()
    )
    assert response.status_code == 502
