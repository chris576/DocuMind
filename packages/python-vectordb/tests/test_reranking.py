"""Unit tests for python-vectordb reranking."""
from unittest.mock import MagicMock, patch

import pytest

from python_vectordb.reranking.base import Reranker
from python_vectordb.reranking.cross_encoder import CrossEncoderReranker
from python_vectordb.reranking.factory import RerankerFactory


@patch("python_vectordb.reranking.cross_encoder.CrossEncoder")
def test_cross_encoder_rerank_orders_and_limits(mock_ce_cls):
    model = MagicMock()
    # Scores favor the first candidate.
    model.predict.return_value = [3.0, 1.0, 0.5]
    mock_ce_cls.return_value = model

    reranker = CrossEncoderReranker("ce-model")
    candidates = [
        {"title": "a", "content": "alpha"},
        {"title": "b", "content": "beta"},
        {"title": "c", "content": "gamma"},
    ]
    result = reranker.rerank("query", candidates, top_k=2)

    mock_ce_cls.assert_called_once_with("ce-model")
    assert len(result) == 2
    # Sorted descending by cross_score -> 'a' first.
    assert result[0]["title"] == "a"
    assert result[1]["title"] == "b"
    assert 0.0 < result[0]["cross_score"] < 1.0


@patch("python_vectordb.reranking.cross_encoder.CrossEncoder")
def test_cross_encoder_rerank_empty(mock_ce_cls):
    reranker = CrossEncoderReranker("ce-model")
    assert reranker.rerank("q", []) == []
    mock_ce_cls.return_value.predict.assert_not_called()


@patch("python_vectordb.reranking.cross_encoder.CrossEncoder")
def test_cross_encoder_rerank_no_top_k_returns_all(mock_ce_cls):
    model = MagicMock()
    model.predict.return_value = [0.0, 0.0]
    mock_ce_cls.return_value = model

    reranker = CrossEncoderReranker("ce-model")
    candidates = [{"title": "a"}, {"title": "b"}]
    result = reranker.rerank("q", candidates)
    assert len(result) == 2


def test_reranker_factory_default():
    with patch("python_vectordb.reranking.cross_encoder.CrossEncoder") as mock_ce:
        mock_ce.return_value = MagicMock()
        reranker = RerankerFactory.create({})
        assert isinstance(reranker, CrossEncoderReranker)
        mock_ce.assert_called_once_with("cross-encoder/ms-marco-MiniLM-L-6-v2")


def test_reranker_factory_custom_model():
    with patch("python_vectordb.reranking.cross_encoder.CrossEncoder") as mock_ce:
        mock_ce.return_value = MagicMock()
        reranker = RerankerFactory.create(
            {"reranker_provider": "cross_encoder", "cross_encoder_model": "custom"}
        )
        assert isinstance(reranker, CrossEncoderReranker)
        mock_ce.assert_called_once_with("custom")


def test_reranker_factory_unknown():
    with pytest.raises(ValueError, match="Unknown reranker provider"):
        RerankerFactory.create({"reranker_provider": "nope"})


def test_reranker_is_abstract():
    with pytest.raises(TypeError):
        Reranker()  # type: ignore[abstract]
