from datetime import UTC, datetime, timedelta
from typing import Any

import bcrypt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.config import get_settings
from backend.core.database import get_session
from backend.models.user import User

settings = get_settings()

bearer_scheme = HTTPBearer()

_BCRYPT_MAX_BYTES = 72


def _password_bytes(password: str) -> bytes:
    return password.encode("utf-8")[:_BCRYPT_MAX_BYTES]


def hash_password(password: str) -> str:
    """Захэшировать пароль"""
    return bcrypt.hashpw(_password_bytes(password), bcrypt.gensalt()).decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Проверить пароль против хэша"""
    try:
        return bcrypt.checkpw(
            _password_bytes(plain_password),
            hashed_password.encode("utf-8"),
        )
    
    except ValueError:
        return False


def create_access_token(
    subject: str | int,
    expires_delta: timedelta | None = None,
) -> str:
    """Создать JWT access-токен"""
    expire = datetime.now(UTC) + (
        expires_delta
        or timedelta(minutes=settings.access_token_expire_minutes)
    )

    payload = {"sub": str(subject), "exp": expire}

    return jwt.encode(payload, settings.secret_key, algorithm=settings.algorithm)


def decode_token(token: str) -> dict[str, Any]:
    """Декодировать и провалидировать JWT (подпись + срок)"""
    return jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])


_credentials_exception = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="Не удалось проверить учётные данные",
    headers={"WWW-Authenticate": "Bearer"},
)


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    session: AsyncSession = Depends(get_session),
) -> User:
    try:
        payload = decode_token(credentials.credentials)
        subject = payload.get("sub")

        if subject is None:
            raise _credentials_exception
        
        user_id = int(subject)

    except (JWTError, ValueError):
        raise _credentials_exception

    user = await session.get(User, user_id)
    
    if user is None:
        raise _credentials_exception
    return user
