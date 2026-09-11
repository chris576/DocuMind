"""Unit tests for the ingestion pipeline FastAPI HTTP layer (mocked coordinator)."""

from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi.testclient import TestClient

import main as ingestion

pytestmark = pytest.mark.anyio


@pytest.fixture
def client(monkeypatch):
    """Provide a TestClient with a mocked multi-target coordinator."""
    target = MagicMock()
    target.id = "paperless"
    target.collection = "paperless"
    target.service = MagicMock()
    target.service.is_initialized = True
    target.service.documents = []
    target.service.indexed_document_ids = set()
    target.service.get_status.return_value = {
        "service": "ingestion-pipeline",
        "status": "ok",
        "documents_count": 0,
        "indexed_documents": 0,
        "chroma_initialized": True,
        "last_indexed": None,
        "running": False,
        "message": "",
    }
    target.service.check_for_updates.return_value = (True, "Latest document: 5")

    coordinator = MagicMock()
    coordinator.targets = [target]
    coordinator.running = False
    coordinator.get_status.return_value = {
        "service": "ingestion-pipeline",
        "status": "ok",
        "documents_count": 0,
        "indexed_documents": 0,
        "targets": [],
        "running": False,
        "message": "",
    }
    coordinator.check_for_updates.return_value = (True, "Latest document: 5")
    coordinator.run.return_value = {
        "status": "completed",
        "new_documents": 2,
        "total_documents": 2,
        "targets": [],
        "errors": [],
    }

    monkeypatch.setattr(ingestion, "coordinator", coordinator)
    monkeypatch.setattr(ingestion, "_push_documents_to_retrieval", AsyncMock())

    return TestClient(ingestion.app), coordinator


def test_health(client):
    c, _coordinator = client
    resp = c.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "healthy"


def test_status(client):
    c, _coordinator = client
    resp = c.get("/status")
    assert resp.status_code == 200
    assert resp.json()["service"] == "ingestion-pipeline"


def test_ingest_background(client):
    c, coordinator = client
    resp = c.post("/ingest", json={"force": False, "check_new": True})
    assert resp.status_code == 200
    assert resp.json()["status"] == "started"
    coordinator.run.assert_called_once_with(force_update=False, check_new=True)


def test_ingest_rejects_running(client):
    c, coordinator = client
    coordinator.running = True
    resp = c.post("/ingest", json={})
    assert resp.status_code == 200
    assert resp.json()["status"] == "running"


def test_ingest_sync(client):
    c, coordinator = client
    resp = c.post("/ingest/sync", json={"force": True})
    assert resp.status_code == 200
    assert resp.json()["status"] == "completed"
    coordinator.run.assert_called_once_with(force_update=True, check_new=False)


def test_ingest_sync_pushes_to_retrieval(client, monkeypatch):
    c, _coordinator = client
    push = AsyncMock()
    monkeypatch.setattr(ingestion, "_push_documents_to_retrieval", push)

    c.post("/ingest/sync", json={"force": True})
    push.assert_awaited_once()


def test_check(client):
    c, _coordinator = client
    resp = c.post("/check")
    assert resp.status_code == 200
    assert resp.json()["needs_update"] is True


def test_status_uninitialized(monkeypatch):
    monkeypatch.setattr(ingestion, "coordinator", None)
    c = TestClient(ingestion.app)
    assert c.get("/status").status_code == 503


def test_ingest_uninitialized(monkeypatch):
    monkeypatch.setattr(ingestion, "coordinator", None)
    c = TestClient(ingestion.app)
    assert c.post("/ingest", json={}).status_code == 503


def test_ingest_sync_uninitialized(monkeypatch):
    monkeypatch.setattr(ingestion, "coordinator", None)
    c = TestClient(ingestion.app)
    assert c.post("/ingest/sync", json={}).status_code == 503


def test_check_uninitialized(monkeypatch):
    monkeypatch.setattr(ingestion, "coordinator", None)
    c = TestClient(ingestion.app)
    assert c.post("/check").status_code == 503


def test_ingest_sync_error_propagates(client):
    c, coordinator = client
    coordinator.run.side_effect = Exception("boom")
    with pytest.raises(Exception, match="boom"):
        c.post("/ingest/sync", json={})


async def test_push_documents_no_docs(monkeypatch):
    target = MagicMock()
    target.service = MagicMock()
    target.service.documents = []
    coordinator = MagicMock()
    coordinator.targets = [target]
    monkeypatch.setattr(ingestion, "coordinator", coordinator)
    result = await ingestion._push_documents_to_retrieval()
    assert result is None
