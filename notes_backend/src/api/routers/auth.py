from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.api import schemas
from src.api.auth import create_access_token, hash_password, verify_password
from src.api.db import get_db
from src.api.models import User


router = APIRouter(prefix="/auth", tags=["auth"])


@router.post(
    "/register",
    response_model=schemas.UserResponse,
    summary="Register a new user",
    description="Create a new account using email and password.",
    status_code=status.HTTP_201_CREATED,
    operation_id="auth_register",
)
async def register(
    payload: schemas.RegisterRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> schemas.UserResponse:
    # PUBLIC_INTERFACE
    """Register a new user."""
    existing = await db.execute(select(User).where(User.email == payload.email))
    if existing.scalar_one_or_none() is not None:
        raise HTTPException(status_code=409, detail="Email already registered")

    user = User(email=str(payload.email).lower().strip(), password_hash=hash_password(payload.password))
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return schemas.UserResponse(id=user.id, email=user.email, created_at=user.created_at)


@router.post(
    "/login",
    response_model=schemas.TokenResponse,
    summary="Login",
    description="Authenticate using email/password and receive a JWT access token.",
    operation_id="auth_login",
)
async def login(
    payload: schemas.LoginRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> schemas.TokenResponse:
    # PUBLIC_INTERFACE
    """Login and return an access token."""
    result = await db.execute(select(User).where(User.email == str(payload.email).lower().strip()))
    user = result.scalar_one_or_none()
    if user is None or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password")

    expires = int((__import__("os").getenv("JWT_ACCESS_TOKEN_EXPIRE_MINUTES") or "60").strip())
    token = create_access_token(subject=user.id, expires_minutes=expires)
    return schemas.TokenResponse(access_token=token, token_type="bearer")
