"""Harness: startet die Retrieval-Pipeline mit Fake-SearchEngine (Port 8002)."""

import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(ROOT, "apps", "retrieval-pipeline"))

import main as retrieval  # noqa: E402

from fakes import FakeSearchEngine  # noqa: E402

# Blatt-Dependency ersetzen: der Lifespan baut statt einer echten DB-Verbindung
# eine deterministische Fake-Engine (initialize/setup_vector_db sind No-Ops).
retrieval.SearchEngine = lambda config: FakeSearchEngine()

import uvicorn  # noqa: E402

if __name__ == "__main__":
    uvicorn.run(retrieval.app, host="127.0.0.1", port=int(os.getenv("PORT", "8002")))
