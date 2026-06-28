from datetime import datetime, timedelta, timezone

import bcrypt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import get_db

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def verify_password(plain: str, hashed: str) -> bool:
    return bcrypt.checkpw(plain.encode(), hashed.encode())


def create_access_token(user_id: str, email: str, is_guest: bool = False) -> str:
    minutes = settings.guest_session_minutes if is_guest else settings.jwt_expire_minutes
    expire = datetime.now(timezone.utc) + timedelta(minutes=minutes)
    payload = {"sub": user_id, "email": email, "exp": expire, "is_guest": is_guest}
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def decode_user_id(token: str) -> str | None:
    try:
        payload = jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
        return payload.get("sub")
    except JWTError:
        return None


async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db),
):
    from app.models.user import User

    credentials_exc = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or expired token",
        headers={"WWW-Authenticate": "Bearer"},
    )
    user_id = decode_user_id(token)
    if not user_id:
        raise credentials_exc

    user = await db.get(User, user_id)
    if not user or not user.is_active:
        raise credentials_exc

    if user.is_guest and user.guest_expires_at:
        if datetime.now(timezone.utc) > user.guest_expires_at.replace(tzinfo=timezone.utc):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Guest session expired",
                headers={"WWW-Authenticate": "Bearer"},
            )

    return user
