import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlmodel import select

from app.core.deps import SessionDep, require_role
from app.models.user import Role, User
from app.schemas.user import UserRead

router = APIRouter(prefix="/users", tags=["users"])

AdminUser = Annotated[User, Depends(require_role(Role.admin))]


@router.get("/", response_model=list[UserRead])
async def list_users(
    session: SessionDep,
    _admin: AdminUser,
    offset: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
) -> list[User]:
    result = await session.exec(select(User).offset(offset).limit(limit))
    return list(result.all())


@router.get("/{user_id}", response_model=UserRead)
async def get_user(user_id: uuid.UUID, session: SessionDep, _admin: AdminUser) -> User:
    user = await session.get(User, user_id)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
        )
    return user


@router.patch("/{user_id}/role", response_model=UserRead)
async def set_user_role(
    user_id: uuid.UUID,
    role: Role,
    session: SessionDep,
    _admin: AdminUser,
) -> User:
    user = await session.get(User, user_id)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
        )
    user.role = role
    session.add(user)
    await session.commit()
    await session.refresh(user)
    return user
