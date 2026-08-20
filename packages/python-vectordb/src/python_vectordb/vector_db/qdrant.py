import logging
import uuid
from typing import Any, Dict, List, Union

from qdrant_client import QdrantClient
from qdrant_client.http import models

from ..embeddings import EmbeddingProvider
from .base import BaseVectorDB, VectorDBDocument, VectorDBSearchResult

logger = logging.getLogger("python_vectordb.vector_db.qdrant")


def _to_point_id(doc_id: str) -> Union[int, str, uuid.UUID]:
    """Convert a document id to a Qdrant-compatible point id.

    Qdrant accepts unsigned integers or UUID strings. Numeric ids (e.g. Paperless
    document ids) are passed through as ints, UUIDs as-is, and any other string is
    mapped to a deterministic UUID so upserts never fail.
    """
    if isinstance(doc_id, int):
        return doc_id
    try:
        return int(doc_id)
    except (ValueError, TypeError):
        pass
    try:
        return uuid.UUID(str(doc_id))
    except (ValueError, AttributeError):
        pass
    return uuid.uuid5(uuid.NAMESPACE_DNS, str(doc_id))


class QdrantVectorDB(BaseVectorDB):
    def __init__(self, config: Dict[str, Any], embedding_provider: EmbeddingProvider):
        self.config = config
        self.url = config.get("url", "http://localhost:6333")
        self.api_key = config.get("api_key")
        self.collection_name = config.get("collection", "documents")
        self.embedding_provider = embedding_provider
        self.embedding_dimension = config.get("embedding_dimension", 384)
        self.client = None
        self.ready = False

    def initialize(self) -> bool:
        try:
            self.client = QdrantClient(url=self.url, api_key=self.api_key)

            collections = self.client.get_collections()
            collection_exists = any(
                c.name == self.collection_name for c in collections.collections
            )

            if not collection_exists:
                self.client.create_collection(
                    collection_name=self.collection_name,
                    vectors_config=models.VectorParams(
                        size=self.embedding_dimension,
                        distance=models.Distance.COSINE,
                    ),
                )

            self.ready = True
            logger.info(f"Qdrant initialized: {self.collection_name}")
            return True
        except Exception as e:
            logger.error(f"Qdrant initialization failed: {str(e)}")
            self.ready = False
            return False

    def add_documents(self, documents: List[VectorDBDocument]) -> None:
        if not self.ready or not self.client:
            raise Exception("Qdrant not initialized")

        batch_size = 100
        for i in range(0, len(documents), batch_size):
            batch = documents[i : i + batch_size]
            texts = [f"{doc.title} {doc.content}" for doc in batch]
            vectors = self.embedding_provider.encode_texts(texts)

            points = [
                models.PointStruct(
                    id=_to_point_id(doc.id),
                    vector=vector,
                    payload={"title": doc.title, "content": doc.content, **doc.metadata},
                )
                for doc, vector in zip(batch, vectors)
            ]

            self.client.upsert(collection_name=self.collection_name, points=points)

        logger.info(f"Added {len(documents)} documents to Qdrant")

    def search(self, query: str, top_k: int = 10) -> List[VectorDBSearchResult]:
        if not self.ready or not self.client:
            raise Exception("Qdrant not initialized")

        query_vector = self.embedding_provider.encode_query(query)
        results = self.client.query_points(
            collection_name=self.collection_name,
            query=query_vector,
            limit=top_k,
        )

        documents = []
        for point in results.points:
            payload = point.payload or {}
            documents.append(
                VectorDBSearchResult(
                    id=str(point.id),
                    title=payload.get("title", ""),
                    content=payload.get("content", ""),
                    score=float(point.score),
                    metadata=payload,
                )
            )
        return documents

    def delete_collection(self) -> None:
        if not self.client:
            raise Exception("Qdrant not initialized")
        self.client.delete_collection(self.collection_name)
        self.ready = False

    def get_status(self) -> Dict[str, Any]:
        if not self.ready or not self.client:
            return {"ready": False, "document_count": 0}
        try:
            info = self.client.get_collection(self.collection_name)
            return {"ready": True, "document_count": info.points_count or 0}
        except Exception:
            return {"ready": False, "document_count": 0}