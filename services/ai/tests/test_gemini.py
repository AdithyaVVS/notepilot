import json

import httpx
import pytest

from app.llm.base import ProviderError
from app.llm.gemini import GeminiProvider

KEY = "test-key-123456"


def provider_with(handler):
    client = httpx.Client(transport=httpx.MockTransport(handler))
    return GeminiProvider(KEY, "gemini-test", client=client)


def test_sends_key_in_header_and_returns_text():
    seen = {}

    def handler(request):
        seen["url"] = str(request.url)
        seen["key"] = request.headers.get("x-goog-api-key")
        seen["body"] = json.loads(request.content)
        reply = {
            "candidates": [
                {
                    "content": {
                        "parts": [
                            {"text": "private reasoning", "thought": True},
                            {"text": '{"summary": "ok"}'},
                        ]
                    }
                }
            ]
        }
        return httpx.Response(200, json=reply)

    text = provider_with(handler).generate("be strict", "<note>hi</note>")

    assert text == '{"summary": "ok"}'
    assert seen["key"] == KEY
    assert KEY not in seen["url"]
    assert "gemini-test:generateContent" in seen["url"]
    assert seen["body"]["system_instruction"]["parts"][0]["text"] == "be strict"
    assert seen["body"]["contents"][0]["parts"][0]["text"] == "<note>hi</note>"
    assert seen["body"]["generationConfig"]["responseMimeType"] == "application/json"


def test_http_error_becomes_provider_error_without_leaking_key():
    def handler(request):
        return httpx.Response(429, json={"error": {"message": f"quota for {KEY}"}})

    with pytest.raises(ProviderError) as error:
        provider_with(handler).generate("x", "y")
    assert "429" in str(error.value)
    assert KEY not in str(error.value)


def test_unexpected_response_shape_becomes_provider_error():
    def handler(request):
        return httpx.Response(200, json={"candidates": []})

    with pytest.raises(ProviderError):
        provider_with(handler).generate("x", "y")


def test_network_error_becomes_provider_error():
    def handler(request):
        raise httpx.ConnectTimeout("too slow")

    with pytest.raises(ProviderError):
        provider_with(handler).generate("x", "y")
