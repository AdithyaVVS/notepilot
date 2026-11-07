from typing import Protocol


class ProviderError(Exception):
    """The LLM could not be reached or refused the request."""


class LLMProvider(Protocol):
    def generate(self, instructions: str, content: str) -> str:
        """Send instructions plus the user's content; return the model's raw text reply."""
        ...
