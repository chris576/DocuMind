"""Unit tests for the ChromaVectorDB adapter (mocked client)."""
from unittest.mock import MagicMock, patch

import pytest

from python_vectordb.vector_db.base import VectorDBDocument
from python_vectordb.vector_db.chroma import ChromaVectorDB


def _provider():
    provider = MagicMock()
    provider.encode_texts.return_value = [[0.1, 0.2, 0.3]]
    provider.encode_query.return_value = [0.1, 0.2, 0.3]
    return provider


def _adapter(**kwargs):
    conf = {"url": "http://localhost:8000", "collection": "docs"}
    conf.update(kwargs)
    return ChromaVectorDB(conf, _provider())


@patch("python_vectordb.vector_db.chroma.chromadb.HttpClient")
def test_initialize_creates_collection(mock_client_cls):
    client = MagicMock()
    client.list_collections.return_value = []
    mock_client_cls.return_value = client

    adapter = _adapter()
    assert adapter.initialize() is True
    assert adapter.ready is True
    client.create_collection.assert_called_once()
    client.get_collection.assert_not_called()


@patch("python_vectordb.vector_db.chroma.chromadb.HttpClient")
def test_initialize_reuses_existing_collection(mock_client_cls):
    client = MagicMock()
    existing = MagicMock()
    existing.name = "docs"
    client.list_collections.return_value = [existing]
    mock_client_cls.return_value = client

    adapter = _adapter()
    assert adapter.initialize() is True
    client.get_collection.assert_called_once_with(name="docs")
    client.create_collection.assert_not_called()


@patch("python_vectordb.vector_db.chroma.chromadb.HttpClient")
def test_initialize_failure_returns_false(mock_client_cls):
    mock_client_cls.side_effect = Exception("conn refused")
    adapter = _adapter()
    assert adapter.initialize() is False
    assert adapter.ready is False


def test_default_metric_is_cosine():
    adapter = _adapter()
    assert adapter.similarity_metric == "cosine"
    assert adapter.space == "cosine"


@pytest.mark.parametrize(
    "metric,space",
    [
        ("cosine", "cosine"),
        ("euclidean", "l2"),
        ("dot", "ip"),
    ],
)
def test_metric_selects_space(metric, space):
    adapter = _adapter(similarity_metric=metric)
    assert adapter.space == space


@patch("python_vectordb.vector_db.chroma.chromadb.HttpClient")
def test_initialize_uses_configured_space(mock_client_cls):
    client = MagicMock()
    client.list_collections.return_value = []
    mock_client_cls.return_value = client

    adapter = _adapter(similarity_metric="euclidean")
    assert adapter.initialize() is True
    client.create_collection.assert_called_once_with(
        name="docs", metadata={"hnsw:space": "l2"}
    )


def test_add_documents_requires_ready():
    adapter = _adapter()
    with pytest.raises(Exception, match="not initialized"):
        adapter.add_documents([VectorDBDocument(id="1", title="t", content="c")])


def test_add_documents_upserts_batch():
    adapter = _adapter()
    adapter.ready = True
    adapter.collection = MagicMock()

    docs = [
        VectorDBDocument(
            id="1", title="t1", content="c1", metadata={"nested": [1, 2]}
        ),
        VectorDBDocument(id="2", title="t2", content="c2", metadata={"n": 1}),
    ]
    adapter.add_documents(docs)

    adapter.collection.upsert.assert_called_once()
    kwargs = adapter.collection.upsert.call_args.kwargs
    assert kwargs["ids"] == ["1", "2"]
    # Nested list serialized to JSON.
    assert kwargs["metadatas"][0] == {"title": "t1", "nested": "[1, 2]"}
    assert kwargs["metadatas"][1] == {"title": "t2", "n": 1}


def test_search_returns_empty_when_no_ids():
    adapter = _adapter()
    adapter.ready = True
    adapter.collection = MagicMock()
    adapter.collection.query.return_value = {"ids": []}

    assert adapter.search("q") == []


