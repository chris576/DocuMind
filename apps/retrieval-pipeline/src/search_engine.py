import logging
from datetime import datetime
from typing import Dict, List

from python_vectordb.reranking import Reranker, RerankerFactory
from python_vectordb.vector_db import (
    GetStatusQuery,
    HybridSearchQuery,
    VectorDBFactory,
)
from python_vectordb.vector_db.bus import VectorDBCommandBus

from .models import SearchEngineStatus, SearchRequest, SearchResult

logger = logging.getLogger("retrieval")


class VectorDBNotInitializedError(Exception):
    """Raised when the vector database has not been initialized."""


class RerankerNotInitializedError(Exception):
    """Raised when the reranker has not been initialized."""


class SearchEngine:
    def __init__(self, config: dict):
        self.config = dict(config)
        self.vector_db_type = config.get("type", config.get("vector_db_type", "pgvector"))
        self.collection_name = config.get("collection", config.get("collection_name", "documents"))
        self.collections: List[str] = config.get("collections") or [self.collection_name]
        self.embedding_model_name = config.get("embedding_model", "paraphrase-multilingual-MiniLM-L12-v2")
        self.embedding_provider = config.get("embedding_provider", "sentence_transformer")
        self.cross_encoder_model_name = config.get("cross_encoder_model", "cross-encoder/ms-marco-MiniLM-L-6-v2")
        self.max_results = config.get("max_results", 20)

        # Foreign (untyped) object; declared Any so mypy does not flag access.
        self.vector_db: VectorDBCommandBus | None = None
        self.readers: Dict[str, VectorDBCommandBus] = {}
        self.is_initialized = False

        self.reranker: Reranker | None = None

        self.status = SearchEngineStatus()

    def _vector_db_config(self) -> dict:
        """Build the config dict for VectorDBFactory (PGVector-only).

        The config already carries url/collection/embedding/reranking knobs;
        only the ``type`` key is normalized for the factory.
        """
        return {**self.config, "type": self.vector_db_type}

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
        except Exception:
            logger.exception("Error initializing search engine")
            self.is_initialized = False
            self.status.initialized = False
            return False

    def setup_vector_db(self) -> bool:
        try:
            if not self.readers:
                self.readers = VectorDBFactory.create_readers(self._vector_db_config(), self.collections)
                if self.readers:
                    # Keep the single-reader attribute for backward compatibility.
                    self.vector_db = next(iter(self.readers.values()))

            total = 0
            ready = True
            for reader in self.readers.values():
                status = reader.ask(GetStatusQuery())
                ready = ready and bool(status.get("ready", False))
                total += int(status.get("document_count", 0))
            logger.info(f"Loaded {len(self.readers)} collection(s) with {total} documents")
            self.status.chroma_ready = ready
            self.status.documents_count = total
            return True
        except Exception:
            logger.exception("Error setting up vector database")
            self.status.chroma_ready = False
            return False

    def _reader_pairs(self, collections: List[str] | None = None) -> List[tuple]:
        """Resolve (collection_name, reader) pairs to search.

        Empty/None selects every known collection. Falls back to the legacy
        single-reader attribute when no multi-collection readers exist.
        """
        if self.readers:
            names = list(collections) if collections else list(self.readers.keys())
            return [(name, self.readers[name]) for name in names if name in self.readers]
        if self.vector_db:
            return [(None, self.vector_db)]
        return []

    def _run_query(self, reader: VectorDBCommandBus, query: str, top_k: int) -> List[dict]:
        results = reader.ask(HybridSearchQuery(query=query, top_k=top_k))
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

    def _collect_results(
        self, query: str, top_k: int | None = None, collections: List[str] | None = None
    ) -> List[dict]:
        top_k = top_k or self.max_results
        merged: List[dict] = []
        for collection, reader in self._reader_pairs(collections):
            for raw_doc in self._run_query(reader, query, top_k):
                doc = dict(raw_doc)
                if collection is not None:
                    doc["collection"] = collection
                merged.append(doc)
        return merged

    def _apply_filters(self, results: List[dict], request: SearchRequest) -> List[dict]:
        """Apply date/correspondent filters to raw search results."""
        if not (request.from_date or request.to_date or request.correspondent):
            return results

        filtered: List[dict] = []
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
        return filtered

    def semantic_search(self, query: str, top_k: int | None = None) -> List[dict]:
        """Semantic-only search across all collections via the CQRS read bus."""
        if not self.vector_db and not self.readers:
            raise VectorDBNotInitializedError("Vector database not initialized")

        top_k = top_k or self.max_results
        merged: List[dict] = []
        for collection, reader in self._reader_pairs():
            for raw_doc in self._run_query(reader, query, min(top_k, 100)):
                doc = dict(raw_doc)
                if collection is not None:
                    doc["collection"] = collection
                merged.append(doc)
        return merged

    def hybrid_search(self, query: str, top_k: int | None = None) -> List[dict]:
        """Hybrid search across all collections (CQRS read bus)."""
        if not self.vector_db and not self.readers:
            raise VectorDBNotInitializedError("Vector database not initialized")
        return self._collect_results(query, top_k)

    def rerank_results(self, query: str, results: List[dict], top_k: int | None = None) -> List[dict]:
        if not results:
            return []

        top_k = top_k or self.max_results

        try:
            if self.reranker is None:
                raise RerankerNotInitializedError("Reranker not initialized")
            reranked = self.reranker.rerank(query, results, top_k)
            return list(reranked) if reranked else []
        except Exception:
            logger.exception("Error reranking")
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
        except Exception:
            logger.exception("Error creating snippet")
            return content[:max_len] + "..." if content else ""

    def search(self, request: SearchRequest) -> List[SearchResult]:
        if not self.is_initialized and not self.initialize():
            raise VectorDBNotInitializedError("Vector database not initialized")

        results = self._collect_results(request.query, request.max_results, request.collections)
        results = self._apply_filters(results, request)
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
