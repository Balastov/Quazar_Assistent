from abc import ABC, abstractmethod
from collections.abc import AsyncIterator
from dataclasses import dataclass, field
from typing import Any


@dataclass
class ChatMessage:
    role: str
    content: str


@dataclass
class TokenUsage:
    prompt_tokens: int = 0
    completion_tokens: int = 0


@dataclass
class LLMResponse:
    content: str = ""
    usage: TokenUsage = field(default_factory=TokenUsage)
    model: str = ""
    provider: str = ""


class LLMProvider(ABC):
    provider_name: str = "base"

    @abstractmethod
    async def chat(
        self,
        messages: list[ChatMessage],
        model_id: str,
        stream: bool = False,
        **kwargs: Any,
    ) -> LLMResponse | AsyncIterator[str]:
        ...

    @abstractmethod
    async def embed(self, texts: list[str], model_id: str) -> list[list[float]]:
        ...
