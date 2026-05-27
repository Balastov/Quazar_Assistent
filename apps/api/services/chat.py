import json
import uuid
from collections.abc import AsyncIterator

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models import Chat, LlmModel, LlmUsageEvent, Message, MessageRole, Project, SearchScope
from packages.llm_providers.base import ChatMessage
from packages.llm_providers.router import LLMRouter
from services.rag import (
    build_context,
    build_system_prompt,
    check_external_llm_allowed,
    retrieve_chunks,
)

llm_router = LLMRouter()


async def stream_chat_response(
    session: AsyncSession,
    chat: Chat,
    user_message: str,
    user_id: uuid.UUID,
) -> AsyncIterator[str]:
    project_result = await session.execute(select(Project).where(Project.id == chat.project_id))
    project = project_result.scalar_one()
    await check_external_llm_allowed(session, chat.project_id)

    scope = chat.search_scope or project.search_scope

    chunks = await retrieve_chunks(session, chat.project_id, user_message, scope)
    context = build_context(chunks)
    system_prompt = build_system_prompt(chat.mode, context)

    history_result = await session.execute(
        select(Message).where(Message.chat_id == chat.id).order_by(Message.created_at)
    )
    history = history_result.scalars().all()

    messages = [ChatMessage(role="system", content=system_prompt)]
    for msg in history[-10:]:
        messages.append(ChatMessage(role=msg.role.value, content=msg.content))
    messages.append(ChatMessage(role="user", content=user_message))

    user_msg = Message(chat_id=chat.id, role=MessageRole.USER, content=user_message)
    session.add(user_msg)
    await session.flush()

    stream = await llm_router.chat(chat.model_id, messages, stream=True)
    full_response = ""

    async for token in stream:
        full_response += token
        yield f"data: {json.dumps({'type': 'token', 'content': token})}\n\n"

    citations = [
        {
            "chunk_id": c["chunk_id"],
            "document_name": c["document_name"],
            "source_type": c["source_type"],
            "excerpt": c["excerpt"],
            "page": c.get("page"),
            "url": c.get("url"),
        }
        for c in chunks
    ]

    assistant_msg = Message(
        chat_id=chat.id,
        role=MessageRole.ASSISTANT,
        content=full_response,
        citations=citations,
    )
    session.add(assistant_msg)

    model_info = llm_router.get_model_info(chat.model_id)
    estimated_tokens = len(user_message.split()) + len(full_response.split())
    usage = LlmUsageEvent(
        organization_id=chat.organization_id,
        user_id=user_id,
        chat_id=chat.id,
        model_id=chat.model_id,
        provider=model_info["provider"],
        prompt_tokens=estimated_tokens // 2,
        completion_tokens=estimated_tokens // 2,
        estimated_cost=llm_router.estimate_cost(chat.model_id, estimated_tokens // 2, estimated_tokens // 2),
    )
    session.add(usage)
    await session.flush()

    yield f"data: {json.dumps({'type': 'done', 'citations': citations, 'message_id': str(assistant_msg.id)})}\n\n"
