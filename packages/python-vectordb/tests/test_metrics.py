"""Unit tests for the cross-adapter similarity metric mapping module."""
import pytest

from python_vectordb.vector_db.metrics import (
    CHROMA_SPACES,
    PGVECTOR_OPERATORS,
    QDRANT_DISTANCES,
    VALID_METRICS,
    normalize_pgvector_score,
    validate_metric,
)


def test_valid_metric_names():
    assert VALID_METRICS == ("cosine", "euclidean", "dot", "manhattan")


def test_validate_metric_normalizes_case():
    assert validate_metric("EUCLIDEAN") == "euclidean"
    assert validate_metric("Cosine") == "cosine"


def test_validate_metric_rejects_unknown():
    with pytest.raises(ValueError, match="Unsupported similarity metric"):
        validate_metric("hamming")


def test_mapping_tables_consistency():
    # userland/manhattan is Qdrant-only.
    assert "cosine" in CHROMA_SPACES
    assert "cosine" in PGVECTOR_OPERATORS
    assert "manhattan" in QDRANT_DISTANCES
    assert "manhattan" not in CHROMA_SPACES
    assert "manhattan" not in PGVECTOR_OPERATORS


def test_pgvector_operators():
    assert PGVECTOR_OPERATORS == {
        "cosine": "<=>",
        "euclidean": "<->",
        "dot": "<#>",
    }


def test_chroma_spaces():
    assert CHROMA_SPACES == {
        "cosine": "cosine",
        "euclidean": "l2",
        "dot": "ip",
    }


def test_qdrant_distances():
    assert QDRANT_DISTANCES == {
        "cosine": "COSINE",
        "euclidean": "EUCLID",
        "dot": "DOT",
        "manhattan": "MANHATTAN",
    }


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
