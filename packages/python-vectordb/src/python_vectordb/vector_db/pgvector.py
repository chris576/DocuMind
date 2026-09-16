import logging
from typing import Any, Dict, List

import psycopg2
import psycopg2.extras

from ..embeddings import EmbeddingProvider
from .base import BaseVectorDB, VectorDBDocument, VectorDBSearchResult
from .metrics import PGVECTOR_OPERATORS, normalize_pgvector_score, resolve_keyword_method
from .queries import FactsQuery

logger = logging.getLogger("python_vectordb.vector_db.pgvector")

# Single fact table that stores embeddings AND denormalized facts side by side.
DEFAULT_TABLE = "document_facts"
# Pre-facts schema: a per-collection table holding `metadata` JSONB + embedding.
LEGACY_TABLE = "documents"

_AGGREGATES = {"sum": "SUM", "avg": "AVG", "min": "MIN", "max": "MAX", "count": "COUNT"}


class PgVectorVectorDB(BaseVectorDB):
    def __init__(self, config: Dict[str, Any], embedding_provider: EmbeddingProvider):
        self.config = config
        self.url = config.get("url")
        self.table_name = config.get("table_name", DEFAULT_TABLE)
        # "collection" now identifies the namespace a writer/reader is bound to.
        self.namespace = config.get("namespace") or config.get("collection") or "paperless"
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
                        namespace TEXT NOT NULL DEFAULT 'paperless',
                        title TEXT NOT NULL,
                        content TEXT NOT NULL,
                        document_type TEXT NOT NULL DEFAULT '',
                        embedding VECTOR({self.embedding_dimension}),
                        raw_json JSONB DEFAULT '{{}}',
                        extracted JSONB DEFAULT '{{}}',
                        checksum TEXT DEFAULT '',
                        extracted_at TIMESTAMPTZ,
                        fts tsvector GENERATED ALWAYS AS (
                            to_tsvector('{self.fts_language}', coalesce(title, '') || ' ' || coalesce(content, ''))
                        ) STORED
                    )
                    """
                )
                cursor.execute(
                    f"CREATE INDEX IF NOT EXISTS {self.table_name}_fts_idx ON {self.table_name} USING GIN (fts)"
                )
                cursor.execute(
                    f"CREATE INDEX IF NOT EXISTS {self.table_name}_raw_json_idx ON {self.table_name} USING GIN (raw_json)"
                )
                cursor.execute(
                    f"CREATE INDEX IF NOT EXISTS {self.table_name}_extracted_idx ON {self.table_name} USING GIN (extracted)"
                )
                cursor.execute(
                    f"CREATE INDEX IF NOT EXISTS {self.table_name}_namespace_type_idx "
                    f"ON {self.table_name} (namespace, document_type)"
                )
                cursor.execute(
                    """
                    CREATE TABLE IF NOT EXISTS fact_keys (
                        document_type TEXT NOT NULL,
                        key TEXT NOT NULL,
                        first_seen TIMESTAMPTZ NOT NULL DEFAULT now(),
                        PRIMARY KEY (document_type, key)
                    )
                    """
                )
                self._migrate_legacy(cursor)
            self.connection.commit()

            self.ready = True
            logger.info(f"PGVector initialized: {self.table_name} (namespace={self.namespace})")
            return True
        except Exception as e:
            logger.error(f"PGVector initialization failed: {str(e)}")
            self.ready = False
            return False

    def _migrate_legacy(self, cursor) -> None:
        """Copy rows from the legacy per-collection table into document_facts.

        The pre-facts schema stored vector metadata in a `documents` table with
        a `metadata` JSONB column and no namespace/raw_json/extracted columns.
        The copy is idempotent (ON CONFLICT DO NOTHING) and the legacy table is
        dropped best-effort afterwards. Non-default legacy table names are not
        migrated; a re-ingestion repopulates them with full metadata anyway.
        """
        try:
            cursor.execute("SAVEPOINT legacy_migration")
            cursor.execute("SELECT to_regclass(%s)", (LEGACY_TABLE,))
            if cursor.fetchone()[0] is None:
                cursor.execute("RELEASE SAVEPOINT legacy_migration")
                return
            cursor.execute(
                f"""
                INSERT INTO {self.table_name}
                    (id, namespace, title, content, document_type, embedding, raw_json, checksum)
                SELECT
                    id, %s, title, content,
                    COALESCE(metadata->>'document_type', ''),
                    embedding, metadata, COALESCE(metadata->>'hash', '')
                FROM {LEGACY_TABLE}
                ON CONFLICT (id) DO NOTHING
                """,
                (self.namespace,),
            )
            cursor.execute(f"DROP TABLE IF EXISTS {LEGACY_TABLE}")
            cursor.execute("RELEASE SAVEPOINT legacy_migration")
            logger.info(f"Migrated legacy '{LEGACY_TABLE}' rows into {self.table_name}")
        except Exception:
            cursor.execute("ROLLBACK TO SAVEPOINT legacy_migration")
            logger.warning("Legacy migration skipped", exc_info=True)

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
                    metadata = doc.metadata or {}
                    document_type = str(metadata.get("document_type", "") or "")
                    checksum = str(metadata.get("hash") or metadata.get("checksum") or "")
                    cursor.execute(
                        f"""
                        INSERT INTO {self.table_name}
                            (id, namespace, title, content, document_type, embedding, raw_json, checksum)
                        VALUES (%s, %s, %s, %s, %s, %s::vector, %s, %s)
                        ON CONFLICT (id) DO UPDATE SET
                            namespace = EXCLUDED.namespace,
                            title = EXCLUDED.title,
                            content = EXCLUDED.content,
                            document_type = EXCLUDED.document_type,
                            embedding = EXCLUDED.embedding,
                            raw_json = EXCLUDED.raw_json,
                            checksum = EXCLUDED.checksum,
                            extracted = CASE
                                WHEN {self.table_name}.checksum = EXCLUDED.checksum
                                THEN {self.table_name}.extracted ELSE '{{}}'::jsonb END,
                            extracted_at = CASE
                                WHEN {self.table_name}.checksum = EXCLUDED.checksum
                                THEN {self.table_name}.extracted_at ELSE NULL END
                        """,
                        (
                            doc.id,
                            self.namespace,
                            doc.title,
                            doc.content,
                            document_type,
                            str(vector.tolist()),
                            psycopg2.extras.Json(metadata),
                            checksum,
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
                SELECT id, title, content, raw_json,
                       1 - (embedding {self.operator} %s::vector) AS score
                FROM {self.table_name}
                WHERE namespace = %s
                ORDER BY embedding {self.operator} %s::vector
                LIMIT %s
                """,
                (query_vector, self.namespace, query_vector, top_k),
            )
            rows = cursor.fetchall()

        documents = []
        for row in rows:
            doc_id, title, content, raw_json, raw_score = row
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
                    metadata=raw_json or {},
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
                    SELECT id, title, content, raw_json,
                           {vector_expr} AS s_score,
                           {rank} AS k_score,
                           ({vector_expr}) * %s + {rank} * %s AS combined
                    FROM {self.table_name}
                    WHERE {fts_match} AND namespace = %s
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
                        self.namespace,
                        top_k,
                    ),
                )
                rows = cursor.fetchall()
        else:
            rows = self._semantic_rows(query_vector, top_k)

        documents = []
        for row in rows:
            doc_id, title, content, raw_json, s_score, _, _ = row
            documents.append(
                VectorDBSearchResult(
                    id=str(doc_id),
                    title=title,
                    content=content,
                    score=float(s_score) if s_score is not None else 0.0,
                    metadata=raw_json or {},
                )
            )
        return documents

    def _semantic_rows(self, query_vector: str, top_k: int):
        """Fetch semantic-only rows (used when keyword channel is disabled)."""
        with self.connection.cursor() as cursor:
            cursor.execute(
                f"""
                SELECT id, title, content, raw_json,
                       1 - (embedding {self.operator} %s::vector) AS s_score,
                       0.0 AS k_score,
                       1 - (embedding {self.operator} %s::vector) AS combined
                FROM {self.table_name}
                WHERE namespace = %s
                ORDER BY embedding {self.operator} %s::vector
                LIMIT %s
                """,
                (query_vector, query_vector, self.namespace, query_vector, top_k),
            )
            return cursor.fetchall()

    def query_facts(self, query: FactsQuery) -> Dict[str, Any]:
        """Query denormalized facts with optional filtering and aggregation."""
        if not self.ready or not self.connection:
            raise Exception("PGVector not initialized")

        namespace = query.namespace or self.namespace
        conditions = ["namespace = %s"]
        params: List[Any] = [namespace]

        if query.document_type:
            conditions.append("document_type = %s")
            params.append(query.document_type)
        if query.key:
            conditions.append("extracted ? %s")
            params.append(query.key)
            if query.value is not None:
                conditions.append("extracted->>%s = %s")
                params.append(query.key)
                params.append(str(query.value))
        if query.from_date:
            conditions.append("COALESCE(raw_json->>'created', '') >= %s")
            params.append(query.from_date)
        if query.to_date:
            conditions.append("COALESCE(raw_json->>'created', '') <= %s")
            params.append(query.to_date)

        where = " AND ".join(conditions)

        with self.connection.cursor() as cursor:
            if query.aggregate and query.key:
                agg_func = _AGGREGATES.get(query.aggregate.lower())
                if agg_func is None:
                    raise ValueError(
                        f"Unsupported aggregation: {query.aggregate}. "
                        f"Supported: {', '.join(sorted(_AGGREGATES))}"
                    )
                if agg_func == "COUNT":
                    cursor.execute(
                        f"SELECT COUNT(*) FROM {self.table_name} WHERE {where}",
                        params,
                    )
                else:
                    cursor.execute(
                        f"SELECT {agg_func}((extracted->>%s)::numeric) "
                        f"FROM {self.table_name} WHERE {where}",
                        [query.key, *params],
                    )
                return {
                    "aggregate": query.aggregate.lower(),
                    "key": query.key,
                    "value": cursor.fetchone()[0],
                }

            cursor.execute(
                f"""
                SELECT id, title, document_type, raw_json, extracted
                FROM {self.table_name}
                WHERE {where}
                LIMIT %s
                """,
                [*params, query.limit],
            )
            rows = cursor.fetchall()

        items = [
            {
                "id": str(row[0]),
                "title": row[1],
                "document_type": row[2],
                "raw_json": row[3] or {},
                "extracted": row[4] or {},
            }
            for row in rows
        ]
        return {"items": items, "count": len(items)}

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
