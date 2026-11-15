"""Gemini (Google Generative Language REST API) provider.

Uses plain HTTPS through an injectable `transport` so tests never touch the network and no extra SDK
is required. The API key is sent in the `x-goog-api-key` header (never in the URL) and is never logged.
The model id is configurable (GEMINI_MODEL); check Google's current model list before deploying.
"""

import json
import re
import socket
import urllib.error
import urllib.request
from collections.abc import Callable

from app.ai.llm_provider import (
    LLMAuthError,
    LLMMalformedResponseError,
    LLMNotConfiguredError,
    LLMProviderError,
    LLMRateLimitError,
    LLMRequest,
    LLMTimeoutError,
)

BASE_URL = "https://generativelanguage.googleapis.com/v1beta/models"
Transport = Callable[[str, dict[str, str], bytes, float], tuple[int, str]]


def urllib_transport(url: str, headers: dict[str, str], body: bytes, timeout: float) -> tuple[int, str]:
    request = urllib.request.Request(url, data=body, headers=headers, method="POST")  # noqa: S310 (fixed https URL)
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:  # noqa: S310
            return response.status, response.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as exc:
        return exc.code, exc.read().decode("utf-8", errors="replace")
    except (TimeoutError, socket.timeout) as exc:
        raise LLMTimeoutError() from exc
    except urllib.error.URLError as exc:
        if isinstance(exc.reason, (TimeoutError, socket.timeout)):
            raise LLMTimeoutError() from exc
        raise LLMProviderError() from exc


_FENCE = re.compile(r"^```(?:json)?\s*|\s*```$", re.IGNORECASE)


class GeminiProvider:
    name = "gemini"

    def __init__(self, api_key: str, model: str = "gemini-2.0-flash", timeout: float = 30.0,
                 transport: Transport | None = None) -> None:
        self.api_key = api_key
        self.model = model
        self.timeout = timeout
        self._transport = transport or urllib_transport

    def generate_json(self, request: LLMRequest) -> dict:
        if not self.api_key:
            raise LLMNotConfiguredError()
        body = json.dumps(
            {
                "systemInstruction": {"parts": [{"text": request.system}]},
                "contents": [{"role": "user", "parts": [{"text": request.prompt}]}],
                "generationConfig": {
                    "temperature": request.temperature,
                    "maxOutputTokens": request.max_output_tokens,
                    "responseMimeType": "application/json",
                },
            }
        ).encode("utf-8")
        headers = {"Content-Type": "application/json", "x-goog-api-key": self.api_key}
        status, text = self._transport(f"{BASE_URL}/{self.model}:generateContent", headers, body, self.timeout)
        self._raise_for_status(status, text)
        return self._parse(text)

    @staticmethod
    def _raise_for_status(status: int, text: str) -> None:
        if status == 200:
            return
        if status in (401, 403) or (status == 400 and ("API_KEY_INVALID" in text or "API key not valid" in text)):
            raise LLMAuthError()
        if status == 429:
            raise LLMRateLimitError()
        raise LLMProviderError()

    @staticmethod
    def _parse(text: str) -> dict:
        try:
            payload = json.loads(text)
            parts = payload["candidates"][0]["content"]["parts"]
            answer = "".join(part.get("text", "") for part in parts).strip()
        except (ValueError, KeyError, IndexError, TypeError, AttributeError) as exc:
            raise LLMMalformedResponseError() from exc
        if not answer:
            raise LLMMalformedResponseError()
        try:
            data = json.loads(_FENCE.sub("", answer))
        except ValueError as exc:
            raise LLMMalformedResponseError() from exc
        if not isinstance(data, dict):
            raise LLMMalformedResponseError()
        return data
