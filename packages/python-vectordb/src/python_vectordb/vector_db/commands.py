from dataclasses import dataclass, field
from typing import List

from .base import VectorDBDocument


@dataclass
class InitializeCommand:
    """Initialize the vector database connection and collection."""


@dataclass
class IndexDocumentsCommand:
    """Add or update documents in the vector database."""

    documents: List[VectorDBDocument] = field(default_factory=list)


@dataclass
class DeleteCollectionCommand:
    """Delete the entire collection."""


@dataclass
class DeleteDocumentsCommand:
    """Delete individual documents from the vector database by id."""

    document_ids: List[str] = field(default_factory=list)
