"""Unit tests for the VectorDB command bus (CQRS routing)."""
from unittest.mock import MagicMock

import pytest

from python_vectordb.vector_db.base import VectorDBDocument
from python_vectordb.vector_db.bus import (
    ReadOnlyError,
    UnknownCommandError,
    UnknownQueryError,
    VectorDBCommandBus,
    WriteOnlyError,
)
from python_vectordb.vector_db.commands import (
    DeleteCollectionCommand,
    DeleteDocumentsCommand,
    IndexDocumentsCommand,
    InitializeCommand,
)
from python_vectordb.vector_db.queries import GetStatusQuery, HybridSearchQuery, SearchQuery


def _writer():
    return MagicMock()


def _reader():
    return MagicMock()


def test_execute_initialize():
    w = _writer()
    bus = VectorDBCommandBus(writer=w)
    w.initialize.return_value = True
    assert bus.execute(InitializeCommand()) is True
    w.initialize.assert_called_once()


def test_execute_index_documents():
    w = _writer()
    bus = VectorDBCommandBus(writer=w)
    docs = [VectorDBDocument(id="1", title="t", content="c")]
    bus.execute(IndexDocumentsCommand(documents=docs))
    w.add_documents.assert_called_once_with(docs)


def test_execute_delete_collection():
    w = _writer()
    bus = VectorDBCommandBus(writer=w)
    bus.execute(DeleteCollectionCommand())
    w.delete_collection.assert_called_once()


def test_execute_delete_documents():
    w = _writer()
    bus = VectorDBCommandBus(writer=w)
    bus.execute(DeleteDocumentsCommand(document_ids=["1", "2"]))
    w.delete_documents.assert_called_once_with(["1", "2"])


def test_execute_unknown_command():
    bus = VectorDBCommandBus(writer=_writer())
    with pytest.raises(UnknownCommandError):
        bus.execute("nope")


def test_execute_read_only_raises():
    bus = VectorDBCommandBus(reader=_reader())
    with pytest.raises(ReadOnlyError):
        bus.execute(InitializeCommand())


def test_ask_search():
    r = _reader()
    bus = VectorDBCommandBus(reader=r)
    r.search.return_value = []
    assert bus.ask(SearchQuery(query="q", top_k=5)) == []
    r.search.assert_called_once_with("q", 5)


def test_ask_get_status():
    r = _reader()
    bus = VectorDBCommandBus(reader=r)
    bus.ask(GetStatusQuery())
    r.get_status.assert_called_once()


def test_ask_hybrid_search():
    r = _reader()
    bus = VectorDBCommandBus(reader=r)
    r.hybrid_search.return_value = []
    assert bus.ask(HybridSearchQuery(query="q", top_k=7)) == []
    r.hybrid_search.assert_called_once_with("q", 7)


def test_ask_unknown_query():
    bus = VectorDBCommandBus(reader=_reader())
    with pytest.raises(UnknownQueryError):
        bus.ask("nope")


def test_ask_write_only_raises():
    bus = VectorDBCommandBus(writer=_writer())
    with pytest.raises(WriteOnlyError):
        bus.ask(SearchQuery(query="q"))
