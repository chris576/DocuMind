"""Unit tests for the concrete LLM providers (mocked clients)."""
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from python_llm.anthropic import AnthropicProvider
from python_llm.base import ChatMessage, GenerateRequest
from python_llm.custom import CustomProvider
from python_llm.ollama import OllamaProvider
from python_llm.opencode import OpenCodeProvider
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


@pytest.mark.anyio
async def test_openai_chat():
    client = _openai_client()
    resp = SimpleNamespace(
        choices=[SimpleNamespace(message=SimpleNamespace(content="chat A"))]
    )
    client.chat.completions.create = AsyncMock(return_value=resp)

    provider = OpenAIProvider({"model": "gpt-4", "openai_api_key": "k"})
    provider.client = client
    reply = await provider.chat([ChatMessage(role="user", content="hi")])
    assert reply == "chat A"
    kwargs = client.chat.completions.create.await_args.kwargs
    assert kwargs["model"] == "gpt-4"
    assert kwargs["messages"] == [{"role": "user", "content": "hi"}]


@pytest.mark.anyio
async def test_openai_generate_propagates_api_error():
    client = _openai_client()
    client.chat.completions.create = AsyncMock(side_effect=Exception("api down"))

    provider = OpenAIProvider({"model": "gpt-4", "openai_api_key": "k"})
    provider.client = client
    with pytest.raises(Exception, match="api down"):
        await provider.generate(GenerateRequest(question="Q"))


@pytest.mark.anyio
async def test_anthropic_generate_stream():
    client = MagicMock()

    class FakeTextStream:
        def __init__(self):
            self._items = iter(["An", "thropic"])

        def __aiter__(self):
            return self

        async def __anext__(self):
            try:
                return next(self._items)
            except StopIteration:
                raise StopAsyncIteration

    class FakeStreamCtx:
        def __init__(self):
            self.text_stream = FakeTextStream()

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            return False

    client.messages.stream.return_value = FakeStreamCtx()

    provider = AnthropicProvider({"model": "claude-3"})
    provider.client = client
    collected = [
        chunk async for chunk in provider.generate_stream(GenerateRequest(question="Q"))
    ]
    assert collected == ["An", "thropic"]


@pytest.mark.anyio
async def test_anthropic_chat_filters_non_user_assistant():
    client = MagicMock()
    resp = SimpleNamespace(content=[SimpleNamespace(text="reply")])
    client.messages.create = AsyncMock(return_value=resp)

    provider = AnthropicProvider({"model": "claude-3"})
    provider.client = client
    reply = await provider.chat(
        [
            ChatMessage(role="system", content="sys"),
            ChatMessage(role="user", content="hi"),
            ChatMessage(role="assistant", content="prev"),
        ]
    )
    assert reply == "reply"
    kwargs = client.messages.create.await_args.kwargs
    assert kwargs["messages"] == [
        {"role": "user", "content": "hi"},
        {"role": "assistant", "content": "prev"},
    ]


@pytest.mark.anyio
async def test_ollama_generate_with_usage():
    client = _openai_client()
    resp = SimpleNamespace(
        choices=[SimpleNamespace(message=SimpleNamespace(content="O"))],
        usage=SimpleNamespace(prompt_tokens=3, completion_tokens=4, total_tokens=7),
    )
    client.chat.completions.create = AsyncMock(return_value=resp)

    provider = OllamaProvider({"base_url": "http://localhost:11434"})
    provider.client = client
    result = await provider.generate(GenerateRequest(question="Q"))
    assert result.answer == "O"
    assert result.prompt_tokens == 3
    assert result.completion_tokens == 4
    assert result.total_tokens == 7


@pytest.mark.anyio
async def test_ollama_chat():
    client = _openai_client()
    resp = SimpleNamespace(
        choices=[SimpleNamespace(message=SimpleNamespace(content="chat O"))]
    )
    client.chat.completions.create = AsyncMock(return_value=resp)

    provider = OllamaProvider({"base_url": "http://localhost:11434"})
    provider.client = client
    reply = await provider.chat([ChatMessage(role="user", content="hi")])
    assert reply == "chat O"


