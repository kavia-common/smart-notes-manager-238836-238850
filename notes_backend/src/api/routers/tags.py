from typing import Annotated, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.api import schemas
from src.api.db import get_db
from src.api.deps import get_current_user
from src.api.models import Tag, User


router = APIRouter(prefix="/tags", tags=["tags"])


@router.get(
    "",
    response_model=list[schemas.TagResponse],
    summary="List tags",
    description="List tags for the current user (optionally filter by name prefix).",
    operation_id="tags_list",
)
async def list_tags(
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    prefix: Annotated[Optional[str], Query(description="Optional name prefix filter.")] = None,
) -> list[schemas.TagResponse]:
    # PUBLIC_INTERFACE
    """List tags for the authenticated user."""
    stmt = select(Tag).where(Tag.owner_id == user.id).order_by(func.lower(Tag.name))
    if prefix:
        stmt = stmt.where(Tag.name.ilike(f"{prefix.strip()}%"))
    res = await db.execute(stmt)
    tags = list(res.scalars().all())
    return [schemas.TagResponse(id=t.id, name=t.name, created_at=t.created_at) for t in tags]


@router.delete(
    "/{tag_id}",
    response_model=schemas.APIMessage,
    summary="Delete tag",
    description="Delete a tag by id. Notes will be unlinked automatically.",
    operation_id="tags_delete",
)
async def delete_tag(
    tag_id: UUID,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> schemas.APIMessage:
    # PUBLIC_INTERFACE
    """Delete tag for the authenticated user."""
    res = await db.execute(select(Tag).where(and_(Tag.id == tag_id, Tag.owner_id == user.id)))
    tag = res.scalar_one_or_none()
    if tag is None:
        raise HTTPException(status_code=404, detail="Tag not found")
    await db.delete(tag)
    await db.commit()
    return schemas.APIMessage(message="Deleted")
