import asyncio
import time
from contextlib import asynccontextmanager

import httpx
from fastapi import Depends, FastAPI, HTTPException, Request, Response
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.limiter import RateLimiter

_client = httpx.AsyncClient()
limiter = RateLimiter(limit=settings.auth_rate_limit)

PROXY_METHODS = ["GET", "POST", "PUT", "PATCH", "DELETE"]
FORWARD_HEADERS = {"authorization", "content-type", "accept"}
# public name -> (which service, path prefix inside that service)
ROUTES = {
    "auth": ("auth", "/auth"),
    "notes": ("notes", "/notes"),
    "tasks": ("notes", "/tasks"),
    "ai": ("ai", "/ai"),
}


async def get_client() -> httpx.AsyncClient:
    return _client


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield
    await _client.aclose()


app = FastAPI(title="NotePilot gateway", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_methods=PROXY_METHODS + ["OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
)


def service_urls() -> dict[str, str]:
    return {
        "auth": settings.auth_url.rstrip("/"),
        "notes": settings.notes_url.rstrip("/"),
        "ai": settings.ai_url.rstrip("/"),
    }


async def check(client: httpx.AsyncClient, name: str, url: str, timeout: float):
    try:
        response = await client.get(f"{url}/health", timeout=timeout)
        if response.status_code == 200:
            return name, response.json()
        return name, {"status": "error", "code": response.status_code}
    except Exception:
        return name, {"status": "unreachable"}


async def check_all(client: httpx.AsyncClient, timeout: float) -> dict:
    results = await asyncio.gather(
        *(check(client, name, url, timeout) for name, url in service_urls().items())
    )
    services = dict(results)
    all_ok = all(s.get("status") == "ok" for s in services.values())
    return {
        "status": "ok" if all_ok else "degraded",
        "gateway": "ok",
        "services": services,
    }


@app.get("/health")
def health():
    return {"status": "ok", "service": "gateway"}


@app.get("/api/health")
async def system_health(client: httpx.AsyncClient = Depends(get_client)):
    return await check_all(client, timeout=5)


@app.get("/api/warmup")
async def warmup(client: httpx.AsyncClient = Depends(get_client)):
    """Wakes every service at once. On free hosting each one can take up to a
    minute to start, and waking them together costs one wait instead of three."""
    started = time.monotonic()
    result = await check_all(client, timeout=55)
    result["elapsed_ms"] = int((time.monotonic() - started) * 1000)
    return result


async def forward(
    request: Request, service: str, path: str, client: httpx.AsyncClient
) -> Response:
    route = ROUTES.get(service)
    if route is None or ".." in path.split("/"):
        raise HTTPException(status_code=404, detail="Not found")
    target, prefix = route

    if service == "auth" and request.method == "POST" and path in {"login", "register"}:
        caller = request.client.host if request.client else "unknown"
        if not limiter.allow(caller):
            raise HTTPException(
                status_code=429,
                detail="Too many attempts. Please wait a minute and try again.",
            )

    body = await request.body()
    if len(body) > settings.max_body_bytes:
        raise HTTPException(status_code=413, detail="Request too large")

    url = service_urls()[target] + prefix + (f"/{path}" if path else "")
    headers = {
        key: value
        for key, value in request.headers.items()
        if key.lower() in FORWARD_HEADERS
    }
    timeout = 60.0 if service == "ai" else 30.0
    try:
        upstream = await client.request(
            request.method,
            url,
            params=list(request.query_params.multi_items()),
            content=body,
            headers=headers,
            timeout=timeout,
        )
    except httpx.TimeoutException:
        raise HTTPException(
            status_code=504, detail=f"The {target} service took too long to respond."
        )
    except httpx.HTTPError:
        raise HTTPException(
            status_code=503,
            detail=f"The {target} service is unavailable. "
            "It may be waking up, so try again in a moment.",
        )
    return Response(
        content=upstream.content,
        status_code=upstream.status_code,
        media_type=upstream.headers.get("content-type"),
    )


@app.api_route("/api/{service}", methods=PROXY_METHODS)
async def proxy_root(
    service: str, request: Request, client: httpx.AsyncClient = Depends(get_client)
):
    return await forward(request, service, "", client)


@app.api_route("/api/{service}/{path:path}", methods=PROXY_METHODS)
async def proxy_path(
    service: str,
    path: str,
    request: Request,
    client: httpx.AsyncClient = Depends(get_client),
):
    return await forward(request, service, path, client)
