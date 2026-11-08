import json

import httpx
import pytest


def test_forwards_request_and_query_string(client, upstream):
    response = client.get("/api/notes?limit=5")
    assert response.status_code == 200
    assert response.json() == {"ok": True}
    assert str(upstream.requests[0].url) == "http://notes:8000/notes?limit=5"


@pytest.mark.parametrize(
    "method, path, expected",
    [
        ("POST", "/api/auth/login", "http://auth:8000/auth/login"),
        ("GET", "/api/auth/me", "http://auth:8000/auth/me"),
        ("PUT", "/api/notes/5/plan", "http://notes:8000/notes/5/plan"),
        ("PATCH", "/api/tasks/3", "http://notes:8000/tasks/3"),
        ("GET", "/api/tasks", "http://notes:8000/tasks"),
        ("POST", "/api/ai/analyze", "http://ai:8000/ai/analyze"),
        ("GET", "/api/ai/usage", "http://ai:8000/ai/usage"),
    ],
)
def test_routes_to_the_right_service(client, upstream, method, path, expected):
    client.request(method, path, json={} if method != "GET" else None)
    assert str(upstream.requests[0].url) == expected


def test_forwards_token_and_body_but_not_other_headers(client, upstream):
    client.post(
        "/api/ai/analyze",
        json={"note": "hello"},
        headers={"Authorization": "Bearer abc", "X-Secret": "nope"},
    )
    seen = upstream.requests[0]
    assert seen.headers["authorization"] == "Bearer abc"
    assert "x-secret" not in seen.headers
    assert json.loads(seen.content) == {"note": "hello"}


def test_passes_through_upstream_errors(client, upstream):
    upstream.respond = lambda request: httpx.Response(
        404, json={"detail": "Note not found"}
    )
    response = client.get("/api/notes/99")
    assert response.status_code == 404
    assert response.json() == {"detail": "Note not found"}


def test_passes_through_empty_204(client, upstream):
    upstream.respond = lambda request: httpx.Response(204)
    response = client.delete("/api/notes/1")
    assert response.status_code == 204
    assert response.content == b""


def test_unknown_service_is_404_and_not_forwarded(client, upstream):
    assert client.get("/api/secret/anything").status_code == 404
    assert upstream.requests == []


def test_path_traversal_is_rejected(client, upstream):
    assert client.get("/api/notes/%2e%2e/%2e%2e/health").status_code == 404
    assert upstream.requests == []


def test_unreachable_service_returns_503(client, upstream):
    def refuse(request):
        raise httpx.ConnectError("refused")

    upstream.respond = refuse
    response = client.get("/api/notes")
    assert response.status_code == 503
    assert "notes" in response.json()["detail"]


def test_slow_service_returns_504(client, upstream):
    def too_slow(request):
        raise httpx.ReadTimeout("slow")

    upstream.respond = too_slow
    assert client.get("/api/ai/usage").status_code == 504


def test_oversized_body_is_rejected(client, upstream):
    response = client.post("/api/ai/analyze", content=b"x" * 70000)
    assert response.status_code == 413
    assert upstream.requests == []
