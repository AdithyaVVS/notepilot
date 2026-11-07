import jwt
from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.config import settings

bearer = HTTPBearer(auto_error=False)


def get_user_id(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer),
) -> int:
    unauthorized = HTTPException(status_code=401, detail="Not authenticated")
    if credentials is None:
        raise unauthorized
    try:
        payload = jwt.decode(
            credentials.credentials,
            settings.jwt_secret,
            algorithms=["HS256"],
            options={"require": ["exp", "sub"]},
        )
        return int(payload["sub"])
    except (jwt.PyJWTError, ValueError):
        raise unauthorized
