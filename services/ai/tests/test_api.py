from datetime import datetime, timedelta, timezone

import jwt
from fastapi.testclient import TestClient

from app.config import settings
from app.llm.base import ProviderError
from app.main import app
from app.providers import get_provider
from tests.conftest import SAMPLE_NOTE

client = TestClient(app)


def auth_headers():
    expires = datetime.now(timezone.utc) + timedelta(hours=1)
    token = jwt.encode(
        {"sub": "1", "exp": expires}, settings.jwt_secret, algorithm="HS256"
    )
    return {"Authorization": f"Bearer {token}"}


class BrokenLLM:
    def generate(self, instructions, content):
        raise ProviderError("provider is down")


def test_analyze_requires_token():
    response = client.post("/ai/analyze", json={"note": SAMPLE_NOTE})
    assert response.status_code == 401


def test_analyze_with_fake_provider():
    response = client.post(
        "/ai/analyze",
        json={"note": SAMPLE_NOTE, "today": "2026-11-04"},
        headers=auth_headers(),
    )
    assert response.status_code == 200
    items = response.json()["action_items"]
    assert [i["owner"] for i in items] == ["Priya", "Rahul", "Ananya"]
    assert items[0]["deadline"] == "2026-11-06"


def test_note_too_short_rejected():
    response = client.post("/ai/analyze", json={"note": "hi"}, headers=auth_headers())
    assert response.status_code == 422


def test_note_too_long_rejected():
    response = client.post(
        "/ai/analyze", json={"note": "x" * 6001}, headers=auth_headers()
    )
    assert response.status_code == 422


def test_provider_failure_returns_502():
    app.dependency_overrides[get_provider] = lambda: BrokenLLM()
    try:
        response = client.post(
            "/ai/analyze", json={"note": SAMPLE_NOTE}, headers=auth_headers()
        )
    finally:
        app.dependency_overrides.clear()
    assert response.status_code == 502
