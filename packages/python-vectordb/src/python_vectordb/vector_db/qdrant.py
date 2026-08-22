import logging
import uuid
from typing import Any, Dict, List

from qdrant_client import QdrantClient
from qdrant_client.http import models

from ..embeddings import EmbeddingProvider
from .base import BaseVectorDB, VectorDBDocument, VectorDBSearchResult
from .metrics import QDRANT_DISTANCES, resolve_keyword_method

logger = logging.getLogger("python_vectordb.vector_db.qdrant")


def _to_point_id(doc_id: str) -> int | str | uuid.UUID:
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
        self.similarity_metric = config.get("similarity_metric", "cosine").lower()
        self.distance = models.Distance[QDRANT_DISTANCES[self.similarity_metric]]
        self.keyword_method = resolve_keyword_method("qdrant", config.get("keyword_method", "auto"))
        self.keyword_weight = float(config.get("keyword_weight", 0.3))
        self.semantic_weight = float(config.get("semantic_weight", 0.7))
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
                        distance=self.distance,
                    ),
                )

            # Ensure full-text payload indexes so the native BM25 query works.
            self._ensure_keyword_indexes()

            self.ready = True
            logger.info(f"Qdrant initialized: {self.collection_name}")
            return True
        except Exception as e:
            logger.error(f"Qdrant initialization failed: {str(e)}")
            self.ready = False
            return False

    def _ensure_keyword_indexes(self) -> None:
        """Best-effort fulltext payload index creation for BM25 search fields."""
        if not self.client:
            return
        existing = set()
        try:
            info = self.client.get_collection(self.collection_name)
            for field in (info.payload_schema or {}):
                existing.add(field)
        except Exception as e:
            logger.debug(f"Could not inspect payload schema: {e}")

        for field in ("title", "content"):
            if field in existing:
                continue
            try:
                self.client.create_payload_index(
                    collection_name=self.collection_name,
                    field_name=field,
                    field_schema=models.TextIndexParams(
                        type=models.TextIndexType.TEXT,
                        tokenizer=models.TokenizerType.WORD,
                        lowercase=True,
                    ),
                )
                logger.info(f"Created fulltext index on '{field}'")
            except Exception as e:
                logger.warning(f"Could not create fulltext index on '{field}': {e}")

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

    def delete_documents(self, document_ids: List[str]) -> None:
        if not self.ready or not self.client:
            raise Exception("Qdrant not initialized")
        if not document_ids:
            return
        point_ids = [_to_point_id(doc_id) for doc_id in document_ids]
        self.client.delete(
            collection_name=self.collection_name,
            points_selector=models.PointIdsList(points=point_ids),
        )
        logger.info(f"Deleted {len(document_ids)} documents from Qdrant")

    def hybrid_search(self, query: str, top_k: int = 10) -> List[VectorDBSearchResult]:
        """Hybrid search: native fulltext (BM25) + semantic, fused inside the adapter.

        Uses Qdrant prefetch with a nearest query and a fulltext payload match
        (on ``title``/``content``), merged by Reciprocal Rank Fusion (RRF).
        The pipeline receives a single fused result list; only the adapter
        knows the concrete Qdrant-level fusion.
        """
        if not self.ready or not self.client:
            raise Exception("Qdrant not initialized")

        return self._prefetch_hybrid(query, top_k)

    def _prefetch_hybrid(self, query: str, top_k: int) -> List[VectorDBSearchResult]:
        """Run the native Qdrant prefetch query (nearest + fulltext) + RRF fusion."""
        fetch_n = max(top_k * 2, 10)
        prefetch: List[Dict[str, Any]] = []

        query_vector = self.embedding_provider.encode_query(query)
        prefetch.append({"query": query_vector, "using": None, "limit": fetch_n})

        if self.keyword_method in ("native", "bm25"):
            prefetch.append(
                {
                    "query": query_vector,
                    "using": None,
                    "filter": models.Filter(
                        should=[
                            models.FieldCondition(
                                key=field,
                                match=models.MatchText(text=query),
                            )
                            for field in ("title", "content")
                        ]
                    ),
                    "params": models.SearchParams(),
                    "limit": fetch_n,
                }
            )

        if not prefetch:
            return []

        resp = self.client.query_points(
            collection_name=self.collection_name,
            prefetch=prefetch,
            query=models.FusionQuery(fusion=models.Fusion.RRF),
            limit=top_k,
        )

        documents = []
        for point in resp.points:
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

    def get_status(self) -> Dict[str, Any]:
        if not self.ready or not self.client:
            return {"ready": False, "document_count": 0}
        try:
            info = self.client.get_collection(self.collection_name)
            return {"ready": True, "document_count": info.points_count or 0}
        except Exception:
            return {"ready": False, "document_count": 0}
