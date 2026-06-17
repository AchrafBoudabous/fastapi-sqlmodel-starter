import uuid

from fastapi import APIRouter, HTTPException, Query, status
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.core.deps import CurrentUser, SessionDep
from app.models.item import Item
from app.models.user import Role, User
from app.schemas.item import ItemCreate, ItemRead, ItemUpdate

router = APIRouter(prefix="/items", tags=["items"])


async def _get_item_or_404(
    item_id: uuid.UUID,
    session: AsyncSession,
    current_user: User,
) -> Item:
    """Fetch an item by id, enforcing ownership for non-admins.

    Returns 404 (not 403) for unauthorized access to avoid leaking resource existence.
    """
    item = await session.get(Item, item_id)
    if item is None or (
        current_user.role != Role.admin and item.owner_id != current_user.id
    ):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Item not found"
        )
    return item


@router.post("/", response_model=ItemRead, status_code=status.HTTP_201_CREATED)
async def create_item(
    body: ItemCreate, session: SessionDep, current_user: CurrentUser
) -> Item:
    item = Item(**body.model_dump(), owner_id=current_user.id)
    session.add(item)
    await session.commit()
    await session.refresh(item)
    return item


@router.get("/", response_model=list[ItemRead])
async def list_items(
    session: SessionDep,
    current_user: CurrentUser,
    offset: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
) -> list[Item]:
    stmt = select(Item)
    if current_user.role != Role.admin:
        stmt = stmt.where(Item.owner_id == current_user.id)
    result = await session.exec(stmt.offset(offset).limit(limit))
    return list(result.all())


@router.get("/{item_id}", response_model=ItemRead)
async def get_item(
    item_id: uuid.UUID, session: SessionDep, current_user: CurrentUser
) -> Item:
    return await _get_item_or_404(item_id, session, current_user)


@router.put("/{item_id}", response_model=ItemRead)
async def update_item(
    item_id: uuid.UUID,
    body: ItemUpdate,
    session: SessionDep,
    current_user: CurrentUser,
) -> Item:
    item = await _get_item_or_404(item_id, session, current_user)
    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(item, field, value)
    session.add(item)
    await session.commit()
    await session.refresh(item)
    return item


@router.delete("/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_item(
    item_id: uuid.UUID,
    session: SessionDep,
    current_user: CurrentUser,
) -> None:
    item = await _get_item_or_404(item_id, session, current_user)
    await session.delete(item)
    await session.commit()
