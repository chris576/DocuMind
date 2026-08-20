import logging
from typing import Any, Dict, List

from .base import DocumentProvider, SourceDocument

logger = logging.getLogger("python_dms.docspell")


class DocspellDocumentProvider(DocumentProvider):
    """Document provider backed by the Docspell REST API.

    Placeholder: the Docspell API integration is not implemented yet. The class
    exists so the factory can select it and so the ingestion service can be
    written against the generic DocumentProvider port.
    """

    def __init__(self, config: Dict[str, Any]):
        self.base_url = config.get("url") or config.get("document_provider_url")
        self.token = config.get("token") or config.get("document_provider_token")

        if not self.base_url or not self.token:
            raise ValueError("Missing document provider configuration (url/token)")

    def check_for_updates(self):
        raise NotImplementedError("Docspell document provider is not implemented yet")

    def fetch_documents(self) -> List[SourceDocument]:
        raise NotImplementedError("Docspell document provider is not implemented yet")

    def fetch_document_content(self, doc_id: str) -> str:
        raise NotImplementedError("Docspell document provider is not implemented yet")