def test_search_maps_results():
    adapter = _adapter()
    adapter.ready = True
    adapter.collection = MagicMock()
    adapter.collection.query.return_value = {
        "ids": [[1]],
        "distances": [[0.2]],
        "metadatas": [[{"title": "t1"}]],
        "documents": [["content1"]],
    }

    results = adapter.search("q", top_k=1)
    assert len(results) == 1
    assert results[0].id == "1"
    assert results[0].title == "t1"
    assert results[0].content == "content1"
    assert abs(results[0].score - 0.8) < 1e-9


def test_delete_collection_requires_client():
    adapter = _adapter()
    with pytest.raises(Exception, match="not initialized"):
        adapter.delete_collection()


def test_delete_collection_calls_client():
    adapter = _adapter()
    adapter.client = MagicMock()
    adapter.delete_collection()
    adapter.client.delete_collection.assert_called_once_with("docs")
    assert adapter.ready is False


def test_delete_documents_requires_ready():
    adapter = _adapter()
    with pytest.raises(Exception, match="not initialized"):
        adapter.delete_documents(["1"])


def test_delete_documents_empty_is_noop():
    adapter = _adapter()
    adapter.ready = True
    adapter.collection = MagicMock()
    adapter.delete_documents([])
    adapter.collection.delete.assert_not_called()


def test_delete_documents_calls_collection():
    adapter = _adapter()
    adapter.ready = True
    adapter.collection = MagicMock()
    adapter.delete_documents(["1", "2"])
    adapter.collection.delete.assert_called_once_with(ids=["1", "2"])


def test_get_status_not_ready():
    adapter = _adapter()
    assert adapter.get_status() == {"ready": False, "document_count": 0}


def test_get_status_ready():
    adapter = _adapter()
    adapter.ready = True
    adapter.collection = MagicMock()
    adapter.collection.count.return_value = 5
    assert adapter.get_status() == {"ready": True, "document_count": 5, "keyword_documents_count": 0}


def test_get_status_ready_exception():
    adapter = _adapter()
    adapter.ready = True
    adapter.collection = MagicMock()
    adapter.collection.count.side_effect = Exception("boom")
    assert adapter.get_status() == {"ready": False, "document_count": 0}


def test_flatten_metadata():
    flat = ChromaVectorDB._flatten_metadata(
        {"a": 1, "b": [1, 2], "c": {"x": 1}, "d": "s"}
    )
    assert flat == {"a": 1, "b": "[1, 2]", "c": '{"x": 1}', "d": "s"}


def test_hybrid_search_requires_ready():
    adapter = _adapter()
    with pytest.raises(Exception, match="not initialized"):
        adapter.hybrid_search("q")


def test_hybrid_search_empty_returns_empty():
    adapter = _adapter()
    adapter.ready = True
    adapter.collection = MagicMock()
    adapter.collection.query.return_value = {"ids": []}
    adapter._bm25 = None
    assert adapter.hybrid_search("q") == []


def test_hybrid_search_fuses_semantic_and_keyword():
    adapter = _adapter(keyword_weight=0.5, semantic_weight=0.5)
    adapter.ready = True
    adapter.collection = MagicMock()
    adapter.collection.query.return_value = {
        "ids": [["1", "2"]],
        "distances": [[0.2, 0.5]],
        "metadatas": [[{"title": "t1"}, {"title": "t2"}]],
        "documents": [["content1", "content2"]],
    }
    # Local BM25 corpus with one matching doc.
    adapter._keyword_documents = [
        {"id": "1", "title": "Rechnung", "content": "Zahlung frist", "correspondent": "", "created": ""},
        {"id": "2", "title": "Vertrag", "content": "Laufzeit", "correspondent": "", "created": ""},
    ]
    adapter._ensure_nltk()
    adapter._rebuild_local_index_from_state()

    results = adapter.hybrid_search("Rechnung", top_k=5)
    assert len(results) >= 1
    # doc "1" matches both channels, so it is present and has a fused score.
    by_id = {r.id: r for r in results}
    assert "1" in by_id
    assert by_id["1"].score > 0


