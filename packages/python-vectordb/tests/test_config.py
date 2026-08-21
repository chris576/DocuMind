"""Unit tests for python-vectordb config."""

from python_vectordb.config import VectorDBConfig, load_vector_db_config


def test_vector_db_config_chroma():
    cfg = VectorDBConfig(
        vector_db_type="chroma",
        embedding_provider="sentence_transformer",
        reranker_provider="cross_encoder",
        collection_name="docs",
        embedding_model="m1",
        cross_encoder_model="m2",
    )
    assert cfg.to_vector_db_config() == {
        "type": "chroma",
        "collection": "docs",
        "embedding_model": "m1",
        "embedding_provider": "sentence_transformer",
        "url": "http://localhost:8000",
    }
    assert cfg.to_embedding_config() == {
        "embedding_provider": "sentence_transformer",
        "embedding_model": "m1",
    }
    assert cfg.to_reranker_config() == {
        "reranker_provider": "cross_encoder",
        "cross_encoder_model": "m2",
    }


def test_vector_db_config_qdrant():
    cfg = VectorDBConfig(
        vector_db_type="QDRANT",
        embedding_provider="st",
        reranker_provider="ce",
        collection_name="docs",
        embedding_model="m1",
        cross_encoder_model="m2",
        qdrant_url="http://qdrant:6333",
        qdrant_api_key="key",
    )
    conf = cfg.to_vector_db_config()
    assert conf["type"] == "qdrant"
    assert conf["url"] == "http://qdrant:6333"
    assert conf["api_key"] == "key"


def test_vector_db_config_pgvector():
    cfg = VectorDBConfig(
        vector_db_type="pgvector",
        embedding_provider="st",
        reranker_provider="ce",
        collection_name="docs",
        embedding_model="m1",
        cross_encoder_model="m2",
        pgvector_url="postgresql://user:pass@localhost/db",
    )
    conf = cfg.to_vector_db_config()
    assert conf["type"] == "pgvector"
    assert conf["url"] == "postgresql://user:pass@localhost/db"


def test_load_vector_db_config_defaults(monkeypatch):
    for var in (
        "VECTOR_DB_TYPE",
        "EMBEDDING_PROVIDER",
        "RERANKER_PROVIDER",
        "COLLECTION_NAME",
        "EMBEDDING_MODEL",
        "CROSS_ENCODER_MODEL",
        "CHROMA_URL",
        "QDRANT_URL",
        "QDRANT_API_KEY",
        "PGVECTOR_URL",
    ):
        monkeypatch.delenv(var, raising=False)

    cfg = load_vector_db_config()
    assert cfg.vector_db_type == "chroma"
    assert cfg.collection_name == "documents"
    assert cfg.chroma_url == "http://localhost:8000"
    assert cfg.qdrant_url == "http://localhost:6333"
    assert cfg.qdrant_api_key is None
    assert cfg.pgvector_url is None


def test_load_vector_db_config_from_env(monkeypatch):
    monkeypatch.setenv("VECTOR_DB_TYPE", "qdrant")
    monkeypatch.setenv("QDRANT_URL", "http://custom:6333")
    monkeypatch.setenv("QDRANT_API_KEY", "abc")

    cfg = load_vector_db_config()
    assert cfg.vector_db_type == "qdrant"
    assert cfg.qdrant_url == "http://custom:6333"
    assert cfg.qdrant_api_key == "abc"
