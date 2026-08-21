"""Unit tests for the generation pipeline FastAPI endpoints (mocked provider)."""
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi.testclient import TestClient

import main as generation

pytestmark = pytest.mark.anyio


@pytest.fixture
def client(monkeypatch):
    provider = MagicMock()
    provider.provider_name = "openai"
    provider.model = "gpt-4"
    provider.generate = AsyncMock(
        return_value=generation.GenerateResponse(
            answer="Answer", provider="openai", model="gpt-4"
        )
    )

    async def _aiter():
        for c in ("c1", "c2"):
            yield c

    provider.generate_stream = MagicMock(return_value=_aiter())
    provider.chat = AsyncMock(return_value="chat reply")

    monkeypatch.setattr(generation, "llm_provider", provider)
    monkeypatch.setattr(generation, "chat_sessions", {})
    return TestClient(generation.app), provider


def test_health(client):
    c, _ = client
    resp = c.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "healthy"


def test_status(client):
    c, _ = client
    resp = c.get("/status")
    assert resp.status_code == 200
    body = resp.json()
    assert body["service"] == "generation-pipeline"
    assert body["status"] == "ok"
    assert body["provider"] == "openai"


def test_generate(client):
    c, provider = client
    resp = c.post("/generate", json={"question": "Q"})
    assert resp.status_code == 200
    assert resp.json()["answer"] == "Answer"
    provider.generate.assert_awaited_once()


def test_generate_uninitialized(monkeypatch):
    monkeypatch.setattr(generation, "llm_provider", None)
    c = TestClient(generation.app)
    resp = c.post("/generate", json={"question": "Q"})
    assert resp.status_code == 503


def test_generate_stream(client):
    c, provider = client
    with c.stream("POST", "/generate/stream", json={"question": "Q"}) as resp:
        assert resp.status_code == 200
        body = "".join(resp.iter_text())
    assert "c1" in body
    assert "c2" in body
    assert "[DONE]" in body


def test_chat_init_and_message(client):
    c, provider = client
    init = c.post("/chat/init", json={"document_id": 1, "document_title": "Doc"})
    assert init.status_code == 200
    chat_id = init.json()["chat_id"]

    msg = c.post(
        "/chat/message", json={"chat_id": chat_id, "message": "Hello"}
    )
    assert msg.status_code == 200
    assert msg.json()["role"] == "assistant"
    assert msg.json()["message"] == "chat reply"
    provider.chat.assert_awaited_once()


def test_chat_message_unknown_session(client):
    c, _ = client
    resp = c.post(
        "/chat/message", json={"chat_id": "nope", "message": "hi"}
    )
    assert resp.status_code == 404


def test_chat_message_stream(client):
    c, provider = client

    async def _aiter():
        for chunk in ("hello", " world"):
            yield chunk

    provider.generate_stream = MagicMock(return_value=_aiter())
    provider.chat = AsyncMock(return_value="ignored")

    init = c.post("/chat/init", json={"document_id": 1})
    chat_id = init.json()["chat_id"]

    with c.stream(
        "POST", "/chat/message/stream", json={"chat_id": chat_id, "message": "hi"}
    ) as resp:
        assert resp.status_code == 200
        body = "".join(resp.iter_text())

    assert "hello" in body
    assert "world" in body
    assert "[DONE]" in body


def test_generate_error_propagates(client):
    c, provider = client
    provider.generate = AsyncMock(side_effect=Exception("gen failed"))
    resp = c.post("/generate", json={"question": "Q"})
    assert resp.status_code == 500


def test_lifespan_sets_provider(monkeypatch):
    from contextlib import asynccontextmanager

    provider = MagicMock()
    monkeypatch.setattr(
        "python_llm.factory.LLMProviderFactory.create", lambda *a, **k: provider
    )
    monkeypatch.setattr(generation, "llm_provider", None)

    @asynccontextmanager
    async def run_lifespan():
        async with generation.lifespan(generation.app) as cm:
            yield cm

    with TestClient(generation.app) as test_client:
        assert test_client.get("/health").status_code == 200
