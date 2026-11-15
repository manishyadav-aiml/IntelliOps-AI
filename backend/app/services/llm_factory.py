from app.ai.gemini_provider import GeminiProvider
from app.ai.llm_provider import LLMProvider
from app.core.config import Settings


def create_provider(settings: Settings) -> LLMProvider | None:
    """The provider is built server-side only; its key is never sent to the frontend."""
    if settings.llm_provider == "gemini":
        return GeminiProvider(settings.gemini_api_key, settings.gemini_model, settings.llm_timeout_seconds)
    return None


def llm_configured(settings: Settings) -> bool:
    return settings.llm_provider == "gemini" and bool(settings.gemini_api_key)
