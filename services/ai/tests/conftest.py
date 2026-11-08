from datetime import datetime, timedelta, timezone

import jwt
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.config import settings
from app.database import get_db
from app.llm.base import ProviderError
from app.main import app
from app.models import Base
from app.providers import get_provider

TEST_URL = settings.database_url.rsplit("/", 1)[0] + "/notepilot_ai_test"
assert TEST_URL.endswith("_test"), "tests must never run against the real database"

test_engine = create_engine(TEST_URL)
TestSession = sessionmaker(bind=test_engine, autoflush=False)

SAMPLE_NOTE = (
    "Weekly sync, 4 Nov\n"
    "- Priya will send the revised budget to finance by Friday.\n"
    "- Rahul needs to fix the login bug ASAP, before next week.\n"
    "We decided to postpone the launch.\n"
    "- Ananya should book the venue by 20 Nov."
)


class ScriptedLLM:
    """Returns pre-written replies in order and records what it was asked."""

    def __init__(self, replies):
        self.replies = list(replies)
        self.calls = []

    def generate(self, instructions, content):
        self.calls.append({"instructions": instructions, "content": content})
        if not self.replies:
            raise AssertionError("LLM was called more times than scripted")
        return self.replies.pop(0)


class BrokenLLM:
    def generate(self, instructions, content):
        raise ProviderError("provider is down")


def auth_headers(user_id=1):
    expires = datetime.now(timezone.utc) + timedelta(hours=1)
    token = jwt.encode(
        {"sub": str(user_id), "exp": expires}, settings.jwt_secret, algorithm="HS256"
    )
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def llm():
    return ScriptedLLM([])


@pytest.fixture
def client(llm):
    Base.metadata.drop_all(test_engine)
    Base.metadata.create_all(test_engine)

    def override_get_db():
        db = TestSession()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_provider] = lambda: llm
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()