def test_hybrid_search_keyword_disabled_returns_semantic_only():
    adapter = _adapter(keyword_method="disabled")
    adapter.ready = True
    adapter.collection = MagicMock()
    adapter.collection.query.return_value = {
        "ids": [["1"]],
        "distances": [[0.1]],
        "metadatas": [[{"title": "t1"}]],
        "documents": [["content"]],
    }
    adapter._keyword_documents = []
    adapter._bm25 = None
    results = adapter.hybrid_search("q")
    assert len(results) == 1


def test_keyword_search_returns_scored_docs():
    adapter = _adapter()
    adapter._keyword_documents = [
        {"id": "1", "title": "Invoice", "content": "payment due", "correspondent": "", "created": ""},
        {"id": "2", "title": "Contract", "content": "term", "correspondent": "", "created": ""},
        {"id": "3", "title": "Report", "content": "summary", "correspondent": "", "created": ""},
    ]
    adapter._ensure_nltk()
    adapter._rebuild_local_index_from_state()
    results = adapter._keyword_search("invoice payment", top_k=5)
    assert any(r["id"] == "1" for r in results)


def test_keyword_search_uninitialized_returns_empty():
    adapter = _adapter()
    adapter._bm25 = None
    adapter._tokenized_corpus = None
    assert adapter._keyword_search("q") == []


@patch("python_vectordb.vector_db.chroma.chromadb.HttpClient")
def test_local_index_persist_and_load(mock_client_cls, tmp_path):
    client = MagicMock()
    client.list_collections.return_value = []
    mock_client_cls.return_value = client

    index_file = str(tmp_path / "bm25.pkl")
    adapter = _adapter(keyword_index_file=index_file)
    assert adapter.initialize() is True

    docs = [
        VectorDBDocument(id="1", title="Alpha report", content="quarterly summary", metadata={}),
        VectorDBDocument(id="2", title="Beta invoice", content="payment due", metadata={}),
        VectorDBDocument(id="3", title="Gamma contract", content="term duration", metadata={}),
    ]
    adapter.add_documents(docs)
    assert adapter._bm25 is not None
    assert len(adapter._keyword_documents) == 3
    assert isinstance(adapter._keyword_search("alpha report", 5)[0]["id"], str)


@patch("python_vectordb.vector_db.chroma.chromadb.HttpClient")
def test_delete_documents_updates_local_index(mock_client_cls):
    client = MagicMock()
    client.list_collections.return_value = []
    mock_client_cls.return_value = client

    adapter = _adapter()
    assert adapter.initialize() is True
    adapter._keyword_documents = [
        {"id": "1", "title": "a", "content": "c", "correspondent": "", "created": ""},
        {"id": "2", "title": "b", "content": "c", "correspondent": "", "created": ""},
    ]
    adapter._rebuild_local_index_from_state()

    adapter.delete_documents(["2"])
    assert [d["id"] for d in adapter._keyword_documents] == ["1"]


@patch("python_vectordb.vector_db.chroma.chromadb.HttpClient")
def test_delete_collection_removes_local_index(mock_client_cls, tmp_path):
    client = MagicMock()
    client.list_collections.return_value = []
    mock_client_cls.return_value = client

    index_file = str(tmp_path / "bm25.pkl")
    adapter = _adapter(keyword_index_file=index_file)
    assert adapter.initialize() is True
    adapter.add_documents([VectorDBDocument(id="1", title="t", content="c", metadata={})])
    assert adapter._bm25 is not None

    adapter.delete_collection()
    assert adapter._bm25 is None
    assert adapter._keyword_documents == []
