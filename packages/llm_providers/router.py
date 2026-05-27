from typing import Any

from config import get_settings

from .base import ChatMessage, LLMProvider, LLMResponse
from .gigachat import GigaChatProvider
from .openai_compat import OpenAICompatibleProvider

settings = get_settings()

MODEL_REGISTRY: dict[str, dict[str, Any]] = {
    "gpt-4o": {"provider": "openai", "display_name": "GPT-4o", "context_window": 128000},
    "gpt-4o-mini": {"provider": "openai", "display_name": "GPT-4o Mini", "context_window": 128000},
    "deepseek-chat": {"provider": "deepseek", "display_name": "DeepSeek Chat", "context_window": 64000},
    "deepseek-reasoner": {"provider": "deepseek", "display_name": "DeepSeek Reasoner", "context_window": 64000},
    "GigaChat": {"provider": "gigachat", "display_name": "GigaChat", "context_window": 32000},
    "GigaChat-Pro": {"provider": "gigachat", "display_name": "GigaChat Pro", "context_window": 32000},
}


class LLMRouter:
    def __init__(self):
        self._providers: dict[str, LLMProvider] = {}

    def _get_provider(self, provider_name: str) -> LLMProvider:
        if provider_name in self._providers:
            return self._providers[provider_name]

        if provider_name == "openai":
            provider = OpenAICompatibleProvider(
                api_key=settings.openai_api_key,
                base_url=settings.openai_base_url,
                provider_name="openai",
            )
        elif provider_name == "deepseek":
            provider = OpenAICompatibleProvider(
                api_key=settings.deepseek_api_key or settings.openai_api_key,
                base_url=settings.deepseek_base_url,
                provider_name="deepseek",
            )
        elif provider_name == "gigachat":
            provider = GigaChatProvider(
                client_id=settings.gigachat_client_id,
                client_secret=settings.gigachat_client_secret,
                scope=settings.gigachat_scope,
            )
        else:
            raise ValueError(f"Unknown provider: {provider_name}")

        self._providers[provider_name] = provider
        return provider

    def get_model_info(self, model_id: str) -> dict[str, Any]:
        if model_id not in MODEL_REGISTRY:
            return {"provider": "openai", "display_name": model_id, "context_window": 128000}
        return MODEL_REGISTRY[model_id]

    def list_models(self) -> list[dict[str, Any]]:
        return [{"id": k, **v} for k, v in MODEL_REGISTRY.items()]

    async def chat(self, model_id: str, messages: list[ChatMessage], stream: bool = False, **kwargs):
        info = self.get_model_info(model_id)
        provider = self._get_provider(info["provider"])
        return await provider.chat(messages, model_id, stream=stream, **kwargs)

    async def embed(self, texts: list[str], model_id: str | None = None) -> list[list[float]]:
        model_id = model_id or settings.embedding_model
        provider = self._get_provider("openai")
        return await provider.embed(texts, model_id)

    def estimate_cost(self, model_id: str, prompt_tokens: int, completion_tokens: int) -> float:
        prices = {
            "gpt-4o": (0.0025, 0.01),
            "gpt-4o-mini": (0.00015, 0.0006),
            "deepseek-chat": (0.00014, 0.00028),
            "GigaChat": (0.0, 0.0),
        }
        input_price, output_price = prices.get(model_id, (0.001, 0.002))
        return (prompt_tokens / 1000 * input_price) + (completion_tokens / 1000 * output_price)
