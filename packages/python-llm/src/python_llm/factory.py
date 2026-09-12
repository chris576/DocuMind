from .anthropic import AnthropicProvider
from .base import BaseLLMProvider
from .custom import CustomProvider
from .ollama import OllamaProvider
from .opencode import OpenCodeProvider
from .openai import OpenAIProvider


class LLMProviderFactory:
    @staticmethod
    def create(provider_type: str, config: dict) -> BaseLLMProvider:
        providers = {
            "openai": OpenAIProvider,
            "ollama": OllamaProvider,
            "anthropic": AnthropicProvider,
            "custom": CustomProvider,
            "opencode": OpenCodeProvider,
        }

        provider_class = providers.get(provider_type.lower())
        if not provider_class:
            raise ValueError(f"Unknown LLM provider: {provider_type}")

        return provider_class(config)
