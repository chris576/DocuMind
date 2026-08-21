import json
import logging
from typing import Any, Dict, List

import chromadb

from ..embeddings import EmbeddingProvider
from .base import BaseVectorDB, VectorDBDocument, VectorDBSearchResult

logger = logging.getLogger("python_vectordb.vector_db.chroma")

class ChromaVectorDB(BaseVectorDB):
    def __init__(self, config: Dict[str, Any], embedding_provider: EmbeddingProvider):
        self.config = config
        self.url = config.get("url", "http://localhost:8000")
        self.collection_name = config.get("collection", "documents")
        self.embedding_provider = embedding_provider
        self.client = None
        self.collection = None
        self.ready = False

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
                    metadata={"hnsw:space": "cosine"},
                )

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

    def delete_collection(self) -> None:
        if not self.client:
            raise Exception("ChromaDB not initialized")
        self.client.delete_collection(self.collection_name)
        self.ready = False

    def delete_documents(self, document_ids: List[str]) -> None:
        if not self.ready or not self.collection:
            raise Exception("ChromaDB not initialized")
        if not document_ids:
            return
        self.collection.delete(ids=document_ids)
        logger.info(f"Deleted {len(document_ids)} documents from ChromaDB")

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
            return {"ready": True, "document_count": count}
        except Exception:
            return {"ready": False, "document_count": 0}
