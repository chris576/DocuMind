from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any, Dict, List

if TYPE_CHECKING:
    from .base import VectorDBDocument, VectorDBSearchResult


class VectorDBWriter(ABC):
    """Write-only port for the vector database (used by the ingestion pipeline)."""

    @abstractmethod
    def initialize(self) -> bool:
        """Initialize the vector database connection and collection."""
        pass

    @abstractmethod
    def add_documents(self, documents: List[VectorDBDocument]) -> None:
        """Add or update documents in the vector database."""
        pass

    @abstractmethod
    def delete_collection(self) -> None:
        """Delete the entire collection."""
        pass


class VectorDBReader(ABC):
    """Read-only port for the vector database (used by the retrieval pipeline)."""

    @abstractmethod
    def search(self, query: str, top_k: int = 10) -> List[VectorDBSearchResult]:
        """Search for similar documents."""
        pass

    @abstractmethod
    def get_status(self) -> Dict[str, Any]:
        """Return the current status of the vector database."""
        pass