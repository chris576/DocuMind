import json
import logging
import os
import pickle
from typing import Any, Dict, List, Optional

import chromadb
from nltk import word_tokenize
from rank_bm25 import BM25Okapi

from ..embeddings import EmbeddingProvider
from .base import BaseVectorDB, VectorDBDocument, VectorDBSearchResult
from .metrics import CHROMA_SPACES, resolve_keyword_method

logger = logging.getLogger("python_vectordb.vector_db.chroma")

# NLTK resources are ensured lazily (never on import).
_NLTK_RESOURCES = ("punkt", "punkt_tab", "stopwords")


class ChromaVectorDB(BaseVectorDB):
    def __init__(self, config: Dict[str, Any], embedding_provider: EmbeddingProvider):
        self.config = config
        self.url = config.get("url", "http://localhost:8000")
        self.collection_name = config.get("collection", "documents")
        self.embedding_provider = embedding_provider
        self.similarity_metric = config.get("similarity_metric", "cosine").lower()
        self.space = CHROMA_SPACES[self.similarity_metric]
        self.keyword_method = resolve_keyword_method("chroma", config.get("keyword_method", "auto"))
        self.keyword_weight = float(config.get("keyword_weight", 0.3))
        self.semantic_weight = float(config.get("semantic_weight", 0.7))
        self.keyword_index_file = config.get("keyword_index_file", "./data/bm25_index.pkl")
        self.client = None
        self.collection = None
        self.ready = False

        # Local BM25 keyword index (rank-bm25 + nltk), lazily rebuilt.
        self._keyword_documents: List[dict] = []
        self._tokenized_corpus: Optional[List[List[str]]] = None
        self._bm25: Any = None

    def initialize(self) -> bool:
        try:
            host = self.url.replace("http://", "").replace("https://", "")
            self.client = chromadb.HttpClient(host=host)

            existing_collections = self.client.list_collections()
            collection_exists = any(
                c.name == self.collection_name for c in existing_collections
            )

            if collection_exists:
                self.collection = self.client.get_collection(
                    name=self.collection_name,
                )
            else:
                self.collection = self.client.create_collection(
                    name=self.collection_name,
                    metadata={"hnsw:space": self.space},
                )

            self._load_local_index()
            self.ready = True
            logger.info(f"ChromaDB initialized: {self.collection_name}")
            return True
        except Exception as e:
            logger.error(f"ChromaDB initialization failed: {str(e)}")
            self.ready = False
            return False

    def add_documents(self, documents: List[VectorDBDocument]) -> None:
        if not self.ready or not self.collection:
            raise Exception("ChromaDB not initialized")

        batch_size = 100
        for i in range(0, len(documents), batch_size):
            batch = documents[i : i + batch_size]
            ids = [doc.id for doc in batch]
            texts = [f"{doc.title} {doc.content}" for doc in batch]
            metadatas = [
                {"title": doc.title, **self._flatten_metadata(doc.metadata)}
                for doc in batch
            ]
            embeddings = self.embedding_provider.encode_texts(texts)

            self.collection.upsert(
                ids=ids,
                embeddings=embeddings,
                documents=texts,
                metadatas=metadatas,
            )

        self._rebuild_local_index(documents)
        logger.info(f"Added {len(documents)} documents to ChromaDB")

    def search(self, query: str, top_k: int = 10) -> List[VectorDBSearchResult]:
        if not self.ready or not self.collection:
            raise Exception("ChromaDB not initialized")

        query_embedding = self.embedding_provider.encode_query(query)
        results = self.collection.query(
            query_embeddings=[query_embedding], n_results=top_k
        )
        if not results["ids"] or len(results["ids"]) == 0:
            return []

        documents = []
        for i, doc_id in enumerate(results["ids"][0]):
            distance = (
                float(results["distances"][0][i])
                if "distances" in results
                else 0.0
            )
            documents.append(
                VectorDBSearchResult(
                    id=str(doc_id),
                    title=results["metadatas"][0][i].get("title", ""),
                    content=results["documents"][0][i],
                    score=max(0.0, 1.0 - distance),
                    metadata=results["metadatas"][0][i],
                )
            )
        return documents

    def hybrid_search(self, query: str, top_k: int = 10) -> List[VectorDBSearchResult]:
        """Hybrid search: Chroma vector search + local BM25, fused in-adapter.

        Maintains the previous search_engine fusion (normalized keyword scores
        + semantic scores weighted by keyword/semantic weight) but keeps the
        implementation encapsulated within the Chroma adapter.
        """
        if not self.ready or not self.collection:
            raise Exception("ChromaDB not initialized")

        semantic = self.search(query, top_k * 2)

        keyword = []
        if self.keyword_method in ("local", "auto"):
            keyword = self._keyword_search(query, top_k * 2)

        if not semantic and not keyword:
            return []

        results_map: Dict[Any, Dict[str, Any]] = {}

        if keyword:
            max_keyword = max((r["score"] for r in keyword), default=1.0)
            for r in keyword:
                normalized = r["score"] / max_keyword if max_keyword > 0 else 0.0
                results_map[r["id"]] = {
                    **r,
                    "score": normalized * self.keyword_weight,
                }

        for sr in semantic:
            entry = results_map.setdefault(
                sr.id,
                {
                    "id": sr.id,
                    "title": sr.title,
                    "content": sr.content,
                    "metadata": sr.metadata,
                    "score": 0.0,
                },
            )
            entry["score"] += sr.score * self.semantic_weight

        combined = sorted(results_map.values(), key=lambda r: r["score"], reverse=True)
        return [
            VectorDBSearchResult(
                id=str(r["id"]),
                title=r.get("title", ""),
                content=r.get("content", ""),
                score=r["score"],
                metadata=r.get("metadata", {}),
            )
            for r in combined[:top_k]
        ]

    def delete_collection(self) -> None:
        if not self.client:
            raise Exception("ChromaDB not initialized")
        self.client.delete_collection(self.collection_name)
        self._keyword_documents = []
        self._tokenized_corpus = None
        self._bm25 = None
        self._delete_local_index()
        self.ready = False

    def delete_documents(self, document_ids: List[str]) -> None:
        if not self.ready or not self.collection:
            raise Exception("ChromaDB not initialized")
        if not document_ids:
            return
        self.collection.delete(ids=document_ids)
        self._keyword_documents = [
            d for d in self._keyword_documents if str(d.get("id")) not in set(document_ids)
        ]
        self._rebuild_local_index_from_state()
        logger.info(f"Deleted {len(document_ids)} documents from ChromaDB")

    # --- Local keyword index (BM25) ---------------------------------------

    def _ensure_nltk(self) -> None:
        """Lazily ensure NLTK tokenization resources (no import-time download)."""
        import nltk

        for resource in _NLTK_RESOURCES:
            try:
                nltk.data.find(self._nltk_lookup_path(resource))
            except LookupError:
                try:
                    nltk.download(resource, quiet=True)
                except Exception as e:  # pragma: no cover - network dependent
                    logger.warning(f"NLTK resource '{resource}' unavailable: {e}")

    @staticmethod
    def _nltk_lookup_path(resource: str) -> str:
        if resource == "punkt_tab":
            return "tokenizers/punkt_tab/english/"
        if resource == "punkt":
            return "tokenizers/punkt/"
        return f"corpora/{resource}/"

    def _tokenize(self, text: str) -> List[str]:
        tokens = word_tokenize(text.lower())
        return list(tokens)

    def _rebuild_local_index(self, documents: List[VectorDBDocument]) -> None:
        """Extend the local keyword corpus with the given documents and rebuild BM25."""
        for doc in documents:
            self._keyword_documents.append(
                {
                    "id": doc.id,
                    "title": doc.title,
                    "content": doc.content,
                    "correspondent": str(doc.metadata.get("correspondent", "")),
                    "created": str(doc.metadata.get("created", "")),
                }
            )
        self._rebuild_local_index_from_state()
        self._save_local_index()

    def _rebuild_local_index_from_state(self) -> None:
        self._ensure_nltk()
        corpus = [
            self._tokenize(
                f"{d.get('title', '')} {d.get('correspondent', '')} {d.get('content', '')}"
            )
            for d in self._keyword_documents
        ]
        if not corpus:
            self._tokenized_corpus = None
            self._bm25 = None
            return
        self._tokenized_corpus = corpus
        self._bm25 = BM25Okapi(corpus)

    def _keyword_search(self, query: str, top_k: int = 10) -> List[dict]:
        if self._bm25 is None or self._tokenized_corpus is None:
            return []
        query_tokens = self._tokenize(query)
        scores = self._bm25.get_scores(query_tokens)
        ranked = sorted(
            (s for s in enumerate(scores) if s[1] > 0),
            key=lambda s: s[1],
            reverse=True,
        )
        results = []
        for idx, score in ranked[:top_k]:
            doc = self._keyword_documents[idx]
            results.append(
                {
                    "id": doc["id"],
                    "title": doc["title"],
                    "content": doc["content"],
                    "correspondent": doc.get("correspondent", ""),
                    "date": doc.get("created", ""),
                    "score": float(score),
                }
            )
        return results

    def _save_local_index(self) -> None:
        try:
            directory = os.path.dirname(self.keyword_index_file)
            if directory:
                os.makedirs(directory, exist_ok=True)
            with open(self.keyword_index_file, "wb") as f:
                pickle.dump(
                    {
                        "documents": self._keyword_documents,
                        "tokenized_corpus": self._tokenized_corpus,
                    },
                    f,
                )
        except Exception as e:
            logger.error(f"Error saving Chroma keyword index: {str(e)}")

    def _load_local_index(self) -> bool:
        if not os.path.exists(self.keyword_index_file):
            return False
        try:
            with open(self.keyword_index_file, "rb") as f:
                data = pickle.load(f)
            self._keyword_documents = data.get("documents", [])
            self._tokenized_corpus = data.get("tokenized_corpus")
            if self._tokenized_corpus:
                self._bm25 = BM25Okapi(self._tokenized_corpus)
            logger.info(f"Loaded Chroma keyword index with {len(self._keyword_documents)} documents")
            return True
        except Exception as e:
            logger.error(f"Error loading Chroma keyword index: {str(e)}")
            return False

    def _delete_local_index(self) -> None:
        try:
            if os.path.exists(self.keyword_index_file):
                os.remove(self.keyword_index_file)
        except Exception as e:
            logger.error(f"Error deleting Chroma keyword index: {str(e)}")

    @staticmethod
    def _flatten_metadata(metadata: Dict[str, Any]) -> Dict[str, Any]:
        """Flatten non-scalar metadata values to JSON strings.

        Chroma requires flat, scalar metadata values (no nested dicts or
        lists). Values that are lists or dicts (e.g. document links, custom
        field objects) are serialized to JSON so they remain filterable.
        """
        flattened: Dict[str, Any] = {}
        for key, value in metadata.items():
            if isinstance(value, (list, dict)):
                flattened[key] = json.dumps(value, ensure_ascii=False)
            else:
                flattened[key] = value
        return flattened

    def get_status(self) -> Dict[str, Any]:
        if not self.ready or not self.collection:
            return {"ready": False, "document_count": 0}
        try:
            count = self.collection.count()
            return {
                "ready": True,
                "document_count": count,
                "keyword_documents_count": len(self._keyword_documents),
            }
        except Exception:
            return {"ready": False, "document_count": 0}
