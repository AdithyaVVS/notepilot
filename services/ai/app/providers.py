from functools import lru_cache

from app.config import settings
from app.llm.base import LLMProvider, ProviderError
from app.llm.fake import FakeProvider
from app.llm.gemini import GeminiProvider


class UnavailableProvider:
    """Stands in when the real provider isn't configured. Fails only when used,
    so sample mode keeps working."""

    def __init__(self, reason: str):
        self.reason = reason

    def generate(self, instructions: str, content: str) -> str:
        raise ProviderError(self.reason)


@lru_cache
def _gemini(api_key: str, model: str) -> GeminiProvider:
    return GeminiProvider(api_key, model)


def get_provider() -> LLMProvider:
    if settings.llm_provider == "fake":
        return FakeProvider()
    if settings.llm_provider == "gemini":
        if not settings.gemini_api_key:
            return UnavailableProvider("GEMINI_API_KEY is not set")
        return _gemini(settings.gemini_api_key, settings.gemini_model)
    return UnavailableProvider(f"Unknown LLM provider: {settings.llm_provider}")
