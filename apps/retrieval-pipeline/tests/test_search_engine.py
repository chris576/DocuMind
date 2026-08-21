"""Unit tests for the retrieval SearchEngine (mocked dependencies)."""
from unittest.mock import MagicMock, patch

import pytest

from src.models import SearchRequest
from src.search_engine import SearchEngine


def _engine(**kwargs):
    config = {
        "vector_db_type": "chroma",
        "collection_name": "docs",
        "embedding_model": "m",
        "embedding_provider": "st",
    }
    config.update(kwargs)
    return SearchEngine(config)


def test_vector_db_config_variants():
    assert _engine(vector_db_type="chroma")._vector_db_config()["type"] == "chroma"
    assert _engine(vector_db_type="qdrant", qdrant_url="http://q")._vector_db_config()["type"] == "qdrant"
    assert _engine(vector_db_type="pgvector", pgvector_url="pg://x")._vector_db_config()["type"] == "pgvector"


@patch("src.search_engine.RerankerFactory.create")
def test_initialize_creates_reranker(mock_factory):
    mock_factory.return_value = MagicMock()
    engine = _engine()
    assert engine.initialize() is True
    assert engine.is_initialized is True
    mock_factory.assert_called_once()


@patch("src.search_engine.RerankerFactory.create")
def test_initialize_failure(mock_factory):
    mock_factory.side_effect = Exception("no model")
    engine = _engine()
    assert engine.initialize() is False
    assert engine.is_initialized is False


@patch("src.search_engine.RerankerFactory.create")
@patch("src.search_engine.VectorDBFactory.create_reader")
def test_setup_vector_db(mock_factory, mock_reranker):
    bus = MagicMock()
    bus.ask.return_value = {"ready": True, "document_count": 5}
    mock_factory.return_value = bus
    mock_reranker.return_value = MagicMock()

    engine = _engine()
    assert engine.setup_vector_db() is True
    assert engine.status.chroma_ready is True
    assert engine.status.documents_count == 5


@patch("src.search_engine.RerankerFactory.create")
def test_setup_bm25_builds_index(mock_reranker):
    mock_reranker.return_value = MagicMock()
    engine = _engine(bm25_file="/tmp/bm25_test.pkl")
    docs = [
        {"id": 1, "title": "Rechnung", "content": "Zahlung frist", "correspondent": "ACME"},
        {"id": 2, "title": "Vertrag", "content": "Laufzeit", "correspondent": "Firma"},
    ]
    assert engine.setup_bm25(docs) is True
    assert engine.bm25_initialized is True
    assert engine.status.bm25_documents_count == 2


@patch("src.search_engine.RerankerFactory.create")
def test_setup_bm25_empty_returns_false(mock_reranker):
    engine = _engine()
    assert engine.setup_bm25([]) is False


def test_keyword_search_requires_bm25():
    engine = _engine()
    try:
        engine.keyword_search("q")
        pytest.fail("should have raised")
    except Exception:
        pass
    try:
        engine.semantic_search("q")
        pytest.fail("should have raised")
    except Exception:
        pass


@patch("src.search_engine.RerankerFactory.create")
def test_semantic_search_requires_vectordb(mock_reranker):
    engine = _engine()
    try:
        engine.semantic_search("q")
        pytest.fail("should have raised")
    except Exception:
        pass


@patch("src.search_engine.RerankerFactory.create")
def test_create_snippet(mock_reranker):
    engine = _engine()
    snippet = engine.create_snippet("invoice payment", "The invoice requires payment. Delivery was on time. Regards.")
    assert "invoice" in snippet or "payment" in snippet


def test_create_snippet_empty():
    engine = _engine()
    assert engine.create_snippet("q", "") == ""


@patch("src.search_engine.RerankerFactory.create")
def test_rerank_results_empty(mock_reranker):
    engine = _engine()
    assert engine.rerank_results("q", []) == []


@patch("src.search_engine.RerankerFactory.create")
def test_rerank_results_fallback_on_error(mock_reranker):
    mock_reranker.return_value = MagicMock()
    engine = _engine()
    results = [{"title": "a"}, {"title": "b"}]
    out = engine.rerank_results("q", results, top_k=1)
    assert len(out) == 1
    assert out[0].get("cross_score") == 0.5


def test_get_status():
    engine = _engine()
    status = engine.get_status()
    assert status["service"] == "retrieval-pipeline"
    assert status["initialized"] is False


