from app.config import settings
from app.llm.base import LLMProvider, ProviderError
from app.llm.fake import FakeProvider


def get_provider() -> LLMProvider:
    if settings.llm_provider == "fake":
        return FakeProvider()
    raise ProviderError(f"Unknown LLM provider: {settings.llm_provider}")
