import logging
from typing import Any, Dict, List

import psycopg2
import psycopg2.extras

from ..embeddings import EmbeddingProvider
from .base import BaseVectorDB, VectorDBDocument, VectorDBSearchResult
from .metrics import PGVECTOR_OPERATORS, normalize_pgvector_score, resolve_keyword_method

logger = logging.getLogger("python_vectordb.vector_db.pgvector")


class PgVectorVectorDB(BaseVectorDB):
    def __init__(self, config: Dict[str, Any], embedding_provider: EmbeddingProvider):
        self.config = config
        self.url = config.get("url")
        self.table_name = config.get("collection", "documents")
        self.embedding_provider = embedding_provider
        self.embedding_dimension = config.get("embedding_dimension", 384)
        self.similarity_metric = config.get("similarity_metric", "cosine").lower()
        self.operator = PGVECTOR_OPERATORS[self.similarity_metric]
        self.keyword_method = resolve_keyword_method("pgvector", config.get("keyword_method", "auto"))
        self.keyword_weight = float(config.get("keyword_weight", 0.3))
        self.semantic_weight = float(config.get("semantic_weight", 0.7))
        self.fts_language = config.get("fts_language", "german")
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
                        metadata JSONB DEFAULT '{{}}',
                        fts tsvector GENERATED ALWAYS AS (
                            to_tsvector('{self.fts_language}', coalesce(title, '') || ' ' || coalesce(content, ''))
                        ) STORED
                    )
                    """
                )
                cursor.execute(
                    f"CREATE INDEX IF NOT EXISTS {self.table_name}_fts_idx ON {self.table_name} USING GIN (fts)"
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
                       1 - (embedding {self.operator} %s::vector) AS score
                FROM {self.table_name}
                ORDER BY embedding {self.operator} %s::vector
                LIMIT %s
                """,
                (query_vector, query_vector, top_k),
            )
            rows = cursor.fetchall()

        documents = []
        for row in rows:
            doc_id, title, content, metadata, raw_score = row
            score = (
                normalize_pgvector_score(self.similarity_metric, float(raw_score))
                if raw_score is not None
                else 0.0
            )
            documents.append(
                VectorDBSearchResult(
                    id=str(doc_id),
                    title=title,
                    content=content,
                    score=score,
                    metadata=metadata or {},
                )
            )
        return documents

    def hybrid_search(self, query: str, top_k: int = 10) -> List[VectorDBSearchResult]:
        """Hybrid search: FTS (ts_rank) + vector distance, fused in SQL.

        Combines the vector similarity score with Postgres full-text ranking
        weighted by keyword/semantic weights. Falls back to semantic-only when
        the FTS channel yields no matches or keyword retrieval is disabled.
        """
        if not self.ready or not self.connection:
            raise Exception("PGVector not initialized")

        query_vector = str(self.embedding_provider.encode_query(query))
        vector_expr = f"1 - (embedding {self.operator} %s::vector)"

        if self.keyword_method in ("fts", "auto"):
            rank = (
                f"ts_rank(fts, plainto_tsquery('{self.fts_language}', %s))"
            )
            fts_match = f"fts @@ plainto_tsquery('{self.fts_language}', %s)"
            with self.connection.cursor() as cursor:
                cursor.execute(
                    f"""
                    SELECT id, title, content, metadata,
                           {vector_expr} AS s_score,
                           {rank} AS k_score,
                           ({vector_expr}) * %s + {rank} * %s AS combined
                    FROM {self.table_name}
                    WHERE {fts_match}
                    ORDER BY combined DESC
                    LIMIT %s
                    """,
                    (
                        query_vector,
                        query,
                        query_vector,
                        self.semantic_weight,
                        self.keyword_weight,
                        query,
                        top_k,
                    ),
                )
                rows = cursor.fetchall()
        else:
            rows = self._semantic_rows(query_vector, top_k)

        documents = []
        for row in rows:
            doc_id, title, content, metadata, s_score, _, _ = row
            documents.append(
                VectorDBSearchResult(
                    id=str(doc_id),
                    title=title,
                    content=content,
                    score=float(s_score) if s_score is not None else 0.0,
                    metadata=metadata or {},
                )
            )
        return documents

    def _semantic_rows(self, query_vector: str, top_k: int):
        """Fetch semantic-only rows (used when keyword channel is disabled)."""
        with self.connection.cursor() as cursor:
            cursor.execute(
                f"""
                SELECT id, title, content, metadata,
                       1 - (embedding {self.operator} %s::vector) AS s_score,
                       0.0 AS k_score,
                       1 - (embedding {self.operator} %s::vector) AS combined
                FROM {self.table_name}
                ORDER BY embedding {self.operator} %s::vector
                LIMIT %s
                """,
                (query_vector, query_vector, query_vector, top_k),
            )
            return cursor.fetchall()

    def delete_collection(self) -> None:
        if not self.connection:
            raise Exception("PGVector not initialized")
        with self.connection.cursor() as cursor:
            cursor.execute(f"DROP TABLE IF EXISTS {self.table_name}")
        self.connection.commit()
        self.ready = False

    def delete_documents(self, document_ids: List[str]) -> None:
        if not self.ready or not self.connection:
            raise Exception("PGVector not initialized")
        if not document_ids:
            return
        with self.connection.cursor() as cursor:
            cursor.execute(
                f"DELETE FROM {self.table_name} WHERE id = ANY(%s)",
                (document_ids,),
            )
        self.connection.commit()
        logger.info(f"Deleted {len(document_ids)} documents from PGVector")

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
