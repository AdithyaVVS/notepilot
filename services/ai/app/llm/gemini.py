import httpx

from app.llm.base import ProviderError

BASE_URL = "https://generativelanguage.googleapis.com/v1beta/models"


class GeminiProvider:
    def __init__(self, api_key: str, model: str, client=None, timeout: float = 30.0):
        self.api_key = api_key
        self.model = model
        self.client = client
        self.timeout = timeout

    def generate(self, instructions: str, content: str) -> str:
        body = {
            "system_instruction": {"parts": [{"text": instructions}]},
            "contents": [{"role": "user", "parts": [{"text": content}]}],
            "generationConfig": {
                "temperature": 0.2,
                "maxOutputTokens": 4096,
                "responseMimeType": "application/json",
            },
        }
        http = self.client or httpx
        try:
            response = http.post(
                f"{BASE_URL}/{self.model}:generateContent",
                headers={"x-goog-api-key": self.api_key},
                json=body,
                timeout=self.timeout,
            )
        except httpx.HTTPError as exc:
            raise ProviderError(f"Could not reach Gemini: {type(exc).__name__}") from exc

        if response.status_code != 200:
            raise ProviderError(f"Gemini returned HTTP {response.status_code}")

        try:
            parts = response.json()["candidates"][0]["content"]["parts"]
            text = "".join(p.get("text", "") for p in parts if not p.get("thought"))
        except (KeyError, IndexError, TypeError, ValueError):
            raise ProviderError("Unexpected response shape from Gemini")
        if not text.strip():
            raise ProviderError("Gemini returned an empty reply")
        return text
