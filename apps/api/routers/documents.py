import hashlib
import uuid

from fastapi import APIRouter, File, HTTPException, UploadFile, status
from sqlalchemy import select

from deps import CurrentUser, DbSession
from models import Document, IndexStatus, Project, SourceType
from schemas import DocumentOut
from services.audit import log_audit
from services.storage import delete_file, upload_file

router = APIRouter(prefix="/projects/{project_id}/documents", tags=["documents"])


@router.get("", response_model=list[DocumentOut])
async def list_documents(
    project_id: uuid.UUID,
    user: CurrentUser,
    db: DbSession,
    folder_id: uuid.UUID | None = None,
):
    await _verify_project(project_id, user, db)
    query = select(Document).where(Document.project_id == project_id)
    if folder_id:
        query = query.where(Document.folder_id == folder_id)
    result = await db.execute(query.order_by(Document.created_at.desc()))
    return result.scalars().all()


@router.post("/upload", response_model=DocumentOut, status_code=status.HTTP_201_CREATED)
async def upload_document(
    project_id: uuid.UUID,
    user: CurrentUser,
    db: DbSession,
    file: UploadFile = File(...),
    folder_id: uuid.UUID | None = None,
):
    await _verify_project(project_id, user, db)
    content = await file.read()
    if len(content) > 100 * 1024 * 1024:
        raise HTTPException(status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, detail="File too large")

    storage_key = upload_file(content, file.filename or "unnamed", file.content_type or "application/octet-stream", project_id)
    content_hash = hashlib.sha256(content).hexdigest()

    doc = Document(
        project_id=project_id,
        folder_id=folder_id,
        name=file.filename or "unnamed",
        mime_type=file.content_type or "application/octet-stream",
        storage_key=storage_key,
        size_bytes=len(content),
        content_hash=content_hash,
        index_status=IndexStatus.PENDING,
        source_type=SourceType.FILE,
    )
    db.add(doc)
    await db.flush()

    from workers.tasks import ingest_document

    ingest_document.delay(str(doc.id))

    await log_audit(
        db, user.organization_id, user.id, "upload", "document", str(doc.id),
        {"filename": doc.name, "size": doc.size_bytes},
    )
    return doc


@router.delete("/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_document(project_id: uuid.UUID, document_id: uuid.UUID, user: CurrentUser, db: DbSession):
    await _verify_project(project_id, user, db)
    result = await db.execute(
        select(Document).where(Document.id == document_id, Document.project_id == project_id)
    )
    doc = result.scalar_one_or_none()
    if not doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")

    delete_file(doc.storage_key)
    await db.delete(doc)
    await log_audit(db, user.organization_id, user.id, "delete", "document", str(document_id))


async def _verify_project(project_id: uuid.UUID, user: CurrentUser, db: DbSession) -> Project:
    result = await db.execute(
        select(Project).where(Project.id == project_id, Project.organization_id == user.organization_id)
    )
    project = result.scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")
    return project
