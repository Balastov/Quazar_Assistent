import uuid

from fastapi import APIRouter, HTTPException, status
from fastapi.responses import StreamingResponse
from sqlalchemy import select

from deps import CurrentUser, DbSession
from models import Chat, Message, Project
from schemas import ChatCreate, ChatOut, ChatUpdate, MessageCreate, MessageOut
from services.audit import log_audit
from services.chat import stream_chat_response

router = APIRouter(tags=["chats"])


@router.get("/projects/{project_id}/chats", response_model=list[ChatOut])
async def list_chats(project_id: uuid.UUID, user: CurrentUser, db: DbSession):
    await _verify_project(project_id, user, db)
    result = await db.execute(
        select(Chat).where(Chat.project_id == project_id, Chat.user_id == user.id).order_by(Chat.updated_at.desc())
    )
    return result.scalars().all()


@router.post("/projects/{project_id}/chats", response_model=ChatOut, status_code=status.HTTP_201_CREATED)
async def create_chat(project_id: uuid.UUID, data: ChatCreate, user: CurrentUser, db: DbSession):
    await _verify_project(project_id, user, db)
    chat = Chat(
        project_id=project_id,
        organization_id=user.organization_id,
        user_id=user.id,
        title=data.title,
        model_id=data.model_id,
        search_scope=data.search_scope,
        mode=data.mode,
    )
    db.add(chat)
    await db.flush()
    await log_audit(db, user.organization_id, user.id, "create", "chat", str(chat.id))
    return chat


@router.get("/chats/{chat_id}", response_model=ChatOut)
async def get_chat(chat_id: uuid.UUID, user: CurrentUser, db: DbSession):
    chat = await _get_chat(chat_id, user, db)
    return chat


@router.patch("/chats/{chat_id}", response_model=ChatOut)
async def update_chat(chat_id: uuid.UUID, data: ChatUpdate, user: CurrentUser, db: DbSession):
    chat = await _get_chat(chat_id, user, db)
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(chat, field, value)
    return chat


@router.delete("/chats/{chat_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_chat(chat_id: uuid.UUID, user: CurrentUser, db: DbSession):
    chat = await _get_chat(chat_id, user, db)
    await db.delete(chat)


@router.get("/chats/{chat_id}/messages", response_model=list[MessageOut])
async def list_messages(chat_id: uuid.UUID, user: CurrentUser, db: DbSession):
    await _get_chat(chat_id, user, db)
    result = await db.execute(select(Message).where(Message.chat_id == chat_id).order_by(Message.created_at))
    return result.scalars().all()


@router.post("/chats/{chat_id}/messages")
async def send_message(chat_id: uuid.UUID, data: MessageCreate, user: CurrentUser, db: DbSession):
    chat = await _get_chat(chat_id, user, db)

    if data.content.strip():
        chat.title = data.content[:50] + ("..." if len(data.content) > 50 else "")

    await log_audit(
        db, user.organization_id, user.id, "chat_message", "chat", str(chat_id),
        {"length": len(data.content)},
    )

    async def event_generator():
        async for event in stream_chat_response(db, chat, data.content, user.id):
            yield event
        await db.commit()

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


async def _get_chat(chat_id: uuid.UUID, user: CurrentUser, db: DbSession) -> Chat:
    result = await db.execute(
        select(Chat).where(
            Chat.id == chat_id,
            Chat.user_id == user.id,
            Chat.organization_id == user.organization_id,
        )
    )
    chat = result.scalar_one_or_none()
    if not chat:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Chat not found")
    return chat


async def _verify_project(project_id: uuid.UUID, user: CurrentUser, db: DbSession) -> Project:
    result = await db.execute(
        select(Project).where(Project.id == project_id, Project.organization_id == user.organization_id)
    )
    project = result.scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")
    return project
