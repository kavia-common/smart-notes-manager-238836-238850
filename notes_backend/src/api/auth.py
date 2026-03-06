import os
from datetime import datetime, timedelta, timezone
from typing import Any, Optional
from uuid import UUID

from jose import JWTError, jwt
from passlib.context import CryptContext


_pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def _require_env(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise RuntimeError(
            f"Missing required environment variable: {name}. "
            f"Set it in the container environment (.env)."
        )
    return value


def hash_password(password: str) -> str:
    """Hash a plaintext password."""
    return _pwd_context.hash(password)


def verify_password(plain_password: str, password_hash: str) -> bool:
    """Verify a password against its hash."""
    return _pwd_context.verify(plain_password, password_hash)


def create_access_token(*, subject: UUID, expires_minutes: int) -> str:
    """Create a JWT access token for the given subject (user id)."""
    secret_key = _require_env("JWT_SECRET_KEY")
    algorithm = os.getenv("JWT_ALGORITHM", "HS256")
    now = datetime.now(timezone.utc)
    expire = now + timedelta(minutes=expires_minutes)

    payload: dict[str, Any] = {
        "sub": str(subject),
        "iat": int(now.timestamp()),
        "exp": int(expire.timestamp()),
    }
    return jwt.encode(payload, secret_key, algorithm=algorithm)


def decode_token(token: str) -> Optional[UUID]:
    """Decode a JWT and return the subject user id if valid, else None."""
    secret_key = _require_env("JWT_SECRET_KEY")
    algorithm = os.getenv("JWT_ALGORITHM", "HS256")
    try:
        payload = jwt.decode(token, secret_key, algorithms=[algorithm])
        sub = payload.get("sub")
        if not sub:
            return None
        return UUID(str(sub))
    except (JWTError, ValueError):
        return None
