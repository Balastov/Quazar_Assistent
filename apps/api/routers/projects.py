import uuid

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select

from deps import CurrentUser, DbSession
from models import Folder, Project
from schemas import FolderCreate, FolderOut, FolderTreeNode, FolderUpdate, ProjectCreate, ProjectOut, ProjectUpdate
from services.audit import log_audit

router = APIRouter(prefix="/projects", tags=["projects"])


@router.get("", response_model=list[ProjectOut])
async def list_projects(user: CurrentUser, db: DbSession):
    result = await db.execute(
        select(Project).where(Project.organization_id == user.organization_id).order_by(Project.created_at.desc())
    )
    return result.scalars().all()


@router.post("", response_model=ProjectOut, status_code=status.HTTP_201_CREATED)
async def create_project(data: ProjectCreate, user: CurrentUser, db: DbSession):
    project = Project(
        organization_id=user.organization_id,
        name=data.name,
        description=data.description,
        search_scope=data.search_scope,
        allow_external_llm=data.allow_external_llm,
    )
    db.add(project)
    await db.flush()
    await log_audit(db, user.organization_id, user.id, "create", "project", str(project.id))
    return project


@router.get("/{project_id}", response_model=ProjectOut)
async def get_project(project_id: uuid.UUID, user: CurrentUser, db: DbSession):
    project = await _get_project(project_id, user, db)
    return project


@router.patch("/{project_id}", response_model=ProjectOut)
async def update_project(project_id: uuid.UUID, data: ProjectUpdate, user: CurrentUser, db: DbSession):
    project = await _get_project(project_id, user, db)
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(project, field, value)
    await log_audit(db, user.organization_id, user.id, "update", "project", str(project.id))
    return project


@router.delete("/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_project(project_id: uuid.UUID, user: CurrentUser, db: DbSession):
    project = await _get_project(project_id, user, db)
    await db.delete(project)
    await log_audit(db, user.organization_id, user.id, "delete", "project", str(project_id))


# Folders
@router.get("/{project_id}/folders", response_model=list[FolderOut])
async def list_folders(project_id: uuid.UUID, user: CurrentUser, db: DbSession, parent_id: uuid.UUID | None = None):
    await _get_project(project_id, user, db)
    query = select(Folder).where(Folder.project_id == project_id)
    if parent_id:
        query = query.where(Folder.parent_id == parent_id)
    else:
        query = query.where(Folder.parent_id.is_(None))
    result = await db.execute(query.order_by(Folder.sort_order, Folder.name))
    return result.scalars().all()


@router.get("/{project_id}/folders/tree", response_model=list[FolderTreeNode])
async def folder_tree(project_id: uuid.UUID, user: CurrentUser, db: DbSession):
    await _get_project(project_id, user, db)
    result = await db.execute(select(Folder).where(Folder.project_id == project_id).order_by(Folder.sort_order))
    folders = list(result.scalars().all())
    return _build_tree(folders)


@router.post("/{project_id}/folders", response_model=FolderOut, status_code=status.HTTP_201_CREATED)
async def create_folder(project_id: uuid.UUID, data: FolderCreate, user: CurrentUser, db: DbSession):
    await _get_project(project_id, user, db)
    path = "/"
    if data.parent_id:
        parent = await _get_folder(data.parent_id, project_id, db)
        path = f"{parent.path_materialized.rstrip('/')}/{parent.name}"

    folder = Folder(
        project_id=project_id,
        parent_id=data.parent_id,
        name=data.name,
        path_materialized=path,
    )
    db.add(folder)
    await db.flush()
    await log_audit(db, user.organization_id, user.id, "create", "folder", str(folder.id))
    return folder


@router.patch("/{project_id}/folders/{folder_id}", response_model=FolderOut)
async def update_folder(
    project_id: uuid.UUID, folder_id: uuid.UUID, data: FolderUpdate, user: CurrentUser, db: DbSession
):
    folder = await _get_folder(folder_id, project_id, db)
    if data.name is not None:
        folder.name = data.name
    if data.parent_id is not None:
        folder.parent_id = data.parent_id
    if data.sort_order is not None:
        folder.sort_order = data.sort_order
    return folder


@router.delete("/{project_id}/folders/{folder_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_folder(project_id: uuid.UUID, folder_id: uuid.UUID, user: CurrentUser, db: DbSession):
    folder = await _get_folder(folder_id, project_id, db)
    await db.delete(folder)


async def _get_project(project_id: uuid.UUID, user: CurrentUser, db: DbSession) -> Project:
    result = await db.execute(
        select(Project).where(Project.id == project_id, Project.organization_id == user.organization_id)
    )
    project = result.scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")
    return project


async def _get_folder(folder_id: uuid.UUID, project_id: uuid.UUID, db: DbSession) -> Folder:
    result = await db.execute(select(Folder).where(Folder.id == folder_id, Folder.project_id == project_id))
    folder = result.scalar_one_or_none()
    if not folder:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Folder not found")
    return folder


def _build_tree(folders: list[Folder]) -> list[FolderTreeNode]:
    by_parent: dict[uuid.UUID | None, list[Folder]] = {}
    for f in folders:
        by_parent.setdefault(f.parent_id, []).append(f)

    def build(parent_id: uuid.UUID | None) -> list[FolderTreeNode]:
        nodes = []
        for folder in by_parent.get(parent_id, []):
            node = FolderTreeNode(
                id=folder.id,
                project_id=folder.project_id,
                parent_id=folder.parent_id,
                name=folder.name,
                path_materialized=folder.path_materialized,
                sort_order=folder.sort_order,
                created_at=folder.created_at,
                children=build(folder.id),
            )
            nodes.append(node)
        return nodes

    return build(None)
