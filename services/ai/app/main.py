from fastapi import FastAPI
from sqlalchemy import text

from app.database import engine
from app.routes import router

app = FastAPI(title="NotePilot AI service")
app.include_router(router)


@app.get("/health")
def health():
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
        database = "ok"
    except Exception:
        database = "unreachable"
    return {
        "status": "ok" if database == "ok" else "degraded",
        "service": "ai",
        "database": database,
    }
