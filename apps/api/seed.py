"""Seed default organization and LLM models. Run: python seed.py"""

import asyncio
import uuid

from sqlalchemy import select

from database import async_session
from models import LlmModel, Organization, User
from services.security import hash_password


async def seed():
    async with async_session() as session:
        org_result = await session.execute(select(Organization).where(Organization.slug == "demo"))
        org = org_result.scalar_one_or_none()
        if not org:
            org = Organization(name="Demo Organization", slug="demo")
            session.add(org)
            await session.flush()

        user_result = await session.execute(select(User).where(User.email == "admin@quazar.local"))
        if not user_result.scalar_one_or_none():
            user = User(
                organization_id=org.id,
                email="admin@quazar.local",
                hashed_password=hash_password("admin12345"),
                full_name="Admin User",
            )
            session.add(user)

        models = [
            LlmModel(id="gpt-4o", provider="openai", display_name="GPT-4o", context_window=128000,
                     price_per_1k_input=0.0025, price_per_1k_output=0.01),
            LlmModel(id="gpt-4o-mini", provider="openai", display_name="GPT-4o Mini", context_window=128000,
                     price_per_1k_input=0.00015, price_per_1k_output=0.0006),
            LlmModel(id="deepseek-chat", provider="deepseek", display_name="DeepSeek Chat", context_window=64000,
                     price_per_1k_input=0.00014, price_per_1k_output=0.00028),
            LlmModel(id="GigaChat", provider="gigachat", display_name="GigaChat", context_window=32000),
            LlmModel(id="GigaChat-Pro", provider="gigachat", display_name="GigaChat Pro", context_window=32000),
        ]
        for model in models:
            existing = await session.get(LlmModel, model.id)
            if not existing:
                session.add(model)

        await session.commit()
        print(f"Seeded organization: {org.id}")
        print("Demo user: admin@quazar.local / admin12345")


if __name__ == "__main__":
    asyncio.run(seed())
