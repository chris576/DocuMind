from .base import DocumentProvider, SourceDocument
from .docspell import DocspellDocumentProvider
from .factory import DocumentProviderFactory
from .paperless import PaperlessDocumentProvider

__all__ = [
    "SourceDocument",
    "DocumentProvider",
    "PaperlessDocumentProvider",
    "DocspellDocumentProvider",
    "DocumentProviderFactory",
]