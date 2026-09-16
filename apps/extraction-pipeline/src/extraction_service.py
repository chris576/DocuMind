import json
import logging
import re
from datetime import datetime, timezone
from typing import Any, Dict, List

import psycopg2
import psycopg2.extras
from python_llm import BaseLLMProvider, GenerateRequest

logger = logging.getLogger("extraction.service")

FACT_KEYS_TABLE = "fact_keys"
ALLOWED_TYPES = ("string", "number", "date", "boolean", "currency")


def normalize_key(raw: Any) -> str:
    """Normalize a fact key to snake_case; an empty result is discarded by the caller."""
    key = str(raw or "").strip().lower()
    key = re.sub(r"[\s\-./]+", "_", key)
    key = re.sub(r"[^a-z0-9_]", "", key)
    key = re.sub(r"_+", "_", key).strip("_")
    return key


def coerce_value(value: Any, fact_type: str) -> Any:
    """Coerce a raw LLM value to the declared fact type."""
    if fact_type in ("number", "currency"):
        if isinstance(value, bool):
            return float(value)
        if isinstance(value, (int, float)):
            return value
        try:
            return float(str(value).replace(",", "."))
        except (TypeError, ValueError):
            return value
    if fact_type == "boolean":
        if isinstance(value, bool):
            return value
        return str(value).lower() in ("true", "1", "yes")
    return value


