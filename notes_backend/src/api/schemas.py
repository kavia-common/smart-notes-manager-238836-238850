from __future__ import annotations

import uuid
from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, EmailStr, Field


class APIMessage(BaseModel):
    message: str = Field(..., description="Human-readable status message.")


class TokenResponse(BaseModel):
    access_token: str = Field(..., description="JWT access token to use as a Bearer token.")
    token_type: str = Field("bearer", description="Token type; always 'bearer'.")


class RegisterRequest(BaseModel):
    email: EmailStr = Field(..., description="User email.")
    password: str = Field(..., min_length=8, description="User password (min 8 chars).")


class LoginRequest(BaseModel):
    email: EmailStr = Field(..., description="User email.")
    password: str = Field(..., description="User password.")


class UserResponse(BaseModel):
    id: uuid.UUID = Field(..., description="User id.")
    email: EmailStr = Field(..., description="User email.")
    created_at: datetime = Field(..., description="Account creation timestamp.")


class TagResponse(BaseModel):
    id: uuid.UUID = Field(..., description="Tag id.")
    name: str = Field(..., description="Tag name.")
    created_at: datetime = Field(..., description="Creation timestamp.")


class NoteBase(BaseModel):
    title: str = Field("", max_length=200, description="Note title.")
    content: str = Field("", description="Note content.")
    is_markdown: bool = Field(False, description="Whether note content is markdown.")
    pinned: bool = Field(False, description="Pinned note appears in pinned list.")
    favorite: bool = Field(False, description="Favorite note appears in favorites list.")


class NoteCreateRequest(NoteBase):
    tag_names: List[str] = Field(default_factory=list, description="List of tag names to attach (created if missing).")


class NoteUpdateRequest(BaseModel):
    title: Optional[str] = Field(None, max_length=200, description="New title.")
    content: Optional[str] = Field(None, description="New content.")
    is_markdown: Optional[bool] = Field(None, description="Whether content is markdown.")
    pinned: Optional[bool] = Field(None, description="Pinned flag.")
    favorite: Optional[bool] = Field(None, description="Favorite flag.")
    tag_names: Optional[List[str]] = Field(None, description="Replace tags with this list of names.")


class NoteResponse(NoteBase):
    id: uuid.UUID = Field(..., description="Note id.")
    created_at: datetime = Field(..., description="Creation timestamp.")
    updated_at: datetime = Field(..., description="Last update timestamp.")
    tags: List[TagResponse] = Field(default_factory=list, description="Attached tags.")


class NotesListResponse(BaseModel):
    items: List[NoteResponse] = Field(..., description="Notes list.")
    total: int = Field(..., description="Total number of matching notes (ignores pagination).")
