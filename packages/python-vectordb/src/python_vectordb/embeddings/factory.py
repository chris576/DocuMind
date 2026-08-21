from typing import Any, Dict, Type

from .base import EmbeddingProvider
from .sentence_transformer import SentenceTransformerEmbeddingProvider


class EmbeddingProviderFactory:
    """Creates an EmbeddingProvider from configuration.

    The concrete implementation is selected by the ``embedding_provider`` config
    value (set via the EMBEDDING_PROVIDER environment variable in the
    container). Supported implementations are registered in ``_REGISTRY``;
    adding a new one only requires a new class and a registry entry.
    """

    _REGISTRY: Dict[str, Type[EmbeddingProvider]] = {
        "sentence_transformer": SentenceTransformerEmbeddingProvider,
    }

    @staticmethod
    def create(config: Dict[str, Any]) -> EmbeddingProvider:
        provider = config.get("embedding_provider", "sentence_transformer")
        model = config.get(
            "embedding_model", "paraphrase-multilingual-MiniLM-L12-v2"
        )

        provider_class = EmbeddingProviderFactory._REGISTRY.get(provider)
        if provider_class is None:
            supported = ", ".join(sorted(EmbeddingProviderFactory._REGISTRY))
            raise ValueError(
                f"Unknown embedding provider: {provider}. "
                f"Supported providers: {supported}"
            )

        return provider_class(model)
