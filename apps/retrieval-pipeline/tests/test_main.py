"""Unit tests for the retrieval pipeline FastAPI HTTP layer (mocked engine)."""

from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

import main as retrieval

pytestmark = pytest.mark.anyio


@pytest.fixture
def client(monkeypatch):
    engine = MagicMock()
    engine.is_initialized = True
    engine.get_status.return_value = {
        "service": "retrieval-pipeline",
        "initialized": True,
        "vector_db_type": "chroma",
        "vector_db_ready": True,
        "chroma_ready": True,
        "bm25_ready": True,
        "documents_count": 3,
        "bm25_documents_count": 3,
        "last_updated": None,
    }
    engine.search.return_value = [
        retrieval.SearchResult(
            title="Rechnung",
            correspondent="ACME",
            date="2024-01-15",
            score=0.9,
            snippet="Zahlung frist",
            doc_id=1,
        )
    ]
    engine.status = MagicMock()
    engine.status.bm25_documents_count = 3

    monkeypatch.setattr(retrieval, "search_engine", engine)
    return TestClient(retrieval.app), engine


def test_health(client):
    c, _engine = client
    resp = c.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "healthy"


def test_status(client):
    c, _engine = client
    resp = c.get("/status")
    assert resp.status_code == 200
    assert resp.json()["service"] == "retrieval-pipeline"
    assert resp.json()["initialized"] is True


def test_search(client):
    c, engine = client
    resp = c.post("/search", json={"query": "invoice", "max_results": 5})
    assert resp.status_code == 200
    body = resp.json()
    assert len(body) == 1
    assert body[0]["title"] == "Rechnung"
    engine.search.assert_called_once()


def test_search_uninitialized(client, monkeypatch):
    c, engine = client
    engine.is_initialized = False
    resp = c.post("/search", json={"query": "q"})
    assert resp.status_code == 503


def test_search_uninitialized_global_none(client, monkeypatch):
    c, _engine = client
    monkeypatch.setattr(retrieval, "search_engine", None)
    resp = c.post("/search", json={"query": "q"})
    assert resp.status_code == 503


def test_search_error_propagates(client):
    c, engine = client
    engine.search.side_effect = Exception("search failed")
    resp = c.post("/search", json={"query": "q"})
    assert resp.status_code == 500


def test_context(client):
    c, engine = client
    resp = c.post("/context", json={"question": "invoice", "max_sources": 2})
    assert resp.status_code == 200
    body = resp.json()
    assert body["query"] == "invoice"
    assert "Rechnung" in body["context"]
    assert len(body["sources"]) == 1
    assert body["sources"][0]["title"] == "Rechnung"


def test_context_empty_results(client):
    c, engine = client
    engine.search.return_value = []
    resp = c.post("/context", json={"question": "nothing"})
    assert resp.status_code == 200
    assert resp.json()["context"] == "No relevant documents found."


def test_context_error_propagates(client):
    c, engine = client
    engine.search.side_effect = Exception("ctx failed")
    resp = c.post("/context", json={"question": "q"})
    assert resp.status_code == 500


def test_index_build_deprecated_noop(client):
    c, engine = client
    resp = c.post("/index/build", json={"documents": [{"id": 1, "title": "t", "content": "c"}]})
    assert resp.status_code == 200
    assert resp.json()["status"] == "completed"
    assert resp.json()["documents_count"] == 1
    assert resp.json()["deprecated"] is True
    # No longer drives a local build; the write path maintains the index.


def test_index_build_empty(client):
    c, engine = client
    resp = c.post("/index/build", json={"documents": []})
    assert resp.status_code == 200
    assert resp.json()["documents_count"] == 0
    assert resp.json()["deprecated"] is True


def test_status_uninitialized_global_none(client, monkeypatch):
    c, _engine = client
    monkeypatch.setattr(retrieval, "search_engine", None)
    assert c.get("/status").status_code == 503
    assert c.post("/index/build", json={"documents": [{"id": 1}]}).status_code == 503
