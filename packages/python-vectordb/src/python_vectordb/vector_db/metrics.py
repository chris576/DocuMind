"""Cross-adapter similarity metric mapping and score normalization.

The vector database adapters accept a normalized, database-agnostic metric
name (``SIMILARITY_METRIC``) and translate it to their native distance
operator / space / enum via the mapping tables below. Scores are normalized
so that "higher = more similar" across all metrics where native values need
rescaling.

Supported metrics: ``cosine``, ``euclidean``, ``dot``, ``manhattan``.
``manhattan`` is only supported by Qdrant; choosing it for Chroma or
PGVector raises a ``KeyError`` at adapter use time.
"""

from typing import Dict

VALID_METRICS: tuple[str, ...] = ("cosine", "euclidean", "dot", "manhattan")

# Keyword retrieval strategy per vector database type.
KEYWORD_DEFAULTS: Dict[str, str] = {
    "qdrant": "native",    # Qdrant native BM25 query + fusion
    "pgvector": "fts",     # PostgreSQL tsvector / ts_rank full text search
    "chroma": "local",     # in-adapter local BM25 index (rank-bm25 + nltk)
}


def resolve_keyword_method(db_type: str, method: str = "auto") -> str:
    """Resolve the keyword retrieval strategy for a database type.

    ``auto`` selects the database's default strategy; explicit overrides are
    returned as-is (the adapter is responsible for honoring them).
    """
    if method != "auto":
        return method.lower()
    return KEYWORD_DEFAULTS.get(db_type.lower(), "local")

# PGVector distance operators used in ORDER BY and the SELECT score expression.
PGVECTOR_OPERATORS: Dict[str, str] = {
    "cosine": "<=>",
    "euclidean": "<->",
    "dot": "<#>",
}

# ChromaDB ``hnsw:space`` values. Set once at collection creation time.
CHROMA_SPACES: Dict[str, str] = {
    "cosine": "cosine",
    "euclidean": "l2",
    "dot": "ip",
}

# Qdrant Distance enum member names (resolved via getattr(models.Distance, _)).
QDRANT_DISTANCES: Dict[str, str] = {
    "cosine": "COSINE",
    "euclidean": "EUCLID",
    "dot": "DOT",
    "manhattan": "MANHATTAN",
}


def validate_metric(metric: str) -> str:
    """Validate a similarity metric name, returning the normalized lowercase name."""
    normalized = metric.lower()
    if normalized not in VALID_METRICS:
        supported = ", ".join(VALID_METRICS)
        raise ValueError(
            f"Unsupported similarity metric: {metric}. "
            f"Supported metrics: {supported}"
        )
    return normalized


def normalize_pgvector_score(metric: str, raw_distance: float) -> float:
    """Convert a raw PGVector distance value to a "higher = more similar" score.

    For ``cosine`` the SQL expression already returns ``1 - distance``; the
    other operators return raw values that need rescaling.
    """
    metric = metric.lower()
    if metric == "euclidean":
        # Euclidean distance is non-negative; map to (0, 1].
        return 1.0 / (1.0 + raw_distance)
    if metric == "dot":
        # ``<#>`` returns the negative inner product; negate to get similarity.
        return -raw_distance
    return raw_distance