class ExtractionService:
    """Extracts structured facts from documents via an LLM.

    Reads pending rows from the ``document_facts`` table (empty ``extracted``),
    lets the LLM produce a fact envelope, normalizes/validates it and writes
    back ``extracted`` + ``extracted_at``. New keys are registered in the
    append-only ``fact_keys`` catalog per document type.
    """

    def __init__(
        self,
        llm: BaseLLMProvider,
        db_url: str,
        table_name: str = "document_facts",
        batch_size: int = 10,
    ):
        self.llm = llm
        self.db_url = db_url
        self.table_name = table_name
        self.batch_size = batch_size
        self.connection = None
        self.ready = False

    def initialize(self) -> bool:
        try:
            if not self.db_url:
                raise ValueError("PGVector connection URL is required")
            self.connection = psycopg2.connect(self.db_url)
            with self.connection.cursor() as cursor:
                cursor.execute(
                    f"""
                    CREATE TABLE IF NOT EXISTS {FACT_KEYS_TABLE} (
                        document_type TEXT NOT NULL,
                        key TEXT NOT NULL,
                        first_seen TIMESTAMPTZ NOT NULL DEFAULT now(),
                        PRIMARY KEY (document_type, key)
                    )
                    """
                )
            self.connection.commit()
            self.ready = True
            return True
        except Exception:
            logger.exception("Extraction service initialization failed")
            self.ready = False
            return False

    def find_pending(self, limit: int | None = None) -> List[Dict[str, Any]]:
        if not self.ready or not self.connection:
            raise Exception("ExtractionService not initialized")
        with self.connection.cursor() as cursor:
            cursor.execute(
                f"""
                SELECT id, title, content, document_type, raw_json
                FROM {self.table_name}
                WHERE extracted = '{{}}'::jsonb OR extracted IS NULL
                ORDER BY id
                LIMIT %s
                """,
                (limit or self.batch_size,),
            )
            rows = cursor.fetchall()
        return [
            {
                "id": str(row[0]),
                "title": row[1],
                "content": row[2] or "",
                "document_type": row[3] or "",
                "raw_json": row[4] or {},
            }
            for row in rows
        ]

    def known_keys(self, document_type: str) -> List[str]:
        if not document_type:
            return []
        with self.connection.cursor() as cursor:
            cursor.execute(
                f"SELECT key FROM {FACT_KEYS_TABLE} WHERE document_type = %s ORDER BY first_seen",
                (document_type,),
            )
            return [row[0] for row in cursor.fetchall()]

    def build_prompt(self, doc: Dict[str, Any], known_keys: List[str]) -> str:
        doc_type = doc.get("document_type") or "unbekannt"
        known = ", ".join(known_keys) if known_keys else "(keine)"
        content = (doc.get("content") or "")[:8000]
        return (
            "Extrahiere strukturierte Fakten aus dem Dokument. "
            "Antworte NUR mit einem JSON-Array, ohne Kommentare.\n"
            "Jedes Element hat die Form: "
            '{"key": "<snake_case>", "value": <skalar>, "type": "string|number|date|boolean|currency", '
            '"confidence": 0.0-1.0, "source": "<kurzes Zitat>"}.\n'
            f"Dokumenttyp: {doc_type}\n"
            f"Bekannte Schlüssel (wiederverwenden, wenn passend): {known}\n\n"
            f"Dokumenttext:\n{content}"
        )

    def parse_envelope(self, answer: str) -> Dict[str, Any]:
        """Parse and validate the LLM envelope into ``{key: {value, type, confidence, source}}``."""
        text = (answer or "").strip()
        fence = re.search(r"```(?:json)?\s*(.*?)\s*```", text, re.DOTALL)
        if fence:
            text = fence.group(1).strip()
        try:
            payload = json.loads(text)
        except json.JSONDecodeError:
            logger.warning("Could not parse LLM envelope as JSON")
            return {}

        if isinstance(payload, dict):
            payload = payload.get("facts", payload)
        if not isinstance(payload, list):
            return {}

        facts: Dict[str, Any] = {}
        for item in payload:
            if not isinstance(item, dict):
                continue
            key = normalize_key(item.get("key"))
            if not key:
                continue
            fact_type = str(item.get("type") or "string").lower()
            if fact_type not in ALLOWED_TYPES:
                fact_type = "string"
            confidence = item.get("confidence")
            try:
                confidence = float(confidence) if confidence is not None else 1.0
            except (TypeError, ValueError):
                confidence = 1.0
            facts[key] = {
                "value": coerce_value(item.get("value"), fact_type),
                "type": fact_type,
                "confidence": max(0.0, min(1.0, confidence)),
                "source": str(item.get("source") or ""),
            }
        return facts

    async def extract_one(self, doc: Dict[str, Any]) -> Dict[str, Any]:
        known = self.known_keys(doc.get("document_type") or "")
        prompt = self.build_prompt(doc, known)
        response = await self.llm.generate(
            GenerateRequest(question=prompt, max_tokens=2000, temperature=0.0)
        )
        return self.parse_envelope(response.answer)

    def save(self, doc_id: str, extracted: Dict[str, Any], extracted_at: str) -> None:
        with self.connection.cursor() as cursor:
            cursor.execute(
                f"UPDATE {self.table_name} SET extracted = %s, extracted_at = %s WHERE id = %s",
                (psycopg2.extras.Json(extracted), extracted_at, str(doc_id)),
            )
        self.connection.commit()

    def register_keys(self, document_type: str, keys: List[str]) -> None:
        if not keys:
            return
        with self.connection.cursor() as cursor:
            for key in keys:
                cursor.execute(
                    f"INSERT INTO {FACT_KEYS_TABLE} (document_type, key) VALUES (%s, %s) "
                    "ON CONFLICT DO NOTHING",
                    (document_type, key),
                )
        self.connection.commit()

    async def run(self, limit: int | None = None) -> Dict[str, Any]:
        if not self.ready or not self.connection:
            raise Exception("ExtractionService not initialized")

        pending = self.find_pending(limit or self.batch_size)
        processed = 0
        failed = 0
        for doc in pending:
            try:
                facts = await self.extract_one(doc)
                if not facts:
                    continue
                self.save(doc["id"], facts, datetime.now(timezone.utc).isoformat())
                self.register_keys(doc.get("document_type") or "", list(facts.keys()))
                processed += 1
            except Exception:
                logger.exception(f"Extraction failed for document {doc.get('id')}")
                failed += 1
        return {"processed": processed, "failed": failed, "pending_total": len(pending)}

    def get_status(self) -> Dict[str, Any]:
        return {
            "service": "extraction-pipeline",
            "ready": self.ready,
            "table": self.table_name,
        }
