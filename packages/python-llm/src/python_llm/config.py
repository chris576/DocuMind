import os
from dataclasses import dataclass
from typing import Any, Dict


@dataclass
class LLMConfig:
    """Configuration for the LLM provider.

    Fully determined by environment variables; loaded by load_llm_config().
    """

    provider: str
    model: str
    api_key: str | None = None
    base_url: str | None = None
    anthropic_api_key: str | None = None
    custom_base_url: str | None = None
    custom_api_key: str | None = None
    custom_model: str | None = None
    opencode_base_url: str | None = None
    opencode_username: str | None = None
    opencode_password: str | None = None
    opencode_model: str | None = None

    def to_provider_config(self) -> Dict[str, Any]:
        """Build the dict expected by LLMProviderFactory.create().

        Only provider-specific keys are passed (``openai_api_key``,
        ``anthropic_api_key``, ``ollama_base_url``, ``custom_*``,
        ``opencode_*``). The providers fall back to these keys after the
        generic ``api_key``/``base_url`` lookups, so not setting the generic
        keys keeps the providers from accidentally picking up another
        provider's key.
        """
        return {
            "model": self.model,
            "openai_api_key": self.api_key,
            "anthropic_api_key": self.anthropic_api_key,
            "ollama_base_url": self.base_url,
            "custom_base_url": self.custom_base_url,
            "custom_api_key": self.custom_api_key,
            "custom_model": self.custom_model,
            "opencode_base_url": self.opencode_base_url,
            "opencode_username": self.opencode_username,
            "opencode_password": self.opencode_password,
            "opencode_model": self.opencode_model,
        }


def load_llm_config() -> LLMConfig:
    """Load LLM provider configuration from environment variables."""
    return LLMConfig(
        provider=os.getenv("LLM_PROVIDER", "ollama"),
        model=os.getenv("LLM_MODEL", "llama3.2"),
        api_key=os.getenv("OPENAI_API_KEY"),
        base_url=os.getenv("OLLAMA_BASE_URL", "http://localhost:11434"),
        anthropic_api_key=os.getenv("ANTHROPIC_API_KEY"),
        custom_base_url=os.getenv("CUSTOM_BASE_URL"),
        custom_api_key=os.getenv("CUSTOM_API_KEY"),
        custom_model=os.getenv("CUSTOM_MODEL"),
        opencode_base_url=os.getenv("OPENCODE_BASE_URL", "http://127.0.0.1:4096"),
        opencode_username=os.getenv("OPENCODE_USERNAME", "opencode"),
        opencode_password=os.getenv("OPENCODE_PASSWORD"),
        opencode_model=os.getenv("OPENCODE_MODEL"),
    )
