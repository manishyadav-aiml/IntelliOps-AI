"""LLM provider abstraction. Every failure maps to a typed error with a user-safe message."""

from dataclasses import dataclass
from typing import Protocol


class LLMError(Exception):
    code = "llm_error"
    user_message = "The AI service failed."


class LLMNotConfiguredError(LLMError):
    code = "llm_not_configured"
    user_message = "The AI assistant is not configured (no API key). Other features keep working."


class LLMAuthError(LLMError):
    code = "llm_invalid_key"
    user_message = "The AI provider rejected the API key. Check the server configuration."


class LLMTimeoutError(LLMError):
    code = "llm_timeout"
    user_message = "The AI service timed out. Please try again."


class LLMRateLimitError(LLMError):
    code = "llm_rate_limited"
    user_message = "The AI service rate limit was reached. Please try again later."


class LLMProviderError(LLMError):
    code = "llm_provider_error"
    user_message = "The AI service is currently unavailable."


class LLMMalformedResponseError(LLMError):
    code = "llm_malformed_response"
    user_message = "The AI service returned an unusable answer. Please try again."


@dataclass
class LLMRequest:
    system: str
    prompt: str
    temperature: float = 0.2
    max_output_tokens: int = 2048


class LLMProvider(Protocol):
    name: str

    def generate_json(self, request: LLMRequest) -> dict:
        """Return the model's answer parsed as a JSON object, or raise an LLMError subclass."""
        ...
