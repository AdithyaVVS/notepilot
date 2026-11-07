from datetime import datetime, timedelta, timezone

import jwt
from sqlalchemy import select

from app.config import settings
from app.models import User
from tests.conftest import TestSession

EMAIL = "me@example.com"
PASSWORD = "password123"


def register(client, email=EMAIL, password=PASSWORD):
    return client.post("/auth/register", json={"email": email, "password": password})


def login(client, email=EMAIL, password=PASSWORD):
    return client.post("/auth/login", json={"email": email, "password": password})


def bearer(token):
    return {"Authorization": f"Bearer {token}"}


def make_token(sub, secret=None, expires_in=timedelta(hours=1)):
    expires = datetime.now(timezone.utc) + expires_in
    return jwt.encode(
        {"sub": sub, "exp": expires}, secret or settings.jwt_secret, algorithm="HS256"
    )


def test_register_returns_user_without_password(client):
    response = register(client)
    assert response.status_code == 201
    body = response.json()
    assert body["email"] == EMAIL
    assert "password" not in body
    assert "password_hash" not in body


def test_password_is_stored_hashed(client):
    register(client)
    with TestSession() as db:
        user = db.scalar(select(User).where(User.email == EMAIL))
    assert user.password_hash != PASSWORD
    assert user.password_hash.startswith("$2")


def test_duplicate_email_rejected_case_insensitively(client):
    assert register(client).status_code == 201
    assert register(client, email="ME@Example.com").status_code == 409


def test_short_password_rejected(client):
    assert register(client, password="short").status_code == 422


def test_invalid_email_rejected(client):
    assert register(client, email="not-an-email").status_code == 422


def test_login_returns_token(client):
    register(client)
    response = login(client)
    assert response.status_code == 200
    assert response.json()["access_token"]
    assert response.json()["token_type"] == "bearer"


def test_wrong_password_rejected(client):
    register(client)
    assert login(client, password="wrong-password").status_code == 401


def test_unknown_email_gets_same_error(client):
    register(client)
    wrong_password = login(client, password="wrong-password")
    unknown_email = login(client, email="nobody@example.com")
    assert unknown_email.status_code == 401
    assert unknown_email.json() == wrong_password.json()


def test_me_returns_current_user(client):
    register(client)
    token = login(client).json()["access_token"]
    response = client.get("/auth/me", headers=bearer(token))
    assert response.status_code == 200
    assert response.json()["email"] == EMAIL


def test_me_requires_token(client):
    assert client.get("/auth/me").status_code == 401


def test_me_rejects_garbage_token(client):
    assert client.get("/auth/me", headers=bearer("garbage")).status_code == 401


def test_me_rejects_expired_token(client):
    register(client)
    token = make_token("1", expires_in=timedelta(hours=-1))
    assert client.get("/auth/me", headers=bearer(token)).status_code == 401


def test_me_rejects_token_signed_with_other_secret(client):
    register(client)
    token = make_token("1", secret="some-other-secret-some-other-secret-1234")
    assert client.get("/auth/me", headers=bearer(token)).status_code == 401


def test_me_rejects_token_for_unknown_user(client):
    token = make_token("999999")
    assert client.get("/auth/me", headers=bearer(token)).status_code == 401
