import httpx
import pytest
from fastapi.testclient import TestClient

from app.main import app, get_client, limiter


class Upstream:
    """Stands in for the other services: records requests, answers as scripted."""

    def __init__(self):
        self.requests = []
        self.respond = lambda request: httpx.Response(200, json={"ok": True})

    def __call__(self, request):
        self.requests.append(request)
        return self.respond(request)


@pytest.fixture
def upstream():
    return Upstream()


@pytest.fixture
def client(upstream):
    fake = httpx.AsyncClient(transport=httpx.MockTransport(upstream))

    async def override_get_client():
        return fake

    app.dependency_overrides[get_client] = override_get_client
    limiter.reset()
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()
