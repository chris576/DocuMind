from dataclasses import dataclass


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
