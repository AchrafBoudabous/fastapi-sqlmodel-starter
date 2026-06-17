import uuid
from collections.abc import Callable
from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError
from sqlmodel.ext.asyncio.session import AsyncSession

from app.core.security import decode_token
from app.db.session import get_session
from app.models.user import Role, User

_bearer = HTTPBearer()

SessionDep = Annotated[AsyncSession, Depends(get_session)]


async def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(_bearer)],
    session: SessionDep,
) -> User:
    exc = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = decode_token(credentials.credentials)
        if payload.get("type") != "access":
            raise exc
        raw_id: str | None = payload.get("sub")
        if raw_id is None:
            raise exc
    except JWTError as err:
        raise exc from err

    try:
        user_id = uuid.UUID(raw_id)
    except ValueError as err:
        raise exc from err
    user = await session.get(User, user_id)
    if user is None or not user.is_active:
        raise exc
    return user


# Reusable type alias for injecting the authenticated user
CurrentUser = Annotated[User, Depends(get_current_user)]


def require_role(*roles: Role) -> Callable[..., User]:
    """Return a FastAPI dependency that enforces one of the given roles."""

    async def _check(current_user: CurrentUser) -> User:
        if current_user.role not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions",
            )
        return current_user

    return _check  # type: ignore[return-value]
