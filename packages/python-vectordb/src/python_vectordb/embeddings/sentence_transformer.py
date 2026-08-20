import logging
from typing import List

from sentence_transformers import SentenceTransformer

from .base import EmbeddingProvider

logger = logging.getLogger("python_vectordb.embeddings.sentence_transformer")


class SentenceTransformerEmbeddingProvider(EmbeddingProvider):
    """EmbeddingProvider backed by a local sentence-transformers model."""

    def __init__(self, model_name: str):
        self.model_name = model_name
        self._model = SentenceTransformer(model_name)
        self._dimension = self._model.get_sentence_embedding_dimension()
        logger.info(
            f"Loaded embedding model: {model_name} (dim={self._dimension})"
        )

    @property
    def dimension(self) -> int:
        return self._dimension

    def encode_texts(self, texts: List[str]) -> List[List[float]]:
        return self._model.encode(texts).tolist()

    def encode_query(self, text: str) -> List[float]:
        return self._model.encode(text).tolist()