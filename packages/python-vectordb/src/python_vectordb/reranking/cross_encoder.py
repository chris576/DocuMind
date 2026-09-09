import logging
import math
from typing import Any, Dict, List

from sentence_transformers import CrossEncoder

from .base import Reranker
from .models import resolve_reranker_model

logger = logging.getLogger("python_vectordb.reranking.cross_encoder")


class CrossEncoderReranker(Reranker):
    """Reranker backed by a local cross-encoder model."""

    def __init__(self, model_name: str):
        self.model_name = resolve_reranker_model(model_name)
        self._model = CrossEncoder(self.model_name)
        logger.info(f"Loaded cross-encoder model: {self.model_name}")

    def rerank(
        self, query: str, candidates: List[Dict[str, Any]], top_k: int | None = None
    ) -> List[Dict[str, Any]]:
        if not candidates:
            return []

        pairs = [
            (query, f"{c.get('title', '')} {str(c.get('content', ''))[:500]}")
            for c in candidates
        ]
        scores = self._model.predict(pairs)

        for candidate, score in zip(candidates, scores):
            candidate["cross_score"] = float(1.0 / (1.0 + math.exp(-score)))

        candidates.sort(key=lambda x: x.get("cross_score", 0.0), reverse=True)
        return candidates[:top_k] if top_k is not None else candidates
