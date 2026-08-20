from dataclasses import dataclass


@dataclass
class SearchQuery:
    """Search for similar documents."""

    query: str
    top_k: int = 10


@dataclass
class GetStatusQuery:
    """Return the current status of the vector database."""