import httpx


def service_health(request):
    name = request.url.host
    return httpx.Response(200, json={"status": "ok", "service": name})


def test_health_reports_all_services(client, upstream):
    upstream.respond = service_health
    body = client.get("/api/health").json()
    assert body["status"] == "ok"
    assert set(body["services"]) == {"auth", "notes", "ai"}


def test_health_reports_degraded_when_one_is_down(client, upstream):
    def respond(request):
        if request.url.host == "notes":
            raise httpx.ConnectError("down")
        return service_health(request)

    upstream.respond = respond
    body = client.get("/api/health").json()
    assert body["status"] == "degraded"
    assert body["services"]["notes"] == {"status": "unreachable"}
    assert body["services"]["auth"]["status"] == "ok"


def test_warmup_wakes_all_services_and_reports_time(client, upstream):
    upstream.respond = service_health
    body = client.get("/api/warmup").json()
    assert body["status"] == "ok"
    assert isinstance(body["elapsed_ms"], int)
    assert sorted(r.url.host for r in upstream.requests) == ["ai", "auth", "notes"]


def test_login_and_register_are_rate_limited(client, upstream):
    for _ in range(10):
        assert client.post("/api/auth/login", json={}).status_code == 200
    blocked = client.post("/api/auth/login", json={})
    assert blocked.status_code == 429
    assert client.post("/api/auth/register", json={}).status_code == 429
    assert len(upstream.requests) == 10
    # other endpoints are not affected
    assert client.get("/api/notes").status_code == 200


def test_cors_allows_the_frontend_origin(client):
    response = client.options(
        "/api/notes",
        headers={
            "Origin": "http://localhost:5173",
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "authorization,content-type",
        },
    )
    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "http://localhost:5173"


def test_cors_blocks_other_origins(client):
    response = client.options(
        "/api/notes",
        headers={
            "Origin": "http://evil.example",
            "Access-Control-Request-Method": "POST",
        },
    )
    assert "access-control-allow-origin" not in response.headers


def test_warmup_keeps_asking_while_a_service_wakes_up(client, upstream, monkeypatch):
    monkeypatch.setattr("app.main.RETRY_DELAY", 0.0)
    attempts = {"notes": 0}

    def respond(request):
        if request.url.host == "notes":
            attempts["notes"] += 1
            if attempts["notes"] < 4:
                return httpx.Response(502)
        return service_health(request)

    upstream.respond = respond
    body = client.get("/api/warmup").json()
    assert body["status"] == "ok"
    assert attempts["notes"] == 4


def test_health_does_not_wait_for_a_sleeping_service(client, upstream):
    upstream.respond = lambda request: httpx.Response(502)
    body = client.get("/api/health").json()
    assert body["status"] == "degraded"
    assert body["services"]["auth"] == {"status": "error", "code": 502}
    assert len(upstream.requests) == 3