@pytest.mark.anyio
async def test_ollama_generate_stream_skips_empty_deltas():
    client = _openai_client()
    chunk1 = SimpleNamespace(
        choices=[SimpleNamespace(delta=SimpleNamespace(content="A"))]
    )
    chunk2 = SimpleNamespace(
        choices=[SimpleNamespace(delta=SimpleNamespace(content="B"))]
    )
    chunk3 = SimpleNamespace(
        choices=[SimpleNamespace(delta=SimpleNamespace(content=None))]
    )

    async def _aiter():
        for c in (chunk1, chunk2, chunk3):
            yield c

    client.chat.completions.create = AsyncMock(return_value=_aiter())

    provider = OllamaProvider({"base_url": "http://localhost:11434"})
    provider.client = client
    collected = [
        chunk async for chunk in provider.generate_stream(GenerateRequest(question="Q"))
    ]
    assert collected == ["A", "B"]


@pytest.mark.anyio
@patch("python_llm.custom.openai.AsyncOpenAI")
async def test_custom_chat(mock_openai_cls):
    client = _openai_client()
    resp = SimpleNamespace(
        choices=[SimpleNamespace(message=SimpleNamespace(content="chat C"))]
    )
    client.chat.completions.create = AsyncMock(return_value=resp)
    mock_openai_cls.return_value = client

    provider = CustomProvider({"model": "m", "custom_base_url": "http://c"})
    provider.client = client
    reply = await provider.chat([ChatMessage(role="user", content="hi")])
    assert reply == "chat C"


@pytest.mark.anyio
@patch("python_llm.custom.openai.AsyncOpenAI")
async def test_custom_generate_stream(mock_openai_cls):
    client = _openai_client()
    chunk1 = SimpleNamespace(
        choices=[SimpleNamespace(delta=SimpleNamespace(content="C1"))]
    )
    chunk2 = SimpleNamespace(
        choices=[SimpleNamespace(delta=SimpleNamespace(content="C2"))]
    )

    async def _aiter():
        for c in (chunk1, chunk2):
            yield c

    client.chat.completions.create = AsyncMock(return_value=_aiter())
    mock_openai_cls.return_value = client

    provider = CustomProvider({"model": "m", "custom_base_url": "http://c"})
    provider.client = client
    collected = [
        chunk async for chunk in provider.generate_stream(GenerateRequest(question="Q"))
    ]
    assert collected == ["C1", "C2"]


def _opencode_response(payload):
    resp = MagicMock()
    resp.raise_for_status = MagicMock()
    resp.json.return_value = payload
    return resp


def _opencode_client(session_id="sess-1", parts=None):
    client = MagicMock()
    parts = parts if parts is not None else [{"type": "text", "text": "OpenCode A"}]
    client.post = AsyncMock(
        side_effect=[
            _opencode_response({"id": session_id}),
            _opencode_response({"parts": parts}),
        ]
    )
    return client


@pytest.mark.anyio
async def test_opencode_generate():
    client = _opencode_client()
    provider = OpenCodeProvider({})
    provider._client = client

    result = await provider.generate(GenerateRequest(question="Q"))
    assert result.answer == "OpenCode A"
    assert result.provider == "opencode"
    assert result.model == ""


@pytest.mark.anyio
async def test_opencode_generate_stream_single_chunk():
    client = _opencode_client()
    provider = OpenCodeProvider({})
    provider._client = client

    collected = [
        chunk async for chunk in provider.generate_stream(GenerateRequest(question="Q"))
    ]
    assert collected == ["OpenCode A"]


@pytest.mark.anyio
async def test_opencode_chat():
    client = _opencode_client(parts=[{"type": "text", "text": "chat reply"}])
    provider = OpenCodeProvider({})
    provider._client = client

    reply = await provider.chat([ChatMessage(role="user", content="hi")])
    assert reply == "chat reply"


def test_opencode_model_body():
    assert OpenCodeProvider({})._model_body() == {}
    assert OpenCodeProvider(
        {"opencode_model": "anthropic/claude-3-5-sonnet"}
    )._model_body() == {
        "model": {"providerID": "anthropic", "modelID": "claude-3-5-sonnet"}
    }


def test_opencode_extract_text():
    payload = {
        "parts": [
            {"type": "text", "text": "first"},
            {"type": "text", "text": None},
            {"type": "tool", "text": "ignored"},
            {"type": "text", "text": "second"},
        ]
    }
    assert OpenCodeProvider._extract_text(payload) == "first\nsecond"
    assert OpenCodeProvider._extract_text({"parts": []}) == ""
