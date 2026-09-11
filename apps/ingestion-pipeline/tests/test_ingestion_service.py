"""Unit tests for the IngestionService orchestrator."""

from unittest.mock import MagicMock

import pytest
from python_dms import SourceDocument
from python_vectordb.vector_db import (
    IndexDocumentsCommand,
    InitializeCommand,
    VectorDBDocument,
)

from src.ingestion_service import IngestionService


def _doc(doc_id, title="T", content="C", **kwargs):
    return SourceDocument(
        id=doc_id,
        title=title,
        content=content,
        correspondent=kwargs.get("correspondent", "Corr"),
        document_type=kwargs.get("document_type", "Type"),
        storage_path=kwargs.get("storage_path", "Path"),
        created=kwargs.get("created", "2024-01-01"),
        tags=kwargs.get("tags", ["tag1"]),
        last_updated=kwargs.get("last_updated", "2024-01-02"),
        hash=kwargs.get("hash", "h"),
        metadata=kwargs.get("metadata", {}),
    )


def _service():
    provider = MagicMock()
    bus = MagicMock()
    return IngestionService(provider, bus), provider, bus


def test_initialize_ok():
    svc, _provider, bus = _service()
    bus.execute.side_effect = lambda cmd: True if isinstance(cmd, InitializeCommand) else None
    assert svc.initialize() is True
    assert svc.is_initialized is True


def test_initialize_failure():
    svc, _provider, bus = _service()
    bus.execute.side_effect = lambda cmd: False if isinstance(cmd, InitializeCommand) else None
    assert svc.initialize() is False
    assert svc.is_initialized is False


def test_initialize_exception():
    svc, _provider, bus = _service()
    bus.execute.side_effect = Exception("init failed")
    assert svc.initialize() is False


def test_check_for_updates_new_doc():
    svc, provider, _bus = _service()
    provider.check_for_updates.return_value = (True, "Latest document: 5")
    svc.indexed_document_ids = {"1", "2"}
    ok, msg = svc.check_for_updates()
    assert ok is True
    assert "5" in msg


def test_check_for_updates_no_new_doc():
    svc, provider, _bus = _service()
    provider.check_for_updates.return_value = (True, "Latest document: 2")
    svc.indexed_document_ids = {"1", "2"}
    ok, msg = svc.check_for_updates()
    assert ok is False
    assert msg == "No new documents detected"


def test_load_documents_force_refresh():
    svc, provider, _bus = _service()
    provider.fetch_documents.return_value = [_doc("1"), _doc("2")]
    docs = svc.load_documents(force_refresh=True)
    assert len(docs) == 2
    assert svc.indexed_document_ids == {"1", "2"}
    assert svc.new_document_ids == {"1", "2"}


def test_load_documents_check_new_filters_existing():
    svc, provider, _bus = _service()
    provider.fetch_documents.return_value = [_doc("1"), _doc("2")]
    svc.indexed_document_ids = {"1"}
    new_docs = svc._check_for_new_documents()
    assert [d.id for d in new_docs] == ["2"]
    assert svc.new_document_ids == {"2"}


def test_load_documents_check_new_exception_returns_empty():
    svc, provider, _bus = _service()
    provider.fetch_documents.side_effect = Exception("boom")
    assert svc._check_for_new_documents() == []


def test_add_documents_to_vector_db_initializes_if_needed():
    svc, _provider, bus = _service()
    bus.execute.side_effect = lambda cmd: True if isinstance(cmd, InitializeCommand) else None
    svc.add_documents_to_vector_db([_doc("1")])
    assert svc.is_initialized is True
    # IndexDocumentsCommand routed to bus.
    index_cmd = [c.args[0] for c in bus.execute.call_args_list if isinstance(c.args[0], IndexDocumentsCommand)]
    assert len(index_cmd) == 1
    assert isinstance(index_cmd[0].documents[0], VectorDBDocument)
    assert index_cmd[0].documents[0].metadata["correspondent"] == "Corr"


def test_add_documents_to_vector_db_initialization_fails():
    svc, _provider, bus = _service()
    bus.execute.side_effect = lambda cmd: False if isinstance(cmd, InitializeCommand) else None
    try:
        svc.add_documents_to_vector_db([_doc("1")])
        pytest.fail("should have raised")
    except Exception:
        pass


def test_get_status_uninitialized():
    svc, _provider, _bus = _service()
    status = svc.get_status()
    assert status["status"] == "uninitialized"
    assert status["documents_count"] == 0


def test_get_status_initialized():
    svc, _provider, _bus = _service()
    svc.is_initialized = True
    svc.documents = [_doc("1")]
    svc.indexed_document_ids = {"1"}
    status = svc.get_status()
    assert status["status"] == "ok"
    assert status["documents_count"] == 1
    assert status["indexed_documents"] == 1


def test_load_documents_check_new_extends_documents():
    svc, provider, _bus = _service()
    svc.documents = [_doc("1")]
    svc.indexed_document_ids = {"1"}
    provider.fetch_documents.return_value = [_doc("1"), _doc("2")]

    docs = svc.load_documents(check_new=True)
    assert [d.id for d in docs] == ["1", "2"]
    assert svc.documents[1].id == "2"


def test_load_documents_without_refresh_keeps_documents():
    svc, provider, _bus = _service()
    svc.documents = [_doc("1")]

    docs = svc.load_documents()
    assert [d.id for d in docs] == ["1"]
    provider.fetch_documents.assert_not_called()


def test_check_for_updates_non_latest_message():
    svc, provider, _bus = _service()
    provider.check_for_updates.return_value = (True, "2 neue Dokumente gefunden")
    ok, msg = svc.check_for_updates()
    assert ok is True
    assert msg == "2 neue Dokumente gefunden"
