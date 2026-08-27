"""Harness: startet die Ingestion-Pipeline mit Fake-Service/Task (Port 8001)."""

import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(ROOT, "apps", "ingestion-pipeline"))

import main as ingestion  # noqa: E402

from fakes import FakeIngestionService, FakeIngestionTask  # noqa: E402

# Blatt-Dependencies ersetzen: keine echte DMS-/Vektor-DB-Verbindung.
ingestion.VectorDBFactory.create_writer = lambda config: object()
ingestion.DocumentProviderFactory.create = lambda config: object()
ingestion.IngestionService = lambda document_provider, vector_db: FakeIngestionService()
ingestion.IngestionTask = lambda service: FakeIngestionTask()

import uvicorn  # noqa: E402

if __name__ == "__main__":
    uvicorn.run(ingestion.app, host="127.0.0.1", port=int(os.getenv("PORT", "8001")))
