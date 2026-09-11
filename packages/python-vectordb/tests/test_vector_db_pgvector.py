"""Unit tests for the PgVectorVectorDB adapter (mocked connection)."""
from unittest.mock import MagicMock, patch

import pytest

from python_vectordb.vector_db.base import VectorDBDocument
from python_vectordb.vector_db.pgvector import PgVectorVectorDB


def _provider():
    provider = MagicMock()
    provider.encode_texts.return_value = [MagicMock(tolist=lambda: [0.1, 0.2, 0.3])]
    provider.encode_query.return_value = [0.1, 0.2, 0.3]
    return provider


def _adapter(**kwargs):
    conf = {
        "url": "postgresql://u:p@localhost/db",
        "collection": "documents",
        "embedding_dimension": 3,
    }
    conf.update(kwargs)
    return PgVectorVectorDB(conf, _provider())


@patch("python_vectordb.vector_db.pgvector.psycopg2.connect")
def test_initialize_creates_table(mock_connect):
    conn = MagicMock()
    cursor = MagicMock()
    conn.cursor.return_value.__enter__.return_value = cursor
    mock_connect.return_value = conn

    adapter = _adapter()
    assert adapter.initialize() is True
    assert adapter.ready is True
    conn.commit.assert_called()
    assert cursor.execute.call_count >= 2
    sqls = [str(c.args[0]) for c in cursor.execute.call_args_list]
    assert any("CREATE TABLE IF NOT EXISTS documents" in s for s in sqls)
    # FTS generated column present in DDL.
    ddl = next(s for s in sqls if "CREATE TABLE IF NOT EXISTS documents" in s)
    assert "tsvector GENERATED ALWAYS AS" in ddl
    assert "to_tsvector('german'" in ddl
    # GIN index created for full text search.
    assert any("USING GIN (fts)" in s for s in sqls)


@patch("python_vectordb.vector_db.pgvector.psycopg2.connect")
def test_initialize_missing_url(mock_connect):
    adapter = _adapter(url=None)
    assert adapter.initialize() is False
    mock_connect.assert_not_called()


@patch("python_vectordb.vector_db.pgvector.psycopg2.connect")
def test_initialize_failure(mock_connect):
    mock_connect.side_effect = Exception("no conn")
    adapter = _adapter()
    assert adapter.initialize() is False


def test_add_documents_requires_ready():
    adapter = _adapter()
    with pytest.raises(Exception, match="not initialized"):
        adapter.add_documents([VectorDBDocument(id="1", title="t", content="c")])


@patch("python_vectordb.vector_db.pgvector.psycopg2.connect")
def test_add_documents_inserts(mock_connect):
    conn = MagicMock()
    cursor = MagicMock()
    conn.cursor.return_value.__enter__.return_value = cursor
    mock_connect.return_value = conn

    adapter = _adapter()
    adapter.ready = True
    adapter.connection = conn

    docs = [VectorDBDocument(id="1", title="t1", content="c1", metadata={"k": "v"})]
    adapter.add_documents(docs)

    conn.commit.assert_called()
    cursor.execute.assert_called()
    sql = cursor.execute.call_args.args[0]
    assert "INSERT INTO documents" in sql
    assert "ON CONFLICT (id) DO UPDATE" in sql


def test_search_requires_ready():
    adapter = _adapter()
    with pytest.raises(Exception, match="not initialized"):
        adapter.search("q")


@patch("python_vectordb.vector_db.pgvector.psycopg2.connect")
def test_search_maps_rows(mock_connect):
    conn = MagicMock()
    cursor = MagicMock()
    conn.cursor.return_value.__enter__.return_value = cursor
    cursor.fetchall.return_value = [
        ("1", "t1", "c1", {"k": "v"}, 0.9),
        ("2", "t2", "c2", {}, None),
    ]
    mock_connect.return_value = conn

    adapter = _adapter()
    adapter.ready = True
    adapter.connection = conn

    results = adapter.search("q")
    assert len(results) == 2
    assert results[0].id == "1"
    assert results[0].score == 0.9
    assert results[1].score == 0.0
    assert results[1].metadata == {}


