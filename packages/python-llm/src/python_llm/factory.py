from .base import BaseLLMProvider
from .openai import OpenAIProvider
from .ollama import OllamaProvider
from .anthropic import AnthropicProvider
from .custom import CustomProvider


class LLMProviderFactory:
    @staticmethod
    def create(provider_type: str, config: dict) -> BaseLLMProvider:
        providers = {
            "openai": OpenAIProvider,
            "ollama": OllamaProvider,
            "anthropic": AnthropicProvider,
            "custom": CustomProvider,
        }

        provider_class = providers.get(provider_type.lower())
        if not provider_class:
            raise ValueError(f"Unknown LLM provider: {provider_type}")

        return provider_class(config)
