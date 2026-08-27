"""Fake-Implementierungen für die Integrationstests.

Ersetzen DB/LLM/DMS an den Blatträndern der Pipelines. Die Pipelines selbst
laufen als echte FastAPI-Apps — nur die teuren/ externen Abhängigkeiten
(Vektor-DB, LLM, DMS) werden hierdurch ersetzt.
"""

from __future__ import annotations

from typing import Any, Dict, List


class FakeSearchEngine:
    """Ersetzt die SearchEngine des Retrieval-Pipelines.

    Liefert deterministische Treffer, damit der Backend→Retrieval-Vertrag
    (Feldnamen, Status-Shape) verifiziert werden kann.
    """

    is_initialized = True

    def __init__(self) -> None:
        self._results: List[Dict[str, Any]] = [
            {
                "title": "Rechnung 2024-001",
                "correspondent": "ACME GmbH",
                "date": "2024-01-15",
                "score": 0.95,
                "snippet": "Zahlungsziel 14 Tage netto.",
                "doc_id": 1,
                "content": "Rechnung über 120,00 EUR.",
            },
            {
                "title": "Vertrag Muster",
                "correspondent": "Beta AG",
                "date": "2024-02-01",
                "score": 0.72,
                "snippet": "Laufzeit 12 Monate.",
                "doc_id": 2,
                "content": "Rahmenvertrag.",
            },
        ]

    # Vom Lifespan aufgerufen (Original sucht eine echte DB-Verbindung).
    def initialize(self) -> None:
        return None

    def setup_vector_db(self) -> None:
        return None

    def search(self, request: Any) -> List[Any]:
        # Lazy-Import: der Harness hat das Pipeline-Verzeichnis bereits auf
        # sys.path gesetzt. Rückgabe als echte SearchResult-Objekte, weil der
        # /context-Endpoint auf Attribute (result.title, ...) zugreift.
        from src.models import SearchResult

        return [SearchResult(**r) for r in self._results]

    def get_status(self) -> Dict[str, Any]:
        return {
            "initialized": True,
            "chroma_ready": True,
            "bm25_ready": True,
            "documents_count": len(self._results),
            "bm25_documents_count": len(self._results),
            "last_updated": None,
        }


class FakeLLMProvider:
    """Ersetzt den LLM-Provider des Generation-Pipelines."""

    provider_name = "fake"
    model = "fake-model"

    async def generate(self, request: Any) -> Any:
        # Import verzögert, damit fakes.py ohne Pipeline-Kontext importierbar bleibt.
        from python_llm import GenerateResponse

        return GenerateResponse(
            answer="Das ist die Antwort basierend auf dem Dokument-Kontext.",
            prompt_tokens=10,
            completion_tokens=5,
            total_tokens=15,
            model=self.model,
            provider=self.provider_name,
        )

    async def generate_stream(self, request: Any):
        for chunk in ("Das ", "ist ", "die ", "Antwort."):
            yield chunk

    async def chat(self, messages: List[Any], stream: bool = False) -> str:
        return "Das ist die Chat-Antwort."


class FakeIngestionService:
    """Ersetzt den IngestionService des Ingestion-Pipelines."""

    is_initialized = True
    documents: List[Any] = []

    def get_status(self) -> Dict[str, Any]:
        return {
            "service": "ingestion-pipeline",
            "initialized": True,
            "documents_count": 2,
        }

    def check_for_updates(self) -> tuple[bool, str]:
        return (True, "2 neue Dokumente gefunden")


class FakeIngestionTask:
    """Ersetzt den IngestionTask des Ingestion-Pipelines."""

    running = False

    def run(self, force_update: bool = False, check_new: bool = True) -> Dict[str, Any]:
        return {"status": "completed", "processed": 2, "indexed": 2}
