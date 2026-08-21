from typing import Any

from .commands import (
    DeleteCollectionCommand,
    DeleteDocumentsCommand,
    IndexDocumentsCommand,
    InitializeCommand,
)
from .ports import VectorDBReader, VectorDBWriter
from .queries import GetStatusQuery, SearchQuery


class ReadOnlyError(RuntimeError):
    """Raised when a write command is executed on a read-only bus."""


class WriteOnlyError(RuntimeError):
    """Raised when a read query is asked on a write-only bus."""


class UnknownCommandError(RuntimeError):
    """Raised when the bus receives an unsupported command."""


class UnknownQueryError(RuntimeError):
    """Raised when the bus receives an unsupported query."""


class VectorDBCommandBus:
    """CQRS-style dispatcher for vector database access.

    Pipelines only interact with this bus by sending Command/Query objects and
    processing the return value. The bus internally routes to the write-only or
    read-only port, so callers never depend on a concrete database or embedding
    implementation.

    - A bus created for ingestion only has a writer: ``execute()`` works,
      ``ask()`` raises ``WriteOnlyError``.
    - A bus created for retrieval only has a reader: ``ask()`` works,
      ``execute()`` raises ``ReadOnlyError``.
    """

    def __init__(
        self,
        writer: VectorDBWriter | None = None,
        reader: VectorDBReader | None = None,
    ):
        self._writer = writer
        self._reader = reader

    def execute(self, command: Any) -> Any:
        """Execute a write command (ingestion side)."""
        if self._writer is None:
            raise ReadOnlyError(
                "This vector database bus is read-only; write commands are not allowed"
            )
        if isinstance(command, InitializeCommand):
            return self._writer.initialize()
        if isinstance(command, IndexDocumentsCommand):
            return self._writer.add_documents(command.documents)
        if isinstance(command, DeleteCollectionCommand):
            return self._writer.delete_collection()
        if isinstance(command, DeleteDocumentsCommand):
            return self._writer.delete_documents(command.document_ids)
        raise UnknownCommandError(f"Unsupported command: {type(command).__name__}")

    def ask(self, query: Any) -> Any:
        """Ask a read query (retrieval side)."""
        if self._reader is None:
            raise WriteOnlyError(
                "This vector database bus is write-only; read queries are not allowed"
            )
        if isinstance(query, SearchQuery):
            return self._reader.search(query.query, query.top_k)
        if isinstance(query, GetStatusQuery):
            return self._reader.get_status()
        raise UnknownQueryError(f"Unsupported query: {type(query).__name__}")
