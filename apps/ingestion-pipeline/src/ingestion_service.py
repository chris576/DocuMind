import logging
from datetime import datetime
from typing import List, Tuple

from python_dms import DocumentProvider, SourceDocument
from python_vectordb.vector_db import (
    IndexDocumentsCommand,
    InitializeCommand,
    VectorDBCommandBus,
    VectorDBDocument,
)

from .models import IngestionStatus

logger = logging.getLogger("ingestion.service")


class IngestionServiceError(Exception):
    """Base error for ingestion service failures."""


class VectorDBInitializationError(IngestionServiceError):
    """Raised when the vector database cannot be initialized."""


class IngestionService:
    """Orchestrates document ingestion into the vector database.

    The service is a thin coordinator: it fetches documents via a
    DocumentProvider (python-dms) and writes them through a write-only
    VectorDBCommandBus (python-vectordb). It has no knowledge of the concrete
    document API, database or embedding implementation.
    """

    def __init__(self, document_provider: DocumentProvider, vector_db: VectorDBCommandBus):
        self.document_provider = document_provider
        self.vector_db = vector_db

        self.documents: List[SourceDocument] = []
        self.indexed_document_ids: set = set()
        self.new_document_ids: set = set()
        self.is_initialized = False

        self.status = IngestionStatus()

    def initialize(self) -> bool:
        """Initialize the vector database via the write-only command bus."""
        try:
            if not self.vector_db.execute(InitializeCommand()):
                raise VectorDBInitializationError("Failed to initialize vector database")

            self.is_initialized = True
            return True
        except Exception:
            logger.exception("Error initializing ingestion service")
            self.is_initialized = False
            return False

    def check_for_updates(self) -> Tuple[bool, str]:
        """Check the document source for updates and report whether indexing is needed."""
        needs_update, message = self.document_provider.check_for_updates()

        if needs_update and message.startswith("Latest document: "):
            newest_id = message.removeprefix("Latest document: ")
            if newest_id in self.indexed_document_ids:
                return False, "No new documents detected"

        return needs_update, message

    def _check_for_new_documents(self) -> List[SourceDocument]:
        logger.info("Checking for new documents")
        try:
            api_documents = self.document_provider.fetch_documents()
            new_docs = []
            self.new_document_ids.clear()

            for doc in api_documents:
                if doc.id not in self.indexed_document_ids:
                    new_docs.append(doc)
                    self.new_document_ids.add(doc.id)
                    self.indexed_document_ids.add(doc.id)

            logger.info(f"Found {len(new_docs)} new documents to index")
            return new_docs
        except Exception:
            logger.exception("Error checking for new documents")
            return []

    def load_documents(self, force_refresh: bool = False, check_new: bool = False) -> List[SourceDocument]:
        if force_refresh:
            logger.info("Forcing full refresh from API")
            self.documents = self.document_provider.fetch_documents()
            self.indexed_document_ids = {doc.id for doc in self.documents}
            self.new_document_ids = self.indexed_document_ids.copy()
        elif check_new:
            logger.info("Checking for new documents")
            new_docs = self._check_for_new_documents()
            if new_docs:
                self.documents.extend(new_docs)
        else:
            logger.info("Loading documents without refresh")

        self.status.documents_count = len(self.documents)
        self.status.last_indexed = datetime.now().isoformat()
        return self.documents

    def add_documents_to_vector_db(self, documents: List[SourceDocument]) -> None:
        if not self.is_initialized and not self.initialize():
            raise VectorDBInitializationError("Failed to initialize ingestion service")

        vector_documents = [
            VectorDBDocument(
                id=str(doc.id),
                title=doc.title,
                content=f"{doc.title} {doc.correspondent} {doc.content}",
                metadata={
                    "title": doc.title,
                    "correspondent": doc.correspondent,
                    "created": doc.created,
                    "tags": ", ".join(doc.tags),
                    "hash": doc.hash,
                },
            )
            for doc in documents
        ]

        self.vector_db.execute(IndexDocumentsCommand(documents=vector_documents))
        logger.info(f"Added/updated {len(documents)} documents to vector database")

    def get_status(self) -> dict:
        # The write-only bus does not expose reads; the service reports its own
        # state, which is known from the writes it has performed.
        return {
            "service": "ingestion-pipeline",
            "status": "ok" if self.is_initialized else "uninitialized",
            "documents_count": len(self.documents),
            "indexed_documents": len(self.indexed_document_ids),
            "chroma_initialized": self.is_initialized,
            "last_indexed": self.status.last_indexed,
            "running": self.status.running,
            "message": self.status.message,
        }
