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
        "similarity_metric": "cosine",
        "keyword_method": "auto",
        "keyword_weight": 0.3,
        "semantic_weight": 0.7,
        "fts_language": "german",
        "keyword_index_file": "./data/bm25_index.pkl",
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


def test_vector_db_config_keyword_overrides():
    cfg = VectorDBConfig(
        vector_db_type="chroma",
        embedding_provider="st",
        reranker_provider="ce",
        collection_name="docs",
        embedding_model="m1",
        cross_encoder_model="m2",
        keyword_method="local",
        keyword_weight=0.4,
        semantic_weight=0.6,
        fts_language="english",
        keyword_index_file="/tmp/kw.pkl",
    )
    conf = cfg.to_vector_db_config()
    assert conf["keyword_method"] == "local"
    assert conf["keyword_weight"] == 0.4
    assert conf["semantic_weight"] == 0.6
    assert conf["fts_language"] == "english"
    assert conf["keyword_index_file"] == "/tmp/kw.pkl"


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
    assert conf["similarity_metric"] == "cosine"


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
        "SIMILARITY_METRIC",
        "CHROMA_URL",
        "QDRANT_URL",
        "QDRANT_API_KEY",
        "PGVECTOR_URL",
    ):
        monkeypatch.delenv(var, raising=False)

    cfg = load_vector_db_config()
    assert cfg.vector_db_type == "chroma"
    assert cfg.collection_name == "documents"
    assert cfg.similarity_metric == "cosine"
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


def test_load_vector_db_config_similarity_metric_env(monkeypatch):
    monkeypatch.setenv("SIMILARITY_METRIC", "euclidean")
    cfg = load_vector_db_config()
    assert cfg.similarity_metric == "euclidean"
    assert cfg.to_vector_db_config()["similarity_metric"] == "euclidean"


def test_load_vector_db_config_keyword_and_provider_env(monkeypatch):
    monkeypatch.setenv("KEYWORD_METHOD", "local")
    monkeypatch.setenv("KEYWORD_WEIGHT", "0.5")
    monkeypatch.setenv("SEMANTIC_WEIGHT", "0.4")
    monkeypatch.setenv("FTS_LANGUAGE", "english")
    monkeypatch.setenv("KEYWORD_INDEX_FILE", "/tmp/kw.pkl")
    monkeypatch.setenv("EMBEDDING_PROVIDER", "custom_emb")
    monkeypatch.setenv("RERANKER_PROVIDER", "custom_reranker")

    cfg = load_vector_db_config()
    assert cfg.keyword_method == "local"
    assert cfg.keyword_weight == 0.5
    assert cfg.semantic_weight == 0.4
    assert cfg.fts_language == "english"
    assert cfg.keyword_index_file == "/tmp/kw.pkl"
    assert cfg.embedding_provider == "custom_emb"
    assert cfg.reranker_provider == "custom_reranker"
