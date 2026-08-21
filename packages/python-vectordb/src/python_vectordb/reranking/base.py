from abc import ABC, abstractmethod
from typing import Any, Dict, List


class Reranker(ABC):
    """Port for cross-encoder based reranking.

    A reranker scores (query, document) pairs jointly, which is more precise
    than vector similarity. It is applied only to a shortlist of candidates.
    """

    @abstractmethod
    def rerank(
        self, query: str, candidates: List[Dict[str, Any]], top_k: int | None = None
    ) -> List[Dict[str, Any]]:
        """Rerank candidate documents and return the top_k, sorted by cross score.

        Each candidate is a dict that is mutated to include a normalized
        ``cross_score`` key.
        """
        pass
