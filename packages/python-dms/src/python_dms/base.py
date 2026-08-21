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
    document_type: str = ""
    storage_path: str = ""
    created: str = ""
    tags: List[str] = field(default_factory=list)
    last_updated: str = ""
    hash: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class DocumentSummary:
    """Lightweight document metadata used for change detection.

    Carries only the fields needed to detect new/changed/deleted documents
    (id + content checksum + last-modified timestamp) so polling does not need
    to transfer full document content.
    """

    id: str
    checksum: str = ""
    modified: str = ""


class DocumentProvider(ABC):
    """Port for a document source.

    Concrete implementations (Paperless, Docspell, ...) are selected via
    configuration and injected into the ingestion service. Consumers never
    depend on a concrete document API.
    """

    def __init__(self, config: Dict[str, Any]) -> None:
        """Store the provider configuration.

        Concrete subclasses read the fields they need from ``config`` (url,
        token, ...). Declaring the constructor here lets the factory instantiate
        any registered provider through the base type.
        """
        self._config = config

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
    def fetch_document_summaries(self) -> List[DocumentSummary]:
        """Fetch lightweight summaries (id, checksum, modified) for change detection."""
        pass

    @abstractmethod
    def fetch_document_content(self, doc_id: str) -> str:
        """Fetch the plain-text content of a single document."""
        pass
