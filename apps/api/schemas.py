from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, EmailStr, Field

from models import IndexStatus, MessageRole, SearchScope


# Auth
class UserRegister(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8)
    full_name: str
    organization_name: str = "Default Organization"


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class UserOut(BaseModel):
    id: uuid.UUID
    email: str
    full_name: str
    organization_id: uuid.UUID

    model_config = {"from_attributes": True}


# Projects
class ProjectCreate(BaseModel):
    name: str
    description: str | None = None
    search_scope: SearchScope = SearchScope.FILES_ONLY
    allow_external_llm: bool = True


class ProjectUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    search_scope: SearchScope | None = None
    allow_external_llm: bool | None = None


class ProjectOut(BaseModel):
    id: uuid.UUID
    organization_id: uuid.UUID
    name: str
    description: str | None
    search_scope: SearchScope
    allow_external_llm: bool
    created_at: datetime

    model_config = {"from_attributes": True}


# Folders
class FolderCreate(BaseModel):
    name: str
    parent_id: uuid.UUID | None = None


class FolderUpdate(BaseModel):
    name: str | None = None
    parent_id: uuid.UUID | None = None
    sort_order: int | None = None


class FolderOut(BaseModel):
    id: uuid.UUID
    project_id: uuid.UUID
    parent_id: uuid.UUID | None
    name: str
    path_materialized: str
    sort_order: int
    created_at: datetime

    model_config = {"from_attributes": True}


class FolderTreeNode(FolderOut):
    children: list["FolderTreeNode"] = []


# Documents
class DocumentOut(BaseModel):
    id: uuid.UUID
    project_id: uuid.UUID
    folder_id: uuid.UUID | None
    name: str
    mime_type: str
    size_bytes: int
    index_status: IndexStatus
    index_error: str | None
    created_at: datetime

    model_config = {"from_attributes": True}


# Chats
class ChatCreate(BaseModel):
    project_id: uuid.UUID
    title: str = "Новый чат"
    model_id: str = "gpt-4o-mini"
    search_scope: SearchScope | None = None
    mode: str = "qa"


class ChatUpdate(BaseModel):
    title: str | None = None
    model_id: str | None = None
    search_scope: SearchScope | None = None
    mode: str | None = None


class ChatOut(BaseModel):
    id: uuid.UUID
    project_id: uuid.UUID
    title: str
    model_id: str
    search_scope: SearchScope | None
    mode: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class MessageCreate(BaseModel):
    content: str


class MessageOut(BaseModel):
    id: uuid.UUID
    chat_id: uuid.UUID
    role: MessageRole
    content: str
    citations: list[dict[str, Any]] | None
    created_at: datetime

    model_config = {"from_attributes": True}


class CitationOut(BaseModel):
    chunk_id: str
    document_name: str
    source_type: str
    excerpt: str
    page: int | None = None
    url: str | None = None


# LLM
class LlmModelOut(BaseModel):
    id: str
    provider: str
    display_name: str
    context_window: int
    supports_vision: bool

    model_config = {"from_attributes": True}


class UsageSummary(BaseModel):
    total_prompt_tokens: int
    total_completion_tokens: int
    estimated_cost: float
    by_model: dict[str, dict[str, Any]]


# Confluence
class ConfluenceBindingCreate(BaseModel):
    base_url: str
    api_token: str
    space_keys: list[str]
    sync_schedule_cron: str | None = None


class ConfluenceBindingOut(BaseModel):
    id: uuid.UUID
    project_id: uuid.UUID
    base_url: str
    space_keys: list[str]
    last_sync_at: datetime | None
    last_sync_status: str | None
    is_active: bool

    model_config = {"from_attributes": True}


# Audit
class AuditLogOut(BaseModel):
    id: uuid.UUID
    action: str
    resource_type: str
    resource_id: str | None
    metadata_json: dict
    created_at: datetime

    model_config = {"from_attributes": True}
