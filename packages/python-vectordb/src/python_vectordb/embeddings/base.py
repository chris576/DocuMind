from abc import ABC, abstractmethod
from typing import List


class EmbeddingProvider(ABC):
    """Port for embedding functions.

    Concrete implementations (e.g. SentenceTransformer) are selected via
    configuration and injected into vector database adapters. Consumers never
    depend on a concrete embedding implementation.
    """

    @property
    @abstractmethod
    def dimension(self) -> int:
        """Dimensionality of the produced embedding vectors."""
        pass

    @abstractmethod
    def encode_texts(self, texts: List[str]) -> List[List[float]]:
        """Encode a list of texts into embedding vectors."""
        pass

    @abstractmethod
    def encode_query(self, text: str) -> List[float]:
        """Encode a single query text into an embedding vector."""
        pass