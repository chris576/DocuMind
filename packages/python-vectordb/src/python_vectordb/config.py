import os
from dataclasses import dataclass
from typing import Any, Dict, Optional


@dataclass
class VectorDBConfig:
    """Configuration for the vector database + embedding + reranking stack.

    Fully determined by environment variables; loaded by load_vector_db_config().
    """

    vector_db_type: str
    embedding_provider: str
    reranker_provider: str
    collection_name: str
    embedding_model: str
    cross_encoder_model: str
    chroma_url: Optional[str] = None
    qdrant_url: Optional[str] = None
    qdrant_api_key: Optional[str] = None
    pgvector_url: Optional[str] = None

    def to_vector_db_config(self) -> Dict[str, Any]:
        """Build the dict expected by VectorDBFactory (delegates embedding)."""
        db_type = self.vector_db_type.lower()
        db_config: Dict[str, Any] = {
            "type": db_type,
            "collection": self.collection_name,
            "embedding_model": self.embedding_model,
            "embedding_provider": self.embedding_provider,
        }
        if db_type == "chroma":
            db_config["url"] = self.chroma_url or "http://localhost:8000"
        elif db_type == "qdrant":
            db_config["url"] = self.qdrant_url or "http://localhost:6333"
            db_config["api_key"] = self.qdrant_api_key
        elif db_type == "pgvector":
            db_config["url"] = self.pgvector_url
        return db_config

    def to_embedding_config(self) -> Dict[str, Any]:
        """Build the dict expected by EmbeddingProviderFactory."""
        return {
            "embedding_provider": self.embedding_provider,
            "embedding_model": self.embedding_model,
        }

    def to_reranker_config(self) -> Dict[str, Any]:
        """Build the dict expected by RerankerFactory."""
        return {
            "reranker_provider": self.reranker_provider,
            "cross_encoder_model": self.cross_encoder_model,
        }


def load_vector_db_config() -> VectorDBConfig:
    """Load vector database / embedding / reranker configuration from env vars."""
    return VectorDBConfig(
        vector_db_type=os.getenv("VECTOR_DB_TYPE", "chroma"),
        embedding_provider=os.getenv("EMBEDDING_PROVIDER", "sentence_transformer"),
        reranker_provider=os.getenv("RERANKER_PROVIDER", "cross_encoder"),
        collection_name=os.getenv("COLLECTION_NAME", "documents"),
        embedding_model=os.getenv(
            "EMBEDDING_MODEL", "paraphrase-multilingual-MiniLM-L12-v2"
        ),
        cross_encoder_model=os.getenv(
            "CROSS_ENCODER_MODEL", "cross-encoder/ms-marco-MiniLM-L-6-v2"
        ),
        chroma_url=os.getenv("CHROMA_URL", "http://localhost:8000"),
        qdrant_url=os.getenv("QDRANT_URL", "http://localhost:6333"),
        qdrant_api_key=os.getenv("QDRANT_API_KEY"),
        pgvector_url=os.getenv("PGVECTOR_URL"),
    )