def test_hybrid_search_combines_keyword_and_semantic():
    engine = _engine()
    engine.bm25_initialized = True
    engine.bm25 = MagicMock()
    engine.bm25.get_scores.return_value = [0.8, 0.4]
    engine.documents = [
        {"id": 1, "title": "Rechnung", "content": "Zahlung", "created": "2024-01-01"},
        {"id": 2, "title": "Vertrag", "content": "Laufzeit", "created": "2024-02-01"},
    ]
    engine.vector_db = MagicMock()
    engine.vector_db.ask.return_value = [
        MagicMock(id="2", title="Vertrag", content="Laufzeit", score=0.9,
                  metadata={"correspondent": "Firma", "created": "2024-02-01"}),
    ]

    results = engine.hybrid_search("Vertrag", top_k=5)
    assert len(results) >= 1
    assert any(r["title"] == "Vertrag" for r in results)


@patch("src.search_engine.RerankerFactory.create")
def test_hybrid_search_both_fail_raises(mock_reranker):
    engine = _engine()
    mock_reranker.return_value = MagicMock()
    try:
        engine.hybrid_search("q")
        pytest.fail("should have raised")
    except Exception:
        pass


def test_keyword_search_with_scores():
    engine = _engine()
    engine.bm25_initialized = True
    engine.bm25 = MagicMock()
    engine.bm25.get_scores.return_value = [0.0, 2.0]
    engine.documents = [
        {"id": 1, "title": "a", "content": "x", "correspondent": "c", "created": "2024"},
        {"id": 2, "title": "b", "content": "y", "correspondent": "d", "created": "2024"},
    ]
    results = engine.keyword_search("b", top_k=5)
    assert len(results) == 1
    assert results[0]["id"] == 2


def test_semantic_search_maps_metadata():
    engine = _engine()
    engine.vector_db = MagicMock()
    engine.vector_db.ask.return_value = [
        MagicMock(id="3", title="t3", content="c3", score=0.8,
                  metadata={"correspondent": "ACME", "created": "2024-03-01"}),
    ]
    results = engine.semantic_search("q")
    assert results[0]["correspondent"] == "ACME"
    assert results[0]["date"] == "2024-03-01"


def test_create_snippet_exception_returns_truncated():
    engine = _engine()
    with patch("src.search_engine.word_tokenize", side_effect=Exception("boom")):
        snippet = engine.create_snippet("q", "long content here")
        assert snippet == "long content here..."


@patch("src.search_engine.RerankerFactory.create")
def test_search_full_flow_with_filters(mock_reranker):
    mock_reranker.return_value = MagicMock()
    engine = _engine()
    engine.initialize()
    engine.vector_db = MagicMock()
    engine.vector_db.ask.return_value = [
        MagicMock(id="1", title="Rechnung", content="Hallo Welt", score=0.9,
                  metadata={"correspondent": "ACME", "created": "2024-01-15"}),
        MagicMock(id="2", title="Vertrag", content="Test", score=0.5,
                  metadata={"correspondent": "Firma", "created": "2023-05-01"}),
    ]
    engine.bm25_initialized = True
    engine.bm25 = MagicMock()
    engine.bm25.get_scores.return_value = [0.0, 0.0]
    engine.documents = []
    engine.reranker = MagicMock()
    engine.reranker.rerank.side_effect = lambda q, results, k: results[:k]

    req = SearchRequest(
        query="Rechnung",
        from_date="2024-01-01",
        to_date="2024-12-31",
        correspondent="acme",
    )
    results = engine.search(req)
    assert len(results) == 1
    assert results[0].title == "Rechnung"
    assert results[0].correspondent == "ACME"
    assert results[0].snippet


def test_search_no_filters_all_results():
    engine = _engine()
    engine.initialize()
    engine.vector_db = MagicMock()
    engine.vector_db.ask.return_value = [
        MagicMock(id="1", title="R", content="c", score=0.7, metadata={}),
    ]
    engine.bm25_initialized = True
    engine.bm25 = MagicMock()
    engine.bm25.get_scores.return_value = [0.0]
    engine.documents = [
        {"id": 1, "title": "R", "content": "c", "correspondent": "", "created": ""}
    ]
    engine.reranker = MagicMock()
    engine.reranker.rerank.side_effect = lambda q, results, k: results[:k]

    results = engine.search(SearchRequest(query="q"))
    assert len(results) == 1
    assert results[0].doc_id == 1


def test_get_status_initialized():
    engine = _engine()
    engine.is_initialized = True
    engine.status.chroma_ready = True
    engine.bm25_initialized = True
    engine.documents = [{"id": 1}]
    engine.tokenized_corpus = [[1]]
    status = engine.get_status()
    assert status["initialized"] is True
    assert status["bm25_ready"] is True
    assert status["documents_count"] == 1
