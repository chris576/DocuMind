"""Unit tests for the concrete LLM providers (mocked clients)."""
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from python_llm.anthropic import AnthropicProvider
from python_llm.base import GenerateRequest
from python_llm.custom import CustomProvider
from python_llm.ollama import OllamaProvider
from python_llm.openai import OpenAIProvider


def _openai_client():
    return MagicMock()


@pytest.mark.anyio
async def test_openai_generate():
    client = _openai_client()
    resp = SimpleNamespace(
        choices=[SimpleNamespace(message=SimpleNamespace(content="Answer A"))],
        usage=SimpleNamespace(prompt_tokens=10, completion_tokens=5, total_tokens=15),
    )
    client.chat.completions.create = AsyncMock(return_value=resp)

    provider = OpenAIProvider({"model": "gpt-4", "openai_api_key": "k"})
    provider.client = client  # avoid network/constructor side effects

    result = await provider.generate(GenerateRequest(question="Q"))
    assert result.answer == "Answer A"
    assert result.prompt_tokens == 10
    assert result.completion_tokens == 5
    assert result.total_tokens == 15
    assert result.provider == "openai"
    assert result.model == "gpt-4"
    assert provider.provider_name == "openai"


@pytest.mark.anyio
async def test_openai_generate_stream():
    client = _openai_client()
    chunk1 = SimpleNamespace(choices=[SimpleNamespace(delta=SimpleNamespace(content="Hel"))])
    chunk2 = SimpleNamespace(choices=[SimpleNamespace(delta=SimpleNamespace(content="lo"))])

    async def _aiter():
        for c in (chunk1, chunk2):
            yield c

    client.chat.completions.create = AsyncMock(return_value=_aiter())

    provider = OpenAIProvider({"model": "gpt-4", "openai_api_key": "k"})
    provider.client = client

    collected = [
        chunk async for chunk in provider.generate_stream(GenerateRequest(question="Q"))
    ]
    assert collected == ["Hel", "lo"]


@pytest.mark.anyio
async def test_ollama_generate_no_usage():
    client = _openai_client()
    resp = SimpleNamespace(
        choices=[SimpleNamespace(message=SimpleNamespace(content="O"))],
        usage=None,
    )
    client.chat.completions.create = AsyncMock(return_value=resp)

    provider = OllamaProvider({"base_url": "http://localhost:11434"})
    provider.client = client
    result = await provider.generate(GenerateRequest(question="Q"))
    assert result.answer == "O"
    assert result.prompt_tokens == 0
    assert result.completion_tokens == 0
    assert result.total_tokens == 0


@pytest.mark.anyio
async def test_anthropic_generate():
    client = MagicMock()
    resp = SimpleNamespace(
        content=[SimpleNamespace(text="Anthropic A")],
        usage=SimpleNamespace(input_tokens=20, output_tokens=7),
    )
    client.messages.create = AsyncMock(return_value=resp)

    provider = AnthropicProvider({"model": "claude-3", "anthropic_api_key": "k"})
    provider.client = client
    result = await provider.generate(GenerateRequest(question="Q"))
    assert result.answer == "Anthropic A"
    assert result.prompt_tokens == 20
    assert result.completion_tokens == 7
    assert result.total_tokens == 27


@pytest.mark.anyio
async def test_anthropic_chat():
    client = MagicMock()
    resp = SimpleNamespace(content=[SimpleNamespace(text="chat reply")])
    client.messages.create = AsyncMock(return_value=resp)

    provider = AnthropicProvider({"model": "claude-3"})
    provider.client = client
    from python_llm.base import ChatMessage

    reply = await provider.chat([ChatMessage(role="user", content="hi")])
    assert reply == "chat reply"
    kwargs = client.messages.create.await_args.kwargs
    assert kwargs["messages"] == [{"role": "user", "content": "hi"}]


@pytest.mark.anyio
@patch("python_llm.custom.openai.AsyncOpenAI")
async def test_custom_generate(mock_openai_cls):
    client = _openai_client()
    resp = SimpleNamespace(
        choices=[SimpleNamespace(message=SimpleNamespace(content="C"))],
        usage=SimpleNamespace(prompt_tokens=1, completion_tokens=1, total_tokens=2),
    )
    client.chat.completions.create = AsyncMock(return_value=resp)
    mock_openai_cls.return_value = client

    provider = CustomProvider({"model": "m", "custom_base_url": "http://c"})
    provider.client = client
    result = await provider.generate(GenerateRequest(question="Q"))
    assert result.answer == "C"
    assert result.provider == "custom"
