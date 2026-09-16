"""Similarity metric mapping and score normalization for PGVector.

The vector database adapter accepts a normalized, database-agnostic metric
name (``SIMILARITY_METRIC``) and translates it to the native PostgreSQL
distance operator via the mapping table below. Scores are normalized so
that "higher = more similar" across all metrics where native values need
rescaling.

Supported metrics: ``cosine``, ``euclidean``, ``dot``.
"""

from typing import Dict

VALID_METRICS: tuple[str, ...] = ("cosine", "euclidean", "dot")

# Keyword retrieval strategy per vector database type.
KEYWORD_DEFAULTS: Dict[str, str] = {
    "pgvector": "fts",  # PostgreSQL tsvector / ts_rank full text search
}


def resolve_keyword_method(db_type: str, method: str = "auto") -> str:
    """Resolve the keyword retrieval strategy for a database type.

    ``auto`` selects the database's default strategy; explicit overrides are
    returned as-is (the adapter is responsible for honoring them).
    """
    if method != "auto":
        return method.lower()
    return KEYWORD_DEFAULTS.get(db_type.lower(), "fts")

# PGVector distance operators used in ORDER BY and the SELECT score expression.
PGVECTOR_OPERATORS: Dict[str, str] = {
    "cosine": "<=>",
    "euclidean": "<->",
    "dot": "<#>",
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
