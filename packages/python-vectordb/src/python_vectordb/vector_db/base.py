from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, List

from .ports import VectorDBReader, VectorDBWriter


@dataclass
class VectorDBDocument:
    id: str
    title: str
    content: str
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class VectorDBSearchResult:
    id: str
    title: str
    content: str
    score: float
    metadata: Dict[str, Any] = field(default_factory=dict)


class BaseVectorDB(VectorDBWriter, VectorDBReader, ABC):
    """Base class for concrete vector database adapters.

    Implements both the write-only (ingestion) and read-only (retrieval) ports.
    The factory wraps concrete connectors into a VectorDBCommandBus that only
    exposes the side a pipeline needs.
    """

    @abstractmethod
    def initialize(self) -> bool:
        """Initialize the vector database connection and collection."""
        pass

    @abstractmethod
    def add_documents(self, documents: List[VectorDBDocument]) -> None:
        """Add or update documents in the vector database."""
        pass

    @abstractmethod
    def search(self, query: str, top_k: int = 10) -> List[VectorDBSearchResult]:
        """Search for similar documents."""
        pass

    @abstractmethod
    def delete_collection(self) -> None:
        """Delete the entire collection."""
        pass

    @abstractmethod
    def get_status(self) -> Dict[str, Any]:
        """Return the current status of the vector database."""
        pass
