import re

from pydantic import BaseModel, ConfigDict, field_validator

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


class Credentials(BaseModel):
    email: str
    password: str

    @field_validator("email")
    @classmethod
    def check_email(cls, value: str) -> str:
        value = value.strip().lower()
        if len(value) > 255 or not EMAIL_RE.match(value):
            raise ValueError("Enter a valid email address")
        return value


class RegisterIn(Credentials):
    @field_validator("password")
    @classmethod
    def check_password(cls, value: str) -> str:
        if len(value) < 8:
            raise ValueError("Password must be at least 8 characters")
        if len(value.encode()) > 72:
            raise ValueError("Password is too long (72 bytes maximum)")
        return value


class LoginIn(Credentials):
    pass


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    email: str
