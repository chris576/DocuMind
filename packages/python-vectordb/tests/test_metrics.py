"""Unit tests for the PGVector similarity metric mapping module."""
import pytest

from python_vectordb.vector_db.metrics import (
    PGVECTOR_OPERATORS,
    VALID_METRICS,
    normalize_pgvector_score,
    resolve_keyword_method,
    validate_metric,
)


def test_valid_metric_names():
    assert VALID_METRICS == ("cosine", "euclidean", "dot")


def test_validate_metric_normalizes_case():
    assert validate_metric("EUCLIDEAN") == "euclidean"
    assert validate_metric("Cosine") == "cosine"


def test_validate_metric_rejects_unknown():
    with pytest.raises(ValueError, match="Unsupported similarity metric"):
        validate_metric("hamming")


def test_pgvector_operators():
    assert PGVECTOR_OPERATORS == {
        "cosine": "<=>",
        "euclidean": "<->",
        "dot": "<#>",
    }


def test_resolve_keyword_method_auto_defaults():
    assert resolve_keyword_method("pgvector") == "fts"
    assert resolve_keyword_method("unknown") == "fts"


def test_resolve_keyword_method_explicit_override():
    assert resolve_keyword_method("pgvector", "local") == "local"
    assert resolve_keyword_method("pgvector", "NATIVE") == "native"


@pytest.mark.parametrize(
    "metric,raw,expected",
    [
        ("cosine", 0.2, 0.2),
        ("euclidean", 0.0, 1.0),
        ("euclidean", 1.0, 0.5),
        ("euclidean", 3.0, 0.25),
        ("dot", -0.8, 0.8),
    ],
)
def test_normalize_pgvector_score(metric, raw, expected):
    assert normalize_pgvector_score(metric, raw) == pytest.approx(expected)
