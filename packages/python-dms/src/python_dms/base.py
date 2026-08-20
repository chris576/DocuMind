import hashlib
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, List, Tuple

logger = logging.getLogger("python_dms.base")


@dataclass
class SourceDocument:
    """A document fetched from an external document source.

    Generic across providers (Paperless-ngx, Docspell, ...). Provider-specific
    metadata is normalized into these fields; unmapped attributes default to
    empty values.
    """

    id: str
    title: str
    content: str
    correspondent: str = ""
    created: str = ""
    tags: List[str] = field(default_factory=list)
    last_updated: str = ""
    hash: str = ""


class DocumentProvider(ABC):
    """Port for a document source.

    Concrete implementations (Paperless, Docspell, ...) are selected via
    configuration and injected into the ingestion service. Consumers never
    depend on a concrete document API.
    """

    @staticmethod
    def compute_hash(doc: Dict[str, Any]) -> str:
        content = f"{doc.get('title', '')}{doc.get('content', '')}{doc.get('correspondent', '')}"
        return hashlib.sha256(content.encode()).hexdigest()

    @abstractmethod
    def check_for_updates(self) -> Tuple[bool, str]:
        """Check the source for updates and report whether indexing is needed."""
        pass

    @abstractmethod
    def fetch_documents(self) -> List[SourceDocument]:
        """Fetch and normalize all documents from the source."""
        pass

    @abstractmethod
    def fetch_document_content(self, doc_id: str) -> str:
        """Fetch the plain-text content of a single document."""
        pass