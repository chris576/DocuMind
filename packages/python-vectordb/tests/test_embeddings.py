"""Unit tests for python-vectordb embeddings."""
from unittest.mock import MagicMock, patch

import pytest

from python_vectordb.embeddings.base import EmbeddingProvider
from python_vectordb.embeddings.factory import EmbeddingProviderFactory
from python_vectordb.embeddings.sentence_transformer import (
    SentenceTransformerEmbeddingProvider,
)


@patch("python_vectordb.embeddings.sentence_transformer.SentenceTransformer")
def test_sentence_transformer_encode(mock_model_cls):
    model = MagicMock()
    model.get_sentence_embedding_dimension.return_value = 384

    def fake_encode(value):
        # encode_texts receives a list -> nested result; encode_query a str -> flat.
        if isinstance(value, list):
            return MagicMock(tolist=lambda: [[0.1] * 384])
        return MagicMock(tolist=lambda: [0.1] * 384)

    model.encode.side_effect = fake_encode
    mock_model_cls.return_value = model

    provider = SentenceTransformerEmbeddingProvider("some-model")
    assert provider.dimension == 384
    assert provider.encode_texts(["a", "b"]) == [[0.1] * 384]
    assert provider.encode_query("q") == [0.1] * 384
    mock_model_cls.assert_called_once_with("some-model")


@patch("python_vectordb.embeddings.sentence_transformer.SentenceTransformer")
def test_embedding_factory_default(mock_model_cls):
    model = MagicMock()
    model.get_sentence_embedding_dimension.return_value = 384
    model.encode.return_value = MagicMock(tolist=lambda: [[0.1] * 384])
    mock_model_cls.return_value = model

    provider = EmbeddingProviderFactory.create({})
    assert isinstance(provider, SentenceTransformerEmbeddingProvider)
    assert provider.dimension == 384
    mock_model_cls.assert_called_once_with("paraphrase-multilingual-MiniLM-L12-v2")


@patch("python_vectordb.embeddings.sentence_transformer.SentenceTransformer")
def test_embedding_factory_custom_model(mock_model_cls):
    model = MagicMock()
    model.get_sentence_embedding_dimension.return_value = 384
    mock_model_cls.return_value = model

    provider = EmbeddingProviderFactory.create(
        {"embedding_provider": "sentence_transformer", "embedding_model": "custom"}
    )
    assert isinstance(provider, SentenceTransformerEmbeddingProvider)
    mock_model_cls.assert_called_once_with("custom")


@patch("python_vectordb.embeddings.sentence_transformer.SentenceTransformer")
def test_sentence_transformer_applies_e5_prefixes(mock_model_cls):
    model = MagicMock()
    model.get_sentence_embedding_dimension.return_value = 384

    def fake_encode(value):
        if isinstance(value, str):
            return MagicMock(tolist=lambda: [0.1] * 384)
        return MagicMock(tolist=lambda: [[0.1] * 384])

    model.encode.side_effect = fake_encode
    mock_model_cls.return_value = model

    provider = SentenceTransformerEmbeddingProvider("e5-small-multilingual")
    assert provider.query_prefix == "query: "
    assert provider.passage_prefix == "passage: "

    provider.encode_texts(["doc"])
    provider.encode_query("q")

    # encode_texts bekommt die passage-prefixed Liste, encode_query den query-prefixed Str.
    assert model.encode.call_args_list[0].args[0] == ["passage: doc"]
    assert model.encode.call_args_list[1].args[0] == "query: q"
    # Alias wurde auf die volle HF-Modell-ID aufgelöst.
    mock_model_cls.assert_called_once_with("intfloat/multilingual-e5-small")


def test_embedding_factory_unknown():
    with pytest.raises(ValueError, match="Unknown embedding provider"):
        EmbeddingProviderFactory.create({"embedding_provider": "nope"})


def test_embedding_provider_is_abstract():
    with pytest.raises(TypeError):
        EmbeddingProvider()  # type: ignore[abstract]
