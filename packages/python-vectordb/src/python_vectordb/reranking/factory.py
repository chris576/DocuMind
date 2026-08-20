from typing import Any, Dict, Type

from .base import Reranker
from .cross_encoder import CrossEncoderReranker


class RerankerFactory:
    """Creates a Reranker from configuration.

    The concrete implementation is selected by the ``reranker_provider`` config
    value (set via the RERANKER_PROVIDER environment variable in the
    container). Supported implementations are registered in ``_REGISTRY``.
    """

    _REGISTRY: Dict[str, Type[Reranker]] = {
        "cross_encoder": CrossEncoderReranker,
    }

    @staticmethod
    def create(config: Dict[str, Any]) -> Reranker:
        provider = config.get("reranker_provider", "cross_encoder")
        model = config.get(
            "cross_encoder_model", "cross-encoder/ms-marco-MiniLM-L-6-v2"
        )

        reranker_class = RerankerFactory._REGISTRY.get(provider)
        if reranker_class is None:
            supported = ", ".join(sorted(RerankerFactory._REGISTRY))
            raise ValueError(
                f"Unknown reranker provider: {provider}. "
                f"Supported providers: {supported}"
            )

        return reranker_class(model)