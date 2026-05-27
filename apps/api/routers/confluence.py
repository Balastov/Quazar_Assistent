import uuid

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select

from deps import CurrentUser, DbSession
from models import ConfluenceBinding, Project
from schemas import ConfluenceBindingCreate, ConfluenceBindingOut
from services.audit import log_audit
from services.security import encrypt_secret
from workers.tasks import sync_confluence_binding

router = APIRouter(prefix="/projects/{project_id}/confluence", tags=["confluence"])


@router.get("", response_model=list[ConfluenceBindingOut])
async def list_bindings(project_id: uuid.UUID, user: CurrentUser, db: DbSession):
    await _verify_project(project_id, user, db)
    result = await db.execute(select(ConfluenceBinding).where(ConfluenceBinding.project_id == project_id))
    return result.scalars().all()


@router.post("", response_model=ConfluenceBindingOut, status_code=status.HTTP_201_CREATED)
async def create_binding(project_id: uuid.UUID, data: ConfluenceBindingCreate, user: CurrentUser, db: DbSession):
    await _verify_project(project_id, user, db)
    binding = ConfluenceBinding(
        project_id=project_id,
        organization_id=user.organization_id,
        base_url=data.base_url.rstrip("/"),
        encrypted_token=encrypt_secret(data.api_token),
        space_keys=data.space_keys,
        sync_schedule_cron=data.sync_schedule_cron,
    )
    db.add(binding)
    await db.flush()
    await log_audit(db, user.organization_id, user.id, "create", "confluence_binding", str(binding.id))
    sync_confluence_binding.delay(str(binding.id))
    return binding


@router.post("/{binding_id}/sync", status_code=status.HTTP_202_ACCEPTED)
async def trigger_sync(project_id: uuid.UUID, binding_id: uuid.UUID, user: CurrentUser, db: DbSession):
    await _verify_project(project_id, user, db)
    result = await db.execute(
        select(ConfluenceBinding).where(
            ConfluenceBinding.id == binding_id,
            ConfluenceBinding.project_id == project_id,
        )
    )
    binding = result.scalar_one_or_none()
    if not binding:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Binding not found")

    sync_confluence_binding.delay(str(binding.id))
    await log_audit(db, user.organization_id, user.id, "sync", "confluence_binding", str(binding_id))
    return {"status": "sync_started"}


@router.delete("/{binding_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_binding(project_id: uuid.UUID, binding_id: uuid.UUID, user: CurrentUser, db: DbSession):
    await _verify_project(project_id, user, db)
    result = await db.execute(
        select(ConfluenceBinding).where(
            ConfluenceBinding.id == binding_id,
            ConfluenceBinding.project_id == project_id,
        )
    )
    binding = result.scalar_one_or_none()
    if not binding:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Binding not found")
    await db.delete(binding)


async def _verify_project(project_id: uuid.UUID, user: CurrentUser, db: DbSession) -> Project:
    result = await db.execute(
        select(Project).where(Project.id == project_id, Project.organization_id == user.organization_id)
    )
    project = result.scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")
    return project
