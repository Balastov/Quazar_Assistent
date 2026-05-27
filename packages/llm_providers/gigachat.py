import uuid
from collections.abc import AsyncIterator
from typing import Any

import httpx

from .base import ChatMessage, LLMProvider, LLMResponse, TokenUsage

GIGACHAT_AUTH_URL = "https://ngw.devices.sberbank.ru:9443/api/v2/oauth"
GIGACHAT_API_URL = "https://gigachat.devices.sberbank.ru/api/v1"


class GigaChatProvider(LLMProvider):
    provider_name = "gigachat"

    def __init__(self, client_id: str, client_secret: str, scope: str = "GIGACHAT_API_PERS"):
        self.client_id = client_id
        self.client_secret = client_secret
        self.scope = scope
        self._token: str | None = None

    async def _get_token(self) -> str:
        if self._token:
            return self._token
        async with httpx.AsyncClient(verify=False) as client:
            response = await client.post(
                GIGACHAT_AUTH_URL,
                headers={
                    "Authorization": f"Basic {self._encode_credentials()}",
                    "RqUID": str(uuid.uuid4()),
                    "Content-Type": "application/x-www-form-urlencoded",
                },
                data={"scope": self.scope},
            )
            response.raise_for_status()
            self._token = response.json()["access_token"]
            return self._token

    def _encode_credentials(self) -> str:
        import base64
        creds = f"{self.client_id}:{self.client_secret}"
        return base64.b64encode(creds.encode()).decode()

    async def chat(
        self,
        messages: list[ChatMessage],
        model_id: str,
        stream: bool = False,
        **kwargs: Any,
    ) -> LLMResponse | AsyncIterator[str]:
        token = await self._get_token()
        formatted = [{"role": m.role, "content": m.content} for m in messages]

        async with httpx.AsyncClient(verify=False, timeout=120.0) as client:
            if stream:

                async def _stream() -> AsyncIterator[str]:
                    async with client.stream(
                        "POST",
                        f"{GIGACHAT_API_URL}/chat/completions",
                        headers={"Authorization": f"Bearer {token}"},
                        json={"model": model_id, "messages": formatted, "stream": True},
                    ) as response:
                        response.raise_for_status()
                        async for line in response.aiter_lines():
                            if line.startswith("data: ") and line != "data: [DONE]":
                                import json
                                data = json.loads(line[6:])
                                delta = data.get("choices", [{}])[0].get("delta", {}).get("content")
                                if delta:
                                    yield delta

                return _stream()

            response = await client.post(
                f"{GIGACHAT_API_URL}/chat/completions",
                headers={"Authorization": f"Bearer {token}"},
                json={"model": model_id, "messages": formatted},
            )
            response.raise_for_status()
            data = response.json()
            usage_data = data.get("usage", {})
            return LLMResponse(
                content=data["choices"][0]["message"]["content"],
                usage=TokenUsage(
                    prompt_tokens=usage_data.get("prompt_tokens", 0),
                    completion_tokens=usage_data.get("completion_tokens", 0),
                ),
                model=model_id,
                provider=self.provider_name,
            )

    async def embed(self, texts: list[str], model_id: str = "Embeddings") -> list[list[float]]:
        token = await self._get_token()
        async with httpx.AsyncClient(verify=False, timeout=60.0) as client:
            response = await client.post(
                f"{GIGACHAT_API_URL}/embeddings",
                headers={"Authorization": f"Bearer {token}"},
                json={"model": model_id, "input": texts},
            )
            response.raise_for_status()
            data = response.json()
            return [item["embedding"] for item in data["data"]]
