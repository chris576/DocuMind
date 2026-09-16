"""Unit tests for the extraction pipeline FastAPI HTTP layer (mocked service)."""
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi.testclient import TestClient

import main as extraction

pytestmark = pytest.mark.anyio


@pytest.fixture
def client(monkeypatch):
    svc = MagicMock()
    svc.ready = True
    svc.get_status.return_value = {
        "service": "extraction-pipeline",
        "ready": True,
        "table": "document_facts",
    }
    svc.run = AsyncMock(return_value={"processed": 1, "failed": 0, "pending_total": 1})
    monkeypatch.setattr(extraction, "extraction_service", svc)
    return TestClient(extraction.app), svc


def test_health(client):
    c, _ = client
    resp = c.get("/health")
    assert resp.status_code == 200
    assert resp.json()["service"] == "extraction-pipeline"


def test_status(client):
    c, _ = client
    resp = c.get("/status")
    assert resp.status_code == 200
    assert resp.json()["ready"] is True


def test_extract(client):
    c, svc = client
    resp = c.post("/extract", json={"limit": 3})
    assert resp.status_code == 200
    assert resp.json()["processed"] == 1
    svc.run.assert_awaited_once()


def test_extract_uninitialized(client, monkeypatch):
    c, _ = client
    monkeypatch.setattr(extraction, "extraction_service", None)
    resp = c.post("/extract", json={})
    assert resp.status_code == 503
