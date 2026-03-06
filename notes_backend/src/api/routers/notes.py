from __future__ import annotations

from typing import Annotated, List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.api import schemas
from src.api.db import get_db
from src.api.deps import get_current_user
from src.api.models import Note, Tag, User


router = APIRouter(prefix="/notes", tags=["notes"])


async def _get_or_create_tags(
    db: AsyncSession,
    owner_id: UUID,
    tag_names: List[str],
) -> List[Tag]:
    normalized = []
    for name in tag_names:
        cleaned = name.strip()
        if cleaned:
            normalized.append(cleaned[:50])
    unique_names = sorted(set(normalized))

    if not unique_names:
        return []

    existing = await db.execute(
        select(Tag).where(and_(Tag.owner_id == owner_id, Tag.name.in_(unique_names)))
    )
    existing_tags = list(existing.scalars().all())
    existing_by_name = {t.name: t for t in existing_tags}

    to_create = [name for name in unique_names if name not in existing_by_name]
    for name in to_create:
        t = Tag(owner_id=owner_id, name=name)
        db.add(t)
        existing_tags.append(t)

    # flush to obtain ids
    await db.flush()
    return existing_tags


def _note_to_schema(note: Note) -> schemas.NoteResponse:
    return schemas.NoteResponse(
        id=note.id,
        title=note.title,
        content=note.content,
        is_markdown=note.is_markdown,
        pinned=note.pinned,
        favorite=note.favorite,
        created_at=note.created_at,
        updated_at=note.updated_at,
        tags=[
            schemas.TagResponse(id=t.id, name=t.name, created_at=t.created_at)
            for t in (note.tags or [])
        ],
    )


@router.get(
    "",
    response_model=schemas.NotesListResponse,
    summary="List notes",
    description="List notes for the current user. Supports search, tag filter, pinned/favorite filters, and pagination.",
    operation_id="notes_list",
)
async def list_notes(
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    q: Annotated[Optional[str], Query(description="Full-text-ish search across title and content.")] = None,
    tag: Annotated[Optional[str], Query(description="Filter notes having a given tag name.")] = None,
    pinned: Annotated[Optional[bool], Query(description="Filter pinned notes.")] = None,
    favorite: Annotated[Optional[bool], Query(description="Filter favorite notes.")] = None,
    limit: Annotated[int, Query(ge=1, le=100, description="Page size.")] = 50,
    offset: Annotated[int, Query(ge=0, description="Offset for pagination.")] = 0,
) -> schemas.NotesListResponse:
    # PUBLIC_INTERFACE
    """List notes for the authenticated user."""
    filters = [Note.owner_id == user.id]

    if q:
        like = f"%{q.strip()}%"
        filters.append(or_(Note.title.ilike(like), Note.content.ilike(like)))
    if pinned is not None:
        filters.append(Note.pinned == pinned)
    if favorite is not None:
        filters.append(Note.favorite == favorite)

    base_stmt = select(Note).where(and_(*filters)).order_by(Note.pinned.desc(), Note.updated_at.desc())

    if tag:
        base_stmt = base_stmt.join(Note.tags).where(and_(Tag.owner_id == user.id, Tag.name == tag.strip()[:50]))

    total_stmt = select(func.count(func.distinct(Note.id))).select_from(base_stmt.subquery())
    total_res = await db.execute(total_stmt)
    total = int(total_res.scalar() or 0)

    stmt = base_stmt.limit(limit).offset(offset)
    res = await db.execute(stmt)
    notes = list(res.scalars().unique().all())
    return schemas.NotesListResponse(items=[_note_to_schema(n) for n in notes], total=total)


@router.post(
    "",
    response_model=schemas.NoteResponse,
    summary="Create note",
    description="Create a new note. Tag names will be created if missing.",
    status_code=status.HTTP_201_CREATED,
    operation_id="notes_create",
)
async def create_note(
    payload: schemas.NoteCreateRequest,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> schemas.NoteResponse:
    # PUBLIC_INTERFACE
    """Create a note for the authenticated user."""
    note = Note(
        owner_id=user.id,
        title=payload.title,
        content=payload.content,
        is_markdown=payload.is_markdown,
        pinned=payload.pinned,
        favorite=payload.favorite,
    )
    tags = await _get_or_create_tags(db, user.id, payload.tag_names)
    note.tags = tags
    db.add(note)
    await db.commit()
    await db.refresh(note)
    return _note_to_schema(note)


@router.get(
    "/{note_id}",
    response_model=schemas.NoteResponse,
    summary="Get note",
    description="Get a single note by id.",
    operation_id="notes_get",
)
async def get_note(
    note_id: UUID,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> schemas.NoteResponse:
    # PUBLIC_INTERFACE
    """Get a note by id for the authenticated user."""
    res = await db.execute(select(Note).where(and_(Note.id == note_id, Note.owner_id == user.id)))
    note = res.scalar_one_or_none()
    if note is None:
        raise HTTPException(status_code=404, detail="Note not found")
    return _note_to_schema(note)


@router.put(
    "/{note_id}",
    response_model=schemas.NoteResponse,
    summary="Update note",
    description="Update note fields. If tag_names provided, replaces existing tags.",
    operation_id="notes_update",
)
async def update_note(
    note_id: UUID,
    payload: schemas.NoteUpdateRequest,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> schemas.NoteResponse:
    # PUBLIC_INTERFACE
    """Update a note by id for the authenticated user."""
    res = await db.execute(select(Note).where(and_(Note.id == note_id, Note.owner_id == user.id)))
    note = res.scalar_one_or_none()
    if note is None:
        raise HTTPException(status_code=404, detail="Note not found")

    if payload.title is not None:
        note.title = payload.title
    if payload.content is not None:
        note.content = payload.content
    if payload.is_markdown is not None:
        note.is_markdown = payload.is_markdown
    if payload.pinned is not None:
        note.pinned = payload.pinned
    if payload.favorite is not None:
        note.favorite = payload.favorite
    if payload.tag_names is not None:
        tags = await _get_or_create_tags(db, user.id, payload.tag_names)
        note.tags = tags

    await db.commit()
    await db.refresh(note)
    return _note_to_schema(note)


@router.delete(
    "/{note_id}",
    response_model=schemas.APIMessage,
    summary="Delete note",
    description="Delete a note by id.",
    operation_id="notes_delete",
)
async def delete_note(
    note_id: UUID,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> schemas.APIMessage:
    # PUBLIC_INTERFACE
    """Delete a note by id for the authenticated user."""
    res = await db.execute(select(Note).where(and_(Note.id == note_id, Note.owner_id == user.id)))
    note = res.scalar_one_or_none()
    if note is None:
        raise HTTPException(status_code=404, detail="Note not found")

    await db.delete(note)
    await db.commit()
    return schemas.APIMessage(message="Deleted")
