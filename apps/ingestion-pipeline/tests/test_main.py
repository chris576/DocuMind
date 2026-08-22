"""Unit tests for the ingestion pipeline FastAPI HTTP layer (mocked services).

These tests verify the REST endpoints and the compatibility handshake with the
retrieval pipeline. The write-only CQRS bus itself is exercised through
IngestionService; here we mock the service/task to focus on HTTP wiring.
"""

from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi.testclient import TestClient

import main as ingestion

pytestmark = pytest.mark.anyio


@pytest.fixture
def client(monkeypatch):
    """Provide a TestClient with mocked service + task globals."""
    service = MagicMock()
    service.is_initialized = True
    service.get_status.return_value = {
        "service": "ingestion-pipeline",
        "status": "ok",
        "documents_count": 0,
        "indexed_documents": 0,
        "chroma_initialized": True,
        "last_indexed": None,
        "running": False,
        "message": "",
    }
    service.check_for_updates.return_value = (True, "Latest document: 5")

    task = MagicMock()
    task.running = False
    task.run.return_value = {
        "status": "completed",
        "new_documents": 2,
        "total_documents": 2,
    }

    monkeypatch.setattr(ingestion, "ingestion_service", service)
    monkeypatch.setattr(ingestion, "ingestion_task", task)
    monkeypatch.setattr(ingestion, "_push_documents_to_retrieval", AsyncMock())

    return TestClient(ingestion.app), service, task


def test_health(client):
    c, _svc, _task = client
    resp = c.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "healthy"


def test_status(client):
    c, _svc, _task = client
    resp = c.get("/status")
    assert resp.status_code == 200
    assert resp.json()["service"] == "ingestion-pipeline"


def test_ingest_background(client):
    c, _svc, task = client
    resp = c.post("/ingest", json={"force": False, "check_new": True})
    assert resp.status_code == 200
    assert resp.json()["status"] == "started"
    # BackgroundTasks execute synchronously inside TestClient after the
    # response is produced, so the ingest run is dispatched here.
    task.run.assert_called_once_with(force_update=False, check_new=True)


def test_ingest_rejects_running(client):
    c, _svc, task = client
    task.running = True
    resp = c.post("/ingest", json={})
    assert resp.status_code == 200
    assert resp.json()["status"] == "running"


def test_ingest_sync(client):
    c, _svc, task = client
    resp = c.post("/ingest/sync", json={"force": True})
    assert resp.status_code == 200
    assert resp.json()["status"] == "completed"
    task.run.assert_called_once_with(force_update=True, check_new=False)


def test_ingest_sync_pushes_to_retrieval(client, monkeypatch):
    c, _svc, task = client
    # Result "completed" must trigger the retrieval push (http.post_json).
    push = AsyncMock()
    monkeypatch.setattr(ingestion, "_push_documents_to_retrieval", push)

    c.post("/ingest/sync", json={"force": True})
    push.assert_awaited_once()


def test_check(client):
    c, _svc, _task = client
    resp = c.post("/check")
    assert resp.status_code == 200
    assert resp.json()["needs_update"] is True
