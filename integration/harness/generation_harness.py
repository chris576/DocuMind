"""Harness: startet die Generation-Pipeline mit Fake-LLM-Provider (Port 8003)."""

import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(ROOT, "apps", "generation-pipeline"))

import main as generation  # noqa: E402

from fakes import FakeLLMProvider  # noqa: E402


class _FakeLLMFactory:
    @staticmethod
    def create(provider, config):
        return FakeLLMProvider()


# Blatt-Dependency ersetzen: der Lifespan nutzt die Fake-Factory statt einer
# echten LLM-Verbindung (OpenAI/Ollama/Anthropic/Custom).
generation.LLMProviderFactory = _FakeLLMFactory

import uvicorn  # noqa: E402

if __name__ == "__main__":
    uvicorn.run(generation.app, host="127.0.0.1", port=int(os.getenv("PORT", "8003")))
