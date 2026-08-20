import logging
from typing import Any, Dict, List

import psycopg2
import psycopg2.extras

from ..embeddings import EmbeddingProvider
from .base import BaseVectorDB, VectorDBDocument, VectorDBSearchResult

logger = logging.getLogger("python_vectordb.vector_db.pgvector")


class PgVectorVectorDB(BaseVectorDB):
    def __init__(self, config: Dict[str, Any], embedding_provider: EmbeddingProvider):
        self.config = config
        self.url = config.get("url")
        self.table_name = config.get("collection", "documents")
        self.embedding_provider = embedding_provider
        self.embedding_dimension = config.get("embedding_dimension", 384)
        self.connection = None
        self.ready = False

    def initialize(self) -> bool:
        try:
            if not self.url:
                raise ValueError("PGVector connection URL is required")
            self.connection = psycopg2.connect(self.url)

            with self.connection.cursor() as cursor:
                cursor.execute("CREATE EXTENSION IF NOT EXISTS vector")
                cursor.execute(
                    f"""
                    CREATE TABLE IF NOT EXISTS {self.table_name} (
                        id TEXT PRIMARY KEY,
                        title TEXT NOT NULL,
                        content TEXT NOT NULL,
                        embedding VECTOR({self.embedding_dimension}),
                        metadata JSONB DEFAULT '{{}}'
                    )
                    """
                )
            self.connection.commit()

            self.ready = True
            logger.info(f"PGVector initialized: {self.table_name}")
            return True
        except Exception as e:
            logger.error(f"PGVector initialization failed: {str(e)}")
            self.ready = False
            return False

    def add_documents(self, documents: List[VectorDBDocument]) -> None:
        if not self.ready or not self.connection:
            raise Exception("PGVector not initialized")

        batch_size = 100
        for i in range(0, len(documents), batch_size):
            batch = documents[i : i + batch_size]
            texts = [f"{doc.title} {doc.content}" for doc in batch]
            vectors = self.embedding_provider.encode_texts(texts)

            with self.connection.cursor() as cursor:
                for doc, vector in zip(batch, vectors):
                    cursor.execute(
                        f"""
                        INSERT INTO {self.table_name} (id, title, content, embedding, metadata)
                        VALUES (%s, %s, %s, %s::vector, %s)
                        ON CONFLICT (id) DO UPDATE SET
                            title = EXCLUDED.title,
                            content = EXCLUDED.content,
                            embedding = EXCLUDED.embedding,
                            metadata = EXCLUDED.metadata
                        """,
                        (
                            doc.id,
                            doc.title,
                            doc.content,
                            str(vector.tolist()),
                            psycopg2.extras.Json(doc.metadata),
                        ),
                    )
            self.connection.commit()

        logger.info(f"Added {len(documents)} documents to PGVector")

    def search(self, query: str, top_k: int = 10) -> List[VectorDBSearchResult]:
        if not self.ready or not self.connection:
            raise Exception("PGVector not initialized")

        query_vector = str(self.embedding_provider.encode_query(query))
        with self.connection.cursor() as cursor:
            cursor.execute(
                f"""
                SELECT id, title, content, metadata,
                       1 - (embedding <=> %s::vector) AS score
                FROM {self.table_name}
                ORDER BY embedding <=> %s::vector
                LIMIT %s
                """,
                (query_vector, query_vector, top_k),
            )
            rows = cursor.fetchall()

        documents = []
        for row in rows:
            doc_id, title, content, metadata, score = row
            documents.append(
                VectorDBSearchResult(
                    id=str(doc_id),
                    title=title,
                    content=content,
                    score=float(score) if score is not None else 0.0,
                    metadata=metadata or {},
                )
            )
        return documents

    def delete_collection(self) -> None:
        if not self.connection:
            raise Exception("PGVector not initialized")
        with self.connection.cursor() as cursor:
            cursor.execute(f"DROP TABLE IF EXISTS {self.table_name}")
        self.connection.commit()
        self.ready = False

    def get_status(self) -> Dict[str, Any]:
        if not self.ready or not self.connection:
            return {"ready": False, "document_count": 0}
        try:
            with self.connection.cursor() as cursor:
                cursor.execute(f"SELECT COUNT(*) FROM {self.table_name}")
                count = cursor.fetchone()[0]
            return {"ready": True, "document_count": int(count)}
        except Exception:
            return {"ready": False, "document_count": 0}