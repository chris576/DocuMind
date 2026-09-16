from dataclasses import dataclass
from typing import Any


@dataclass
class SearchQuery:
    """Search for similar documents."""

    query: str
    top_k: int = 10


@dataclass
class HybridSearchQuery:
    """Hybrid keyword + semantic search across both retrieval channels.

    The concrete fusion strategy is an adapter concern: the adapter decides
    whether it uses a native BM25/FTS implementation, a local BM25 index, or a
    rank-based fusion — the pipeline only asks "give me your best hybrid
    results".
    """

    query: str
    top_k: int = 10


@dataclass
class GetStatusQuery:
    """Return the current status of the vector database."""


@dataclass
class FactsQuery:
    """Query denormalized facts from the document fact table.

    Filters on namespace/document_type/key/value plus an optional numeric
    aggregation (sum/avg/min/max/count) over the ``key`` column in ``extracted``.
    """

    document_type: str | None = None
    key: str | None = None
    value: Any = None
    from_date: str | None = None
    to_date: str | None = None
    namespace: str | None = None
    limit: int = 100
    aggregate: str | None = None
