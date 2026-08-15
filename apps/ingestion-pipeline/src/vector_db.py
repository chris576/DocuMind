import logging
from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any

import chromadb
from chromadb.utils import embedding_functions
from sentence_transformers import SentenceTransformer

logger = logging.getLogger("ingestion.vector_db")

class VectorDBDocument:
    def __init__(self, id: str, title: str, content: str, metadata: Optional[Dict[str, Any]] = None):
        self.id = id
        self.title = title
        self.content = content
        self.metadata = metadata or {}

class VectorDBSearchResult:
    def __init__(self, id: str, title: str, content: str, score: float, metadata: Optional[Dict[str, Any]] = None):
        self.id = id
        self.title = title
        self.content = content
        self.score = score
        self.metadata = metadata or {}

class BaseVectorDB(ABC):
    @abstractmethod
    def initialize(self) -> bool:
        pass

    @abstractmethod
    def add_documents(self, documents: List[VectorDBDocument]) -> None:
        pass

    @abstractmethod
    def search(self, query: str, top_k: int = 10) -> List[VectorDBSearchResult]:
        pass

    @abstractmethod
    def delete_collection(self) -> None:
        pass

    @abstractmethod
    def get_status(self) -> Dict[str, Any]:
        pass

class ChromaVectorDB(BaseVectorDB):
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.url = config.get("url", "http://localhost:8000")
        self.collection_name = config.get("collection", "documents")
        self.embedding_model = config.get("embedding_model", "paraphrase-multilingual-MiniLM-L12-v2")
        self.client = None
        self.collection = None
        self.embedding_function = None
        self.ready = False

    def initialize(self) -> bool:
        try:
            host = self.url.replace("http://", "").replace("https://", "")
            self.client = chromadb.HttpClient(host=host)
            self.embedding_function = embedding_functions.SentenceTransformerEmbeddingFunction(
                model_name=self.embedding_model
            )

            existing_collections = self.client.list_collections()
            collection_exists = any(c.name == self.collection_name for c in existing_collections)

            if collection_exists:
                self.collection = self.client.get_collection(
                    name=self.collection_name,
                    embedding_function=self.embedding_function
                )
            else:
                self.collection = self.client.create_collection(
                    name=self.collection_name,
                    embedding_function=self.embedding_function
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
            batch = documents[i:i+batch_size]
            ids = [doc.id for doc in batch]
            texts = [f"{doc.title} {doc.content}" for doc in batch]
            metadatas = [{"title": doc.title, **doc.metadata} for doc in batch]

            self.collection.upsert(ids=ids, documents=texts, metadatas=metadatas)

        logger.info(f"Added {len(documents)} documents to ChromaDB")

    def search(self, query: str, top_k: int = 10) -> List[VectorDBSearchResult]:
        if not self.ready or not self.collection:
            raise Exception("ChromaDB not initialized")

        results = self.collection.query(query_texts=[query], n_results=top_k)
        if not results["ids"] or len(results["ids"]) == 0:
            return []

        documents = []
        for i, doc_id in enumerate(results["ids"][0]):
            documents.append(VectorDBSearchResult(
                id=str(doc_id),
                title=results["metadatas"][0][i].get("title", ""),
                content=results["documents"][0][i],
                score=float(results["distances"][0][i]) if "distances" in results else 0.0,
                metadata=results["metadatas"][0][i]
            ))
        return documents

    def delete_collection(self) -> None:
        if not self.client:
            raise Exception("ChromaDB not initialized")
        self.client.delete_collection(self.collection_name)
        self.ready = False

    def get_status(self) -> Dict[str, Any]:
        if not self.ready or not self.collection:
            return {"ready": False, "document_count": 0}
        try:
            count = self.collection.count()
            return {"ready": True, "document_count": count}
        except Exception:
            return {"ready": False, "document_count": 0}

class VectorDBFactory:
    @staticmethod
    def create(config: Dict[str, Any]) -> BaseVectorDB:
        db_type = config.get("type", "chroma").lower()

        if db_type == "chroma":
            return ChromaVectorDB(config)
        else:
            raise ValueError(f"Unsupported vector database type: {db_type}")