def test_delete_collection_requires_conn():
    adapter = _adapter()
    with pytest.raises(Exception, match="not initialized"):
        adapter.delete_collection()


@patch("python_vectordb.vector_db.pgvector.psycopg2.connect")
def test_delete_collection_drops_table(mock_connect):
    conn = MagicMock()
    cursor = MagicMock()
    conn.cursor.return_value.__enter__.return_value = cursor
    mock_connect.return_value = conn

    adapter = _adapter()
    adapter.connection = conn
    adapter.delete_collection()
    conn.commit.assert_called()
    assert "DROP TABLE IF EXISTS documents" in cursor.execute.call_args.args[0]


def test_delete_documents_requires_ready():
    adapter = _adapter()
    with pytest.raises(Exception, match="not initialized"):
        adapter.delete_documents(["1"])


@patch("python_vectordb.vector_db.pgvector.psycopg2.connect")
def test_delete_documents_calls_delete(mock_connect):
    conn = MagicMock()
    cursor = MagicMock()
    conn.cursor.return_value.__enter__.return_value = cursor
    mock_connect.return_value = conn

    adapter = _adapter()
    adapter.ready = True
    adapter.connection = conn
    adapter.delete_documents(["1", "2"])
    conn.commit.assert_called()
    assert "DELETE FROM documents" in cursor.execute.call_args.args[0]


@patch("python_vectordb.vector_db.pgvector.psycopg2.connect")
def test_delete_documents_empty_is_noop(mock_connect):
    conn = MagicMock()
    cursor = MagicMock()
    conn.cursor.return_value.__enter__.return_value = cursor
    mock_connect.return_value = conn

    adapter = _adapter()
    adapter.ready = True
    adapter.connection = conn
    adapter.delete_documents([])
    cursor.execute.assert_not_called()
    conn.commit.assert_not_called()


@patch("python_vectordb.vector_db.pgvector.psycopg2.connect")
def test_add_documents_batches_over_100(mock_connect):
    conn = MagicMock()
    cursor = MagicMock()
    conn.cursor.return_value.__enter__.return_value = cursor
    mock_connect.return_value = conn

    provider = MagicMock()

    def encode_texts(texts):
        return [MagicMock(tolist=lambda: [0.1]) for _ in texts]

    provider.encode_texts.side_effect = encode_texts

    adapter = PgVectorVectorDB(
        {
            "url": "postgresql://u:p@localhost/db",
            "collection": "documents",
            "embedding_dimension": 1,
        },
        provider,
    )
    adapter.ready = True
    adapter.connection = conn

    docs = [
        VectorDBDocument(id=str(i), title=f"t{i}", content=f"c{i}")
        for i in range(250)
    ]
    adapter.add_documents(docs)

    # 250 Dokumente -> 3 Batches -> 3 Commits, aber 250 Einzel-Inserts.
    assert conn.commit.call_count == 3
    assert cursor.execute.call_count == 250


def test_get_status_not_ready():
    adapter = _adapter()
    assert adapter.get_status() == {"ready": False, "document_count": 0}


@patch("python_vectordb.vector_db.pgvector.psycopg2.connect")
def test_get_status_ready(mock_connect):
    conn = MagicMock()
    cursor = MagicMock()
    conn.cursor.return_value.__enter__.return_value = cursor
    cursor.fetchone.return_value = (7,)
    mock_connect.return_value = conn

    adapter = _adapter()
    adapter.ready = True
    adapter.connection = conn
    assert adapter.get_status() == {"ready": True, "document_count": 7}


@patch("python_vectordb.vector_db.pgvector.psycopg2.connect")
def test_get_status_exception(mock_connect):
    conn = MagicMock()
    cursor = MagicMock()
    cursor.execute.side_effect = Exception("boom")
    conn.cursor.return_value.__enter__.return_value = cursor
    mock_connect.return_value = conn

    adapter = _adapter()
    adapter.ready = True
    adapter.connection = conn
    assert adapter.get_status() == {"ready": False, "document_count": 0}


def test_default_metric_is_cosine():
    assert _adapter().similarity_metric == "cosine"
    assert _adapter().operator == "<=>"


