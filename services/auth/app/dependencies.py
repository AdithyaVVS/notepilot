from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import User
from app.security import decode_access_token

bearer = HTTPBearer(auto_error=False)


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer),
    db: Session = Depends(get_db),
) -> User:
    unauthorized = HTTPException(status_code=401, detail="Not authenticated")
    if credentials is None:
        raise unauthorized
    payload = decode_access_token(credentials.credentials)
    if payload is None:
        raise unauthorized
    try:
        user_id = int(payload["sub"])
    except (KeyError, ValueError):
        raise unauthorized
    user = db.get(User, user_id)
    if user is None:
        raise unauthorized
    return user
