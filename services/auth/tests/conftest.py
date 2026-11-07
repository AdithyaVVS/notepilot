import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.config import settings
from app.database import get_db
from app.main import app
from app.models import Base

TEST_URL = settings.database_url.rsplit("/", 1)[0] + "/notepilot_auth_test"
assert TEST_URL.endswith("_test"), "tests must never run against the real database"

test_engine = create_engine(TEST_URL)
TestSession = sessionmaker(bind=test_engine, autoflush=False)


@pytest.fixture(autouse=True)
def fresh_database():
    Base.metadata.drop_all(test_engine)
    Base.metadata.create_all(test_engine)
    yield


@pytest.fixture
def client():
    def override_get_db():
        db = TestSession()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()
