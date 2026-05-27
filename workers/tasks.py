import hashlib
import sys
import uuid
from datetime import UTC, datetime
from pathlib import Path

from celery import shared_task
from sqlalchemy import create_engine, delete, select
from sqlalchemy.orm import Session

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "apps" / "api"))

from config import get_settings
from models import (
    ConfluenceBinding,
    ConfluencePage,
    Document,
    DocumentChunk,
    IndexStatus,
    Project,
    SourceType,
)
from packages.ingestion.chunker import chunk_text
from packages.ingestion.confluence import ConfluenceClient
from packages.ingestion.parsers import extract_text
from packages.llm_providers.router import LLMRouter
from services.security import decrypt_secret
from services.storage import download_file

settings = get_settings()
engine = create_engine(settings.database_url_sync)
llm_router = LLMRouter()


def _session() -> Session:
    return Session(engine)


@shared_task(name="workers.tasks.ingest_document")
def ingest_document(document_id: str) -> dict:
    with _session() as session:
        doc = session.get(Document, uuid.UUID(document_id))
        if not doc:
            return {"error": "Document not found"}

        doc.index_status = IndexStatus.PROCESSING
        session.commit()

        try:
            content = download_file(doc.storage_key)
            text = extract_text(content, doc.mime_type, doc.name)
            if not text.strip():
                doc.index_status = IndexStatus.FAILED
                doc.index_error = "No text extracted"
                session.commit()
                return {"error": "No text extracted"}

            project = session.get(Project, doc.project_id)
            chunks_data = chunk_text(text)

            session.execute(delete(DocumentChunk).where(DocumentChunk.document_id == doc.id))

            texts = [c["content"] for c in chunks_data]
            embeddings = []
            if texts:
                import asyncio
                embeddings = asyncio.run(llm_router.embed(texts, settings.embedding_model))

            for i, chunk_data in enumerate(chunks_data):
                embedding = embeddings[i] if i < len(embeddings) else None
                chunk = DocumentChunk(
                    document_id=doc.id,
                    project_id=doc.project_id,
                    organization_id=project.organization_id,
                    chunk_index=chunk_data["chunk_index"],
                    content=chunk_data["content"],
                    metadata_json={**chunk_data.get("metadata", {}), "document_name": doc.name},
                    source_type=doc.source_type,
                    embedding=embedding,
                )
                session.add(chunk)

            doc.index_status = IndexStatus.READY
            doc.index_error = None
            session.commit()
            return {"status": "ready", "chunks": len(chunks_data)}

        except Exception as e:
            doc.index_status = IndexStatus.FAILED
            doc.index_error = str(e)
            session.commit()
            return {"error": str(e)}


@shared_task(name="workers.tasks.sync_confluence_binding")
def sync_confluence_binding(binding_id: str) -> dict:
    import asyncio
    return asyncio.run(_sync_confluence_async(binding_id))


async def _sync_confluence_async(binding_id: str) -> dict:
    with _session() as session:
        binding = session.get(ConfluenceBinding, uuid.UUID(binding_id))
        if not binding or not binding.is_active:
            return {"error": "Binding not found or inactive"}

        binding.last_sync_status = "processing"
        session.commit()

        try:
            token = decrypt_secret(binding.encrypted_token)
            client = ConfluenceClient(binding.base_url, token)
            pages = await client.list_pages_in_spaces(binding.space_keys, binding.last_sync_at)
            synced = 0

            project = session.get(Project, binding.project_id)

            for page in pages:
                meta = client.page_metadata(page, binding.base_url)
                text = client.page_to_text(page)
                if not text.strip():
                    continue

                content_hash = hashlib.sha256(text.encode()).hexdigest()
                storage_key = f"confluence/{binding.id}/{meta['page_id']}.txt"

                existing_page = session.execute(
                    select(ConfluencePage).where(
                        ConfluencePage.binding_id == binding.id,
                        ConfluencePage.page_id == meta["page_id"],
                    )
                ).scalar_one_or_none()

                doc = None
                if existing_page and existing_page.document_id:
                    doc = session.get(Document, existing_page.document_id)
                    if doc and doc.content_hash == content_hash:
                        continue

                if not doc:
                    doc = Document(
                        project_id=binding.project_id,
                        name=f"[Confluence] {meta['title']}",
                        mime_type="text/plain",
                        storage_key=storage_key,
                        size_bytes=len(text.encode()),
                        content_hash=content_hash,
                        index_status=IndexStatus.PENDING,
                        source_type=SourceType.CONFLUENCE,
                        external_id=meta["page_id"],
                    )
                    session.add(doc)
                    session.flush()
                else:
                    doc.content_hash = content_hash
                    doc.index_status = IndexStatus.PENDING

                if existing_page:
                    existing_page.title = meta["title"]
                    existing_page.url = meta["url"]
                    existing_page.version = meta["version"]
                    existing_page.document_id = doc.id
                else:
                    conf_page = ConfluencePage(
                        binding_id=binding.id,
                        project_id=binding.project_id,
                        page_id=meta["page_id"],
                        title=meta["title"],
                        url=meta["url"],
                        version=meta["version"],
                        document_id=doc.id,
                    )
                    session.add(conf_page)

                session.execute(delete(DocumentChunk).where(DocumentChunk.document_id == doc.id))
                chunks_data = chunk_text(text)
                texts = [c["content"] for c in chunks_data]
                embeddings = await llm_router.embed(texts, settings.embedding_model) if texts else []

                for i, chunk_data in enumerate(chunks_data):
                    chunk = DocumentChunk(
                        document_id=doc.id,
                        project_id=binding.project_id,
                        organization_id=project.organization_id,
                        chunk_index=chunk_data["chunk_index"],
                        content=chunk_data["content"],
                        metadata_json={
                            **chunk_data.get("metadata", {}),
                            "document_name": doc.name,
                            "url": meta["url"],
                            "title": meta["title"],
                        },
                        source_type=SourceType.CONFLUENCE,
                        embedding=embeddings[i] if i < len(embeddings) else None,
                    )
                    session.add(chunk)

                doc.index_status = IndexStatus.READY
                synced += 1

            binding.last_sync_at = datetime.now(UTC)
            binding.last_sync_status = "success"
            session.commit()
            return {"status": "success", "synced_pages": synced}

        except Exception as e:
            binding.last_sync_status = f"failed: {e}"
            session.commit()
            return {"error": str(e)}


@shared_task(name="workers.tasks.sync_all_confluence_bindings")
def sync_all_confluence_bindings() -> dict:
    with _session() as session:
        bindings = session.execute(
            select(ConfluenceBinding).where(ConfluenceBinding.is_active == True)  # noqa: E712
        ).scalars().all()
        for binding in bindings:
            sync_confluence_binding.delay(str(binding.id))
    return {"triggered": len(bindings)}
