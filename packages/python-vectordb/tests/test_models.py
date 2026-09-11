"""Unit tests for model alias resolution (embeddings + reranking)."""
from python_vectordb.embeddings.models import MODEL_SPECS, resolve_model_spec
from python_vectordb.reranking.models import RERANKER_MODEL_SPECS, resolve_reranker_model


def test_resolve_model_spec_e5_alias_applies_prefixes():
    spec = resolve_model_spec("e5-small-multilingual")
    assert spec.model_id == "intfloat/multilingual-e5-small"
    assert spec.query_prefix == "query: "
    assert spec.passage_prefix == "passage: "


def test_resolve_model_spec_e5_full_id():
    spec = resolve_model_spec("intfloat/multilingual-e5-base")
    assert spec.model_id == "intfloat/multilingual-e5-base"
    assert spec.query_prefix == "query: "
    assert spec.passage_prefix == "passage: "


def test_resolve_model_spec_bge_m3_query_prefix_only():
    spec = resolve_model_spec("bge-m3")
    assert spec.model_id == "BAAI/bge-m3"
    assert spec.query_prefix == "Represent this sentence for searching relevant passages: "
    assert spec.passage_prefix == ""


def test_resolve_model_spec_minilm_no_prefixes():
    spec = resolve_model_spec("minilm-multilingual")
    assert spec.model_id == "paraphrase-multilingual-MiniLM-L12-v2"
    assert spec.query_prefix == ""
    assert spec.passage_prefix == ""


def test_resolve_model_spec_unknown_passthrough():
    spec = resolve_model_spec("my-custom-model")
    assert spec.model_id == "my-custom-model"
    assert spec.query_prefix == ""
    assert spec.passage_prefix == ""


def test_model_specs_alias_points_to_same_model_id():
    assert (
        MODEL_SPECS["e5-small-multilingual"].model_id
        == MODEL_SPECS["intfloat/multilingual-e5-small"].model_id
    )


def test_resolve_reranker_model_known_alias():
    assert (
        resolve_reranker_model("msmarco-minilm")
        == "cross-encoder/ms-marco-MiniLM-L-6-v2"
    )
    assert resolve_reranker_model("bge-reranker-m3") == "BAAI/bge-reranker-v2-m3"


def test_resolve_reranker_model_known_full_id():
    assert (
        resolve_reranker_model("cross-encoder/ms-marco-MiniLM-L-6-v2")
        == "cross-encoder/ms-marco-MiniLM-L-6-v2"
    )


def test_resolve_reranker_model_unknown_passthrough():
    assert resolve_reranker_model("custom-ce") == "custom-ce"


def test_reranker_specs_alias_points_to_same_model_id():
    assert (
        RERANKER_MODEL_SPECS["msmarco-minilm"]
        == RERANKER_MODEL_SPECS["cross-encoder/ms-marco-MiniLM-L-6-v2"]
    )
