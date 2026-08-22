"""Unit tests for the IngestionTask."""

from unittest.mock import MagicMock

import pytest

from src.ingestion_service import IngestionService
from src.tasks import IngestionTask


def _service():
    svc = MagicMock(spec=IngestionService)
    svc.is_initialized = False
    svc.documents = []
    svc.indexed_document_ids = set()
    svc.new_document_ids = set()
    svc.status = MagicMock()
    return svc


def test_run_initializes_and_indexes_new():
    svc = _service()
    task = IngestionTask(svc)

    svc.initialize.return_value = True
    svc.new_document_ids = {"1"}
    svc.documents = [
        MagicMock(id="1", title="t", content="c", correspondent="x"),
    ]

    result = task.run()
    assert result["status"] == "completed"
    assert result["new_documents"] == 1
    assert svc.initialize.called
    svc.add_documents_to_vector_db.assert_called_once()
    assert svc.status.running is False
    assert task.running is False


def test_run_force_update():
    svc = _service()
    task = IngestionTask(svc)

    svc.initialize.return_value = True
    svc.new_document_ids = {"1", "2"}

    result = task.run(force_update=True)
    assert result["status"] == "completed"
    assert result["new_documents"] == 2
    svc.load_documents.assert_called_once_with(force_refresh=True)


def test_run_no_new_documents():
    svc = _service()
    task = IngestionTask(svc)

    svc.initialize.return_value = True
    svc.new_document_ids = set()
    svc.documents = []

    result = task.run()
    assert result["status"] == "completed"
    assert result["new_documents"] == 0
    svc.add_documents_to_vector_db.assert_not_called()


def test_run_initialization_failure_raises():
    svc = _service()
    task = IngestionTask(svc)

    svc.initialize.return_value = False
    try:
        task.run()
        pytest.fail("should have raised")
    except Exception:
        pass
    assert svc.status.running is False
    assert task.running is False


def test_run_exception_propagates():
    svc = _service()
    task = IngestionTask(svc)
    svc.initialize.return_value = True
    svc.load_documents.side_effect = Exception("load failed")

    try:
        task.run()
        pytest.fail("should have raised")
    except Exception:
        pass
    assert svc.status.running is False
    assert task.running is False