@pytest.mark.parametrize(
    "metric,operator",
    [
        ("cosine", "<=>"),
        ("euclidean", "<->"),
        ("dot", "<#>"),
    ],
)
def test_metric_selects_operator(metric, operator):
    adapter = _adapter(similarity_metric=metric)
    assert adapter.similarity_metric == metric
    assert adapter.operator == operator


@patch("python_vectordb.vector_db.pgvector.psycopg2.connect")
def test_search_uses_selected_operator(mock_connect):
    conn = MagicMock()
    cursor = MagicMock()
    conn.cursor.return_value.__enter__.return_value = cursor
    cursor.fetchall.return_value = []
    mock_connect.return_value = conn

    adapter = _adapter(similarity_metric="euclidean")
    adapter.ready = True
    adapter.connection = conn

    adapter.search("q")
    sql = cursor.execute.call_args.args[0]
    assert "<->" in sql


@patch("python_vectordb.vector_db.pgvector.psycopg2.connect")
def test_search_normalizes_euclidean_score(mock_connect):
    conn = MagicMock()
    cursor = MagicMock()
    conn.cursor.return_value.__enter__.return_value = cursor
    cursor.fetchall.return_value = [
        ("1", "t1", "c1", {"k": "v"}, 5.0),
    ]
    mock_connect.return_value = conn

    adapter = _adapter(similarity_metric="euclidean")
    adapter.ready = True
    adapter.connection = conn

    results = adapter.search("q")
    # Euclidean raw distance 5.0 -> 1/(1+5) = 1/6.
    assert abs(results[0].score - 1.0 / 6.0) < 1e-9


def test_hybrid_search_requires_ready():
    adapter = _adapter()
    with pytest.raises(Exception, match="not initialized"):
        adapter.hybrid_search("q")


@patch("python_vectordb.vector_db.pgvector.psycopg2.connect")
def test_hybrid_search_fuses_fts_and_vector(mock_connect):
    conn = MagicMock()
    cursor = MagicMock()
    conn.cursor.return_value.__enter__.return_value = cursor
    cursor.fetchall.return_value = [
        ("1", "t1", "c1", {"k": "v"}, 0.9, 0.5, 0.9),
    ]
    mock_connect.return_value = conn

    adapter = _adapter()
    adapter.ready = True
    adapter.connection = conn

    results = adapter.hybrid_search("invoice")
    assert len(results) == 1
    assert results[0].id == "1"
    assert results[0].score == 0.9

    sql = cursor.execute.call_args.args[0]
    assert "ts_rank" in sql
    assert "plainto_tsquery('german'" in sql
    assert "fts @@ plainto_tsquery('german'" in sql


@patch("python_vectordb.vector_db.pgvector.psycopg2.connect")
def test_hybrid_search_keyword_disabled_uses_semantic_rows(mock_connect):
    conn = MagicMock()
    cursor = MagicMock()
    conn.cursor.return_value.__enter__.return_value = cursor
    cursor.fetchall.return_value = [
        ("1", "t1", "c1", {}, 0.8, 0.0, 0.8),
    ]
    mock_connect.return_value = conn

    adapter = _adapter(keyword_method="disabled")
    adapter.ready = True
    adapter.connection = conn

    results = adapter.hybrid_search("q")
    assert len(results) == 1
    # Semantic-only path has no ts_rank in SQL.
    sql = cursor.execute.call_args.args[0]
    assert "ts_rank" not in sql


@patch("python_vectordb.vector_db.pgvector.psycopg2.connect")
def test_hybrid_search_uses_configured_fts_language(mock_connect):
    conn = MagicMock()
    cursor = MagicMock()
    conn.cursor.return_value.__enter__.return_value = cursor
    cursor.fetchall.return_value = [
        ("1", "t1", "c1", {}, 0.9, 0.5, 0.9),
    ]
    mock_connect.return_value = conn

    adapter = _adapter(fts_language="english")
    adapter.ready = True
    adapter.connection = conn

    adapter.hybrid_search("q")
    sql = cursor.execute.call_args.args[0]
    assert "plainto_tsquery('english'" in sql
