import logging
from datetime import datetime
from typing import List

from python_vectordb.reranking import Reranker, RerankerFactory
from python_vectordb.vector_db import (
    GetStatusQuery,
    HybridSearchQuery,
    VectorDBFactory,
)
from python_vectordb.vector_db.bus import VectorDBCommandBus

from .models import SearchEngineStatus, SearchRequest, SearchResult

logger = logging.getLogger("retrieval")


class SearchEngine:
    def __init__(self, config: dict):
        self.vector_db_type = config.get("vector_db_type", "chroma")
        self.chroma_url = config.get("chroma_url", "http://localhost:8000")
        self.qdrant_url = config.get("qdrant_url", "http://localhost:6333")
        self.qdrant_api_key = config.get("qdrant_api_key")
        self.pgvector_url = config.get("pgvector_url")
        self.collection_name = config.get("collection_name", "documents")
        self.embedding_model_name = config.get("embedding_model", "paraphrase-multilingual-MiniLM-L12-v2")
        self.embedding_provider = config.get("embedding_provider", "sentence_transformer")
        self.similarity_metric = config.get("similarity_metric", "cosine")
        self.cross_encoder_model_name = config.get("cross_encoder_model", "cross-encoder/ms-marco-MiniLM-L-6-v2")
        self.max_results = config.get("max_results", 20)

        # Foreign (untyped) object; declared Any so mypy does not flag access.
        self.vector_db: VectorDBCommandBus | None = None
        self.is_initialized = False

        self.reranker: Reranker | None = None

        self.status = SearchEngineStatus()

    def _vector_db_config(self) -> dict:
        db_type = self.vector_db_type.lower()
        db_config = {
            "type": db_type,
            "collection": self.collection_name,
            "embedding_model": self.embedding_model_name,
            "embedding_provider": self.embedding_provider,
            "similarity_metric": self.similarity_metric,
        }
        if db_type == "chroma":
            db_config["url"] = self.chroma_url
        elif db_type == "qdrant":
            db_config["url"] = self.qdrant_url
            db_config["api_key"] = self.qdrant_api_key
        elif db_type == "pgvector":
            db_config["url"] = self.pgvector_url
        return db_config

    def initialize(self) -> bool:
        try:
            if self.reranker is None:
                logger.info("Initializing reranker")
                self.reranker = RerankerFactory.create(
                    {"reranker_provider": "cross_encoder", "cross_encoder_model": self.cross_encoder_model_name}
                )

            self.is_initialized = True
            self.status.initialized = True
            self.status.last_updated = datetime.now().isoformat()
            return True
        except Exception as e:
            logger.error(f"Error initializing search engine: {str(e)}")
            self.is_initialized = False
            self.status.initialized = False
            return False

    def setup_vector_db(self) -> bool:
        try:
            if self.vector_db is None:
                self.vector_db = VectorDBFactory.create_reader(self._vector_db_config())

            status = self.vector_db.ask(GetStatusQuery())
            logger.info(f"Loaded vector database with {status.get('document_count', 0)} documents")
            self.status.chroma_ready = status.get("ready", False)
            self.status.documents_count = status.get("document_count", 0)
            return True
        except Exception as e:
            logger.error(f"Error setting up vector database: {str(e)}")
            self.status.chroma_ready = False
            return False

    def semantic_search(self, query: str, top_k: int | None = None) -> List[dict]:
        """Semantic-only search via the CQRS read bus."""
        if not self.vector_db:
            raise Exception("Vector database not initialized")

        top_k = top_k or self.max_results
        results = self.vector_db.ask(HybridSearchQuery(query=query, top_k=min(top_k, 100)))

        documents = []
        for result in results:
            metadata = result.metadata or {}
            documents.append(
                {
                    "id": result.id,
                    "title": result.title,
                    "correspondent": metadata.get("correspondent", ""),
                    "date": metadata.get("created", ""),
                    "score": float(result.score),
                    "content": result.content,
                }
            )

        return documents

    def hybrid_search(self, query: str, top_k: int | None = None) -> List[dict]:
        """Hybrid search, fully delegated to the adapter (CQRS read bus).

        The adapter owns its keyword implementation (native BM25, FTS or local
        BM25) and returns already-fused results; the engine only normalizes the
        result shape for downstream use.
        """
        if not self.vector_db:
            raise Exception("Vector database not initialized")

        top_k = top_k or self.max_results
        results = self.vector_db.ask(HybridSearchQuery(query=query, top_k=top_k))

        documents = []
        for result in results:
            metadata = result.metadata or {}
            documents.append(
                {
                    "id": result.id,
                    "title": result.title,
                    "correspondent": metadata.get("correspondent", ""),
                    "date": metadata.get("created", ""),
                    "score": float(result.score),
                    "content": result.content,
                }
            )

        return documents

    def rerank_results(self, query: str, results: List[dict], top_k: int | None = None) -> List[dict]:
        if not results:
            return []

        top_k = top_k or self.max_results

        try:
            if self.reranker is None:
                raise Exception("Reranker not initialized")
            reranked = self.reranker.rerank(query, results, top_k)
            return list(reranked) if reranked else []
        except Exception as e:
            logger.error(f"Error reranking: {str(e)}")
            for r in results:
                r["cross_score"] = 0.5
            return results[:top_k]

    def create_snippet(self, query: str, content: str, max_len: int = 200) -> str:
        if not content:
            return ""

        try:
            query_terms = set(query.lower().split())
            sentences = content.split(". ")

            sentence_scores = []
            for sentence in sentences:
                sentence_terms = set(sentence.lower().split())
                score = len(query_terms.intersection(sentence_terms))
                sentence_scores.append((sentence, score))

            sentence_scores.sort(key=lambda x: x[1], reverse=True)

            snippet = ""
            for sentence, _ in sentence_scores:
                if len(snippet) + len(sentence) <= max_len:
                    snippet += sentence + ". "
                else:
                    break

            if not snippet:
                snippet = content[:max_len] + "..."

            return snippet.strip()
        except Exception as e:
            logger.error(f"Error creating snippet: {str(e)}")
            return content[:max_len] + "..." if content else ""

    def search(self, request: SearchRequest) -> List[SearchResult]:
        if not self.is_initialized:
            self.initialize()

        results = self.hybrid_search(request.query, request.max_results)

        if request.from_date or request.to_date or request.correspondent:
            filtered = []
            for result in results:
                include = True

                if request.from_date and result.get("date"):
                    if result["date"].split("T")[0] < request.from_date:
                        include = False

                if request.to_date and result.get("date"):
                    if result["date"].split("T")[0] > request.to_date:
                        include = False

                if request.correspondent and result.get("correspondent"):
                    if request.correspondent.lower() not in result["correspondent"].lower():
                        include = False

                if include:
                    filtered.append(result)
            results = filtered

        reranked = self.rerank_results(request.query, results, request.max_results)

        formatted = []
        for result in reranked:
            snippet = self.create_snippet(request.query, result.get("content", ""))
            formatted.append(
                SearchResult(
                    title=result.get("title", "Untitled"),
                    correspondent=result.get("correspondent", ""),
                    date=result.get("date", ""),
                    score=result.get("score", 0),
                    cross_score=result.get("cross_score", 0.5),
                    snippet=snippet,
                    doc_id=result.get("id"),
                    content=result.get("content", "")[:500],
                )
            )

        return formatted

    def get_status(self) -> dict:
        return {
            "service": "retrieval-pipeline",
            "initialized": self.is_initialized,
            "vector_db_type": self.vector_db_type,
            "vector_db_ready": self.status.chroma_ready,
            "chroma_ready": self.status.chroma_ready,
            "last_updated": self.status.last_updated,
        }
