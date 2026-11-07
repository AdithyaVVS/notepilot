import asyncio

import httpx
from fastapi import FastAPI

from app.config import settings

app = FastAPI(title="NotePilot gateway")

SERVICES = {
    "auth": settings.auth_url,
    "notes": settings.notes_url,
    "ai": settings.ai_url,
}


async def check(client: httpx.AsyncClient, name: str, url: str):
    try:
        response = await client.get(f"{url}/health", timeout=5)
        if response.status_code == 200:
            return name, response.json()
        return name, {"status": "error", "code": response.status_code}
    except Exception:
        return name, {"status": "unreachable"}


@app.get("/health")
def health():
    return {"status": "ok", "service": "gateway"}


@app.get("/api/health")
async def system_health():
    async with httpx.AsyncClient() as client:
        results = await asyncio.gather(
            *(check(client, name, url) for name, url in SERVICES.items())
        )
    services = dict(results)
    all_ok = all(s.get("status") == "ok" for s in services.values())
    return {
        "status": "ok" if all_ok else "degraded",
        "gateway": "ok",
        "services": services,
    }
