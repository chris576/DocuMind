import logging
from typing import List

from sentence_transformers import SentenceTransformer

from .base import EmbeddingProvider
from .models import EmbeddingModelSpec, resolve_model_spec

logger = logging.getLogger("python_vectordb.embeddings.sentence_transformer")


class SentenceTransformerEmbeddingProvider(EmbeddingProvider):
    """EmbeddingProvider backed by a local sentence-transformers model.

    Akzeptiert einen Modellnamen oder Alias. Für E5-/BGE-Modelle werden die
    asymmetrischen Query-/Passage-Prefixe automatisch angewendet.
    """

    def __init__(self, model_name: str):
        self.model_name = model_name
        spec: EmbeddingModelSpec = resolve_model_spec(model_name)
        self.query_prefix = spec.query_prefix
        self.passage_prefix = spec.passage_prefix
        self._model = SentenceTransformer(spec.model_id)
        self._dimension = self._model.get_sentence_embedding_dimension()
        logger.info(
            "Loaded embedding model: %s (dim=%d)", spec.model_id, self._dimension
        )

    @property
    def dimension(self) -> int:
        return self._dimension

    def encode_texts(self, texts: List[str]) -> List[List[float]]:
        if self.passage_prefix:
            texts = [self.passage_prefix + t for t in texts]
        return self._model.encode(texts).tolist()

    def encode_query(self, text: str) -> List[float]:
        if self.query_prefix:
            text = self.query_prefix + text
        return self._model.encode(text).tolist()
