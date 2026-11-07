from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_user
from app.models import User
from app.schemas import LoginIn, RegisterIn, TokenOut, UserOut
from app.security import (
    DUMMY_HASH,
    create_access_token,
    hash_password,
    verify_password,
)

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=UserOut, status_code=201)
def register(data: RegisterIn, db: Session = Depends(get_db)):
    if db.scalar(select(User).where(User.email == data.email)):
        raise HTTPException(status_code=409, detail="Email already registered")
    user = User(email=data.email, password_hash=hash_password(data.password))
    db.add(user)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="Email already registered")
    db.refresh(user)
    return user


@router.post("/login", response_model=TokenOut)
def login(data: LoginIn, db: Session = Depends(get_db)):
    user = db.scalar(select(User).where(User.email == data.email))
    password_ok = verify_password(
        data.password, user.password_hash if user else DUMMY_HASH
    )
    if user is None or not password_ok:
        raise HTTPException(status_code=401, detail="Incorrect email or password")
    return TokenOut(access_token=create_access_token(user.id, user.email))


@router.get("/me", response_model=UserOut)
def me(user: User = Depends(get_current_user)):
    return user
