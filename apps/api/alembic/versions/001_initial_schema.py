"""initial schema

Revision ID: 001
Revises:
Create Date: 2026-05-06
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from pgvector.sqlalchemy import Vector

revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    op.create_table(
        "organizations",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("slug", sa.String(100), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("slug"),
    )

    op.create_table(
        "users",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("organization_id", sa.UUID(), nullable=False),
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column("hashed_password", sa.String(255), nullable=False),
        sa.Column("full_name", sa.String(255), nullable=False),
        sa.Column("is_active", sa.Boolean(), default=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("email"),
    )

    op.create_table(
        "llm_models",
        sa.Column("id", sa.String(128), nullable=False),
        sa.Column("provider", sa.String(64), nullable=False),
        sa.Column("display_name", sa.String(255), nullable=False),
        sa.Column("context_window", sa.Integer(), default=128000),
        sa.Column("supports_vision", sa.Boolean(), default=False),
        sa.Column("price_per_1k_input", sa.Float(), default=0.0),
        sa.Column("price_per_1k_output", sa.Float(), default=0.0),
        sa.Column("is_active", sa.Boolean(), default=True),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "projects",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("organization_id", sa.UUID(), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text()),
        sa.Column(
            "search_scope",
            sa.Enum("files_only", "confluence_only", "files_and_confluence", name="search_scope"),
            server_default="files_only",
        ),
        sa.Column("allow_external_llm", sa.Boolean(), default=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"]),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "folders",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("project_id", sa.UUID(), nullable=False),
        sa.Column("parent_id", sa.UUID()),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("path_materialized", sa.String(2048), default="/"),
        sa.Column("sort_order", sa.Integer(), default=0),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"]),
        sa.ForeignKeyConstraint(["parent_id"], ["folders.id"]),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "documents",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("project_id", sa.UUID(), nullable=False),
        sa.Column("folder_id", sa.UUID()),
        sa.Column("name", sa.String(512), nullable=False),
        sa.Column("mime_type", sa.String(128), nullable=False),
        sa.Column("storage_key", sa.String(1024), nullable=False),
        sa.Column("size_bytes", sa.Integer(), default=0),
        sa.Column("version", sa.Integer(), default=1),
        sa.Column("content_hash", sa.String(64)),
        sa.Column(
            "index_status",
            sa.Enum("pending", "processing", "ready", "failed", name="index_status"),
            server_default="pending",
        ),
        sa.Column("index_error", sa.Text()),
        sa.Column(
            "source_type",
            sa.Enum("file", "confluence", "web", name="source_type"),
            server_default="file",
        ),
        sa.Column("external_id", sa.String(255)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"]),
        sa.ForeignKeyConstraint(["folder_id"], ["folders.id"]),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "document_chunks",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("document_id", sa.UUID(), nullable=False),
        sa.Column("project_id", sa.UUID(), nullable=False),
        sa.Column("organization_id", sa.UUID(), nullable=False),
        sa.Column("chunk_index", sa.Integer(), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("metadata_json", sa.dialects.postgresql.JSONB(), default={}),
        sa.Column(
            "source_type",
            sa.Enum("file", "confluence", "web", name="source_type_chunk"),
            nullable=False,
        ),
        sa.Column("embedding", Vector(1536)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["document_id"], ["documents.id"]),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"]),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"]),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_index("ix_chunks_project", "document_chunks", ["project_id"])
    op.create_index(
        "ix_chunks_embedding",
        "document_chunks",
        ["embedding"],
        postgresql_using="ivfflat",
        postgresql_with={"lists": 100},
        postgresql_ops={"embedding": "vector_cosine_ops"},
    )

    op.create_table(
        "chats",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("project_id", sa.UUID(), nullable=False),
        sa.Column("organization_id", sa.UUID(), nullable=False),
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("title", sa.String(255), default="Новый чат"),
        sa.Column("model_id", sa.String(128), default="gpt-4o-mini"),
        sa.Column("search_scope", sa.Enum("files_only", "confluence_only", "files_and_confluence", name="search_scope_chat")),
        sa.Column("mode", sa.String(32), default="qa"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"]),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "messages",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("chat_id", sa.UUID(), nullable=False),
        sa.Column("role", sa.Enum("user", "assistant", "system", name="message_role"), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("citations", sa.dialects.postgresql.JSONB()),
        sa.Column("token_count", sa.Integer()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["chat_id"], ["chats.id"]),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "llm_provider_configs",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("organization_id", sa.UUID(), nullable=False),
        sa.Column("provider", sa.String(64), nullable=False),
        sa.Column("encrypted_api_key", sa.Text()),
        sa.Column("base_url", sa.String(512)),
        sa.Column("is_enabled", sa.Boolean(), default=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("organization_id", "provider", name="uq_org_provider"),
    )

    op.create_table(
        "llm_usage_events",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("organization_id", sa.UUID(), nullable=False),
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("chat_id", sa.UUID()),
        sa.Column("model_id", sa.String(128), nullable=False),
        sa.Column("provider", sa.String(64), nullable=False),
        sa.Column("prompt_tokens", sa.Integer(), default=0),
        sa.Column("completion_tokens", sa.Integer(), default=0),
        sa.Column("estimated_cost", sa.Float(), default=0.0),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["chat_id"], ["chats.id"]),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "confluence_bindings",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("project_id", sa.UUID(), nullable=False),
        sa.Column("organization_id", sa.UUID(), nullable=False),
        sa.Column("base_url", sa.String(512), nullable=False),
        sa.Column("encrypted_token", sa.Text(), nullable=False),
        sa.Column("space_keys", sa.ARRAY(sa.String())),
        sa.Column("sync_schedule_cron", sa.String(64)),
        sa.Column("last_sync_at", sa.DateTime(timezone=True)),
        sa.Column("last_sync_status", sa.String(32)),
        sa.Column("is_active", sa.Boolean(), default=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"]),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"]),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "confluence_pages",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("binding_id", sa.UUID(), nullable=False),
        sa.Column("project_id", sa.UUID(), nullable=False),
        sa.Column("page_id", sa.String(64), nullable=False),
        sa.Column("title", sa.String(512), nullable=False),
        sa.Column("url", sa.String(1024), nullable=False),
        sa.Column("version", sa.Integer(), default=1),
        sa.Column("last_modified", sa.DateTime(timezone=True)),
        sa.Column("document_id", sa.UUID()),
        sa.ForeignKeyConstraint(["binding_id"], ["confluence_bindings.id"]),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"]),
        sa.ForeignKeyConstraint(["document_id"], ["documents.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("binding_id", "page_id", name="uq_binding_page"),
    )

    op.create_table(
        "audit_logs",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("organization_id", sa.UUID(), nullable=False),
        sa.Column("user_id", sa.UUID()),
        sa.Column("action", sa.String(64), nullable=False),
        sa.Column("resource_type", sa.String(64), nullable=False),
        sa.Column("resource_id", sa.String(64)),
        sa.Column("metadata_json", sa.dialects.postgresql.JSONB(), default={}),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )

    # Row Level Security policies (enabled for future multi-tenant)
    op.execute("ALTER TABLE projects ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE folders ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE documents ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE document_chunks ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE chats ENABLE ROW LEVEL SECURITY")

    op.execute("""
        CREATE POLICY projects_org_isolation ON projects
        USING (
            current_setting('app.current_organization_id', true) IS NULL
            OR current_setting('app.current_organization_id', true) = ''
            OR organization_id = current_setting('app.current_organization_id', true)::uuid
        )
    """)
    op.execute("""
        CREATE POLICY folders_org_isolation ON folders
        USING (
            current_setting('app.current_organization_id', true) IS NULL
            OR current_setting('app.current_organization_id', true) = ''
            OR project_id IN (
                SELECT id FROM projects
                WHERE organization_id = current_setting('app.current_organization_id', true)::uuid
            )
        )
    """)
    op.execute("""
        CREATE POLICY documents_org_isolation ON documents
        USING (
            current_setting('app.current_organization_id', true) IS NULL
            OR current_setting('app.current_organization_id', true) = ''
            OR project_id IN (
                SELECT id FROM projects
                WHERE organization_id = current_setting('app.current_organization_id', true)::uuid
            )
        )
    """)
    op.execute("""
        CREATE POLICY chunks_org_isolation ON document_chunks
        USING (
            current_setting('app.current_organization_id', true) IS NULL
            OR current_setting('app.current_organization_id', true) = ''
            OR organization_id = current_setting('app.current_organization_id', true)::uuid
        )
    """)
    op.execute("""
        CREATE POLICY chats_org_isolation ON chats
        USING (
            current_setting('app.current_organization_id', true) IS NULL
            OR current_setting('app.current_organization_id', true) = ''
            OR organization_id = current_setting('app.current_organization_id', true)::uuid
        )
    """)


def downgrade() -> None:
    for table in [
        "audit_logs", "confluence_pages", "confluence_bindings", "llm_usage_events",
        "llm_provider_configs", "messages", "chats", "document_chunks", "documents",
        "folders", "projects", "llm_models", "users", "organizations",
    ]:
        op.drop_table(table)
