"""Unit tests for the QdrantVectorDB adapter (mocked client)."""
from unittest.mock import MagicMock, patch

import pytest
from qdrant_client.http import models

from python_vectordb.vector_db.base import VectorDBDocument
from python_vectordb.vector_db.qdrant import QdrantVectorDB, _to_point_id


def _provider():
    provider = MagicMock()
    provider.encode_texts.return_value = [[0.1, 0.2, 0.3], [0.1, 0.2, 0.3]]
    provider.encode_query.return_value = [0.1, 0.2, 0.3]
    return provider


def _adapter(**kwargs):
    conf = {"url": "http://localhost:6333", "collection": "docs", "embedding_dimension": 3}
    conf.update(kwargs)
    return QdrantVectorDB(conf, _provider())


@patch("python_vectordb.vector_db.qdrant.QdrantClient")
def test_initialize_creates_collection(mock_client_cls):
    client = MagicMock()
    client.get_collections.return_value = MagicMock(collections=[])
    mock_client_cls.return_value = client

    adapter = _adapter()
    assert adapter.initialize() is True
    client.create_collection.assert_called_once()
    client.get_collection.assert_not_called()


@patch("python_vectordb.vector_db.qdrant.QdrantClient")
def test_initialize_reuses_collection(mock_client_cls):
    client = MagicMock()
    existing = MagicMock()
    existing.name = "docs"
    client.get_collections.return_value = MagicMock(collections=[existing])
    mock_client_cls.return_value = client

    adapter = _adapter()
    assert adapter.initialize() is True
    client.create_collection.assert_not_called()


@patch("python_vectordb.vector_db.qdrant.QdrantClient")
def test_initialize_failure(mock_client_cls):
    mock_client_cls.side_effect = Exception("boom")
    adapter = _adapter()
    assert adapter.initialize() is False


def test_add_documents_requires_ready():
    adapter = _adapter()
    with pytest.raises(Exception, match="not initialized"):
        adapter.add_documents([VectorDBDocument(id="1", title="t", content="c")])


def test_add_documents_upserts_points():
    adapter = _adapter()
    adapter.ready = True
    adapter.client = MagicMock()

    docs = [
        VectorDBDocument(id="1", title="t1", content="c1", metadata={"k": "v"}),
        VectorDBDocument(id="abc", title="t2", content="c2"),
    ]
    adapter.add_documents(docs)

    adapter.client.upsert.assert_called_once()
    args = adapter.client.upsert.call_args.kwargs
    assert args["collection_name"] == "docs"
    assert len(args["points"]) == 2


def test_search_returns_empty_on_no_points():
    adapter = _adapter()
    adapter.ready = True
    adapter.client = MagicMock()
    adapter.client.query_points.return_value = MagicMock(points=[])

    assert adapter.search("q") == []


def test_search_maps_points():
    adapter = _adapter()
    adapter.ready = True
    adapter.client = MagicMock()

    point = MagicMock()
    point.id = 1
    point.score = 0.7
    point.payload = {"title": "t1", "content": "c1"}
    adapter.client.query_points.return_value = MagicMock(points=[point])

    results = adapter.search("q")
    assert len(results) == 1
    assert results[0].id == "1"
    assert results[0].title == "t1"
    assert results[0].score == 0.7


def test_delete_collection_requires_client():
    adapter = _adapter()
    with pytest.raises(Exception, match="not initialized"):
        adapter.delete_collection()


def test_delete_collection_calls_client():
    adapter = _adapter()
    adapter.client = MagicMock()
    adapter.delete_collection()
    adapter.client.delete_collection.assert_called_once_with("docs")


def test_delete_documents_requires_ready():
    adapter = _adapter()
    with pytest.raises(Exception, match="not initialized"):
        adapter.delete_documents(["1"])


def test_delete_documents_empty_noop():
    adapter = _adapter()
    adapter.ready = True
    adapter.client = MagicMock()
    adapter.delete_documents([])
    adapter.client.delete.assert_not_called()


def test_delete_documents_calls_client():
    adapter = _adapter()
    adapter.ready = True
    adapter.client = MagicMock()
    adapter.delete_documents(["1", "2"])
    adapter.client.delete.assert_called_once()
    assert adapter.client.delete.call_args.kwargs["collection_name"] == "docs"


def test_get_status_not_ready():
    adapter = _adapter()
    assert adapter.get_status() == {"ready": False, "document_count": 0}


def test_get_status_ready():
    adapter = _adapter()
    adapter.ready = True
    adapter.client = MagicMock()
    info = MagicMock()
    info.points_count = 4
    adapter.client.get_collection.return_value = info
    assert adapter.get_status() == {"ready": True, "document_count": 4}


def test_get_status_exception():
    adapter = _adapter()
    adapter.ready = True
    adapter.client = MagicMock()
    adapter.client.get_collection.side_effect = Exception("boom")
    assert adapter.get_status() == {"ready": False, "document_count": 0}


def test_to_point_id():
    # Numeric ids pass through as int.
    assert _to_point_id("42") == 42
    # Valid UUID strings pass through as UUID.
    u = "12345678-1234-5678-1234-567812345678"
    assert str(_to_point_id(u)) == u
    # Arbitrary strings are deterministically mapped to a UUID (not empty).
    mapped = _to_point_id("abc-123")
    assert isinstance(mapped, str) or hasattr(mapped, "hex")
    assert str(mapped) != ""


def test_default_metric_is_cosine():
    adapter = _adapter()
    assert adapter.similarity_metric == "cosine"
    assert adapter.distance == models.Distance.COSINE


@pytest.mark.parametrize(
    "metric,distance",
    [
        ("cosine", models.Distance.COSINE),
        ("euclidean", models.Distance.EUCLID),
        ("dot", models.Distance.DOT),
        ("manhattan", models.Distance.MANHATTAN),
    ],
)
def test_metric_selects_distance(metric, distance):
    adapter = _adapter(similarity_metric=metric)
    assert adapter.distance == distance


@patch("python_vectordb.vector_db.qdrant.QdrantClient")
def test_initialize_uses_configured_distance(mock_client_cls):
    client = MagicMock()
    client.get_collections.return_value = MagicMock(collections=[])
    mock_client_cls.return_value = client

    adapter = _adapter(similarity_metric="euclidean")
    assert adapter.initialize() is True
    created = client.create_collection.call_args.kwargs["vectors_config"]
    assert created.distance == models.Distance.EUCLID
