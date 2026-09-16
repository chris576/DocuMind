"""Unit tests for python-vectordb config."""

from python_vectordb.config import VectorDBConfig, load_vector_db_config


def test_vector_db_config_pgvector():
    cfg = VectorDBConfig(
        vector_db_type="pgvector",
        embedding_provider="sentence_transformer",
        reranker_provider="cross_encoder",
        collection_name="docs",
        embedding_model="m1",
        cross_encoder_model="m2",
        pgvector_url="postgresql://user:pass@localhost/db",
    )
    assert cfg.to_vector_db_config() == {
        "type": "pgvector",
        "collection": "docs",
        "table_name": "document_facts",
        "embedding_model": "m1",
        "embedding_provider": "sentence_transformer",
        "similarity_metric": "cosine",
        "keyword_method": "auto",
        "keyword_weight": 0.3,
        "semantic_weight": 0.7,
        "fts_language": "german",
        "url": "postgresql://user:pass@localhost/db",
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
        vector_db_type="pgvector",
        embedding_provider="st",
        reranker_provider="ce",
        collection_name="docs",
        embedding_model="m1",
        cross_encoder_model="m2",
        keyword_method="local",
        keyword_weight=0.4,
        semantic_weight=0.6,
        fts_language="english",
        fact_table="facts_custom",
    )
    conf = cfg.to_vector_db_config()
    assert conf["keyword_method"] == "local"
    assert conf["keyword_weight"] == 0.4
    assert conf["semantic_weight"] == 0.6
    assert conf["fts_language"] == "english"
    assert conf["table_name"] == "facts_custom"


def test_load_vector_db_config_defaults(monkeypatch):
    for var in (
        "VECTOR_DB_TYPE",
        "EMBEDDING_PROVIDER",
        "RERANKER_PROVIDER",
        "COLLECTION_NAME",
        "EMBEDDING_MODEL",
        "CROSS_ENCODER_MODEL",
        "SIMILARITY_METRIC",
        "PGVECTOR_URL",
        "FACT_TABLE",
    ):
        monkeypatch.delenv(var, raising=False)

    cfg = load_vector_db_config()
    assert cfg.vector_db_type == "pgvector"
    assert cfg.collection_name == "documents"
    assert cfg.similarity_metric == "cosine"
    assert cfg.pgvector_url is None
    assert cfg.fact_table == "document_facts"


def test_load_vector_db_config_from_env(monkeypatch):
    monkeypatch.setenv("VECTOR_DB_TYPE", "pgvector")
    monkeypatch.setenv("PGVECTOR_URL", "postgresql://u:p@localhost/db")
    monkeypatch.setenv("FACT_TABLE", "my_facts")

    cfg = load_vector_db_config()
    assert cfg.vector_db_type == "pgvector"
    assert cfg.pgvector_url == "postgresql://u:p@localhost/db"
    assert cfg.fact_table == "my_facts"


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
    monkeypatch.setenv("EMBEDDING_PROVIDER", "custom_emb")
    monkeypatch.setenv("RERANKER_PROVIDER", "custom_reranker")

    cfg = load_vector_db_config()
    assert cfg.keyword_method == "local"
    assert cfg.keyword_weight == 0.5
    assert cfg.semantic_weight == 0.4
    assert cfg.fts_language == "english"
    assert cfg.embedding_provider == "custom_emb"
    assert cfg.reranker_provider == "custom_reranker"
