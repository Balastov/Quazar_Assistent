from collections.abc import AsyncIterator
from typing import Any

import httpx
from openai import AsyncOpenAI

from .base import ChatMessage, LLMProvider, LLMResponse, TokenUsage


class OpenAICompatibleProvider(LLMProvider):
    def __init__(self, api_key: str, base_url: str, provider_name: str = "openai"):
        self.provider_name = provider_name
        self.client = AsyncOpenAI(api_key=api_key, base_url=base_url)

    async def chat(
        self,
        messages: list[ChatMessage],
        model_id: str,
        stream: bool = False,
        **kwargs: Any,
    ) -> LLMResponse | AsyncIterator[str]:
        formatted = [{"role": m.role, "content": m.content} for m in messages]

        if stream:

            async def _stream() -> AsyncIterator[str]:
                response = await self.client.chat.completions.create(
                    model=model_id, messages=formatted, stream=True, **kwargs
                )
                async for chunk in response:
                    delta = chunk.choices[0].delta.content if chunk.choices else None
                    if delta:
                        yield delta

            return _stream()

        response = await self.client.chat.completions.create(
            model=model_id, messages=formatted, stream=False, **kwargs
        )
        usage = response.usage
        return LLMResponse(
            content=response.choices[0].message.content or "",
            usage=TokenUsage(
                prompt_tokens=usage.prompt_tokens if usage else 0,
                completion_tokens=usage.completion_tokens if usage else 0,
            ),
            model=model_id,
            provider=self.provider_name,
        )

    async def embed(self, texts: list[str], model_id: str) -> list[list[float]]:
        response = await self.client.embeddings.create(model=model_id, input=texts)
        return [item.embedding for item in response.data]
