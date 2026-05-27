import uuid

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from config import get_settings
from models import Document, DocumentChunk, Project, SearchScope, SourceType
from packages.llm_providers.router import LLMRouter

settings = get_settings()
llm_router = LLMRouter()


def _source_types_for_scope(scope: SearchScope) -> list[SourceType]:
    if scope == SearchScope.FILES_ONLY:
        return [SourceType.FILE]
    if scope == SearchScope.CONFLUENCE_ONLY:
        return [SourceType.CONFLUENCE]
    return [SourceType.FILE, SourceType.CONFLUENCE]


async def retrieve_chunks(
    session: AsyncSession,
    project_id: uuid.UUID,
    query: str,
    search_scope: SearchScope,
    top_k: int = 8,
) -> list[dict]:
    embeddings = await llm_router.embed([query], settings.embedding_model)
    query_embedding = embeddings[0]
    source_types = _source_types_for_scope(search_scope)
    source_values = [st.value for st in source_types]

    embedding_str = "[" + ",".join(str(x) for x in query_embedding) + "]"

    sql = text("""
        SELECT
            dc.id,
            dc.content,
            dc.metadata_json,
            dc.source_type,
            dc.chunk_index,
            d.name as document_name,
            d.id as document_id,
            1 - (dc.embedding <=> :embedding::vector) as similarity
        FROM document_chunks dc
        JOIN documents d ON d.id = dc.document_id
        WHERE dc.project_id = :project_id
          AND dc.source_type = ANY(:source_types)
          AND dc.embedding IS NOT NULL
        ORDER BY dc.embedding <=> :embedding::vector
        LIMIT :top_k
    """)

    result = await session.execute(
        sql,
        {
            "embedding": embedding_str,
            "project_id": str(project_id),
            "source_types": source_values,
            "top_k": top_k,
        },
    )
    rows = result.mappings().all()

    chunks = []
    for row in rows:
        meta = row["metadata_json"] or {}
        chunks.append({
            "chunk_id": str(row["id"]),
            "content": row["content"],
            "document_name": row["document_name"],
            "document_id": str(row["document_id"]),
            "source_type": row["source_type"],
            "page": meta.get("page"),
            "url": meta.get("url"),
            "similarity": float(row["similarity"]),
            "excerpt": row["content"][:300],
        })
    return chunks


def build_context(chunks: list[dict]) -> str:
    if not chunks:
        return "Релевантных документов не найдено."
    parts = []
    for i, c in enumerate(chunks, 1):
        source_label = c["document_name"]
        if c.get("url"):
            source_label += f" ({c['url']})"
        parts.append(f"[Источник {i}: {source_label}]\n{c['content']}")
    return "\n\n---\n\n".join(parts)


def build_system_prompt(mode: str, context: str) -> str:
    base = """Ты — Quazar Assistent, корпоративный AI-ассистент.
Отвечай на основе предоставленного контекста из документов организации.
Если информации недостаточно — честно скажи об этом.
Указывай номера источников [Источник N] при ссылке на факты.
Отвечай на языке пользователя."""

    if mode == "draft":
        base += "\n\nРежим: создание черновика документа. Структурируй ответ с заголовками в Markdown."

    return f"{base}\n\nКонтекст из базы знаний:\n\n{context}"


async def check_external_llm_allowed(session: AsyncSession, project_id: uuid.UUID) -> Project:
    result = await session.execute(select(Project).where(Project.id == project_id))
    project = result.scalar_one()
    if not project.allow_external_llm:
        raise ValueError("External LLM is disabled for this project")
    return project
