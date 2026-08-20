from typing import Any, Dict, Type

from .base import DocumentProvider
from .docspell import DocspellDocumentProvider
from .paperless import PaperlessDocumentProvider


class DocumentProviderFactory:
    """Creates a DocumentProvider from configuration.

    The concrete implementation is selected by the ``type`` config value (set
    via the DOCUMENT_PROVIDER environment variable in the container).
    Supported providers are registered in ``_REGISTRY``; adding a new one only
    requires a new class and a registry entry.
    """

    _REGISTRY: Dict[str, Type[DocumentProvider]] = {
        "paperless": PaperlessDocumentProvider,
        "docspell": DocspellDocumentProvider,
    }

    @staticmethod
    def create(config: Dict[str, Any]) -> DocumentProvider:
        provider = config.get("type", "paperless")

        provider_class = DocumentProviderFactory._REGISTRY.get(provider)
        if provider_class is None:
            supported = ", ".join(sorted(DocumentProviderFactory._REGISTRY))
            raise ValueError(
                f"Unknown document provider: {provider}. "
                f"Supported providers: {supported}"
            )

        return provider_class(config)