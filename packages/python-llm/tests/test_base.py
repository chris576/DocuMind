"""Unit tests for the LLM provider base prompt builder."""
from python_llm.base import (
    BaseLLMProvider,
    GenerateRequest,
    GenerateResponse,
)


class EmptyProvider(BaseLLMProvider):
    """Minimal concrete provider only exercising the base prompt builder."""

    async def generate(self, request):
        raise NotImplementedError

    async def generate_stream(self, request):
        raise NotImplementedError

    async def chat(self, messages, stream=False):
        raise NotImplementedError


def test_prompt_builder_plain_question():
    provider = EmptyProvider({"model": "m"})
    prompt = provider._build_prompt(GenerateRequest(question="Who pays?"))

    assert "Question: Who pays?" in prompt
    assert "Answer:" in prompt
    # No context/sources section when absent.
    assert "Context:" not in prompt
    assert "Sources:" not in prompt


def test_prompt_builder_with_context_and_sources():
    provider = EmptyProvider({"model": "m"})
    request = GenerateRequest(
        question="Who pays?",
        context="Invoice context here",
        sources=[
            {"title": "Rechnung", "correspondent": "ACME", "date": "2024-01-01"},
        ],
    )
    prompt = provider._build_prompt(request)

    assert "Context:\nInvoice context here" in prompt
    assert "Sources:" in prompt
    assert "1. Rechnung (ACME, 2024-01-01)" in prompt


def test_prompt_builder_sources_without_context():
    provider = EmptyProvider({"model": "m"})
    request = GenerateRequest(
        question="Q",
        sources=[{"title": "T", "correspondent": "C", "date": "D"}],
    )
    prompt = provider._build_prompt(request)

    assert "Sources:" in prompt
    assert "1. T (C, D)" in prompt
    assert "Context:" not in prompt


def test_prompt_builder_unknown_fallbacks():
    provider = EmptyProvider({"model": "m"})
    request = GenerateRequest(question="Q", context="ctx", sources=[{}])
    prompt = provider._build_prompt(request)

    assert "1. Unknown (Unknown, Unknown)" in prompt


def test_generate_request_defaults():
    request = GenerateRequest(question="Q")
    assert request.context == ""
    assert request.sources == []
    assert request.max_tokens == 1000
    assert request.temperature == 0.7
    assert request.stream is False


def test_generate_response_defaults():
    response = GenerateResponse(answer="A")
    assert response.answer == "A"
    assert response.prompt_tokens == 0
    assert response.completion_tokens == 0
    assert response.total_tokens == 0
    assert response.model == ""
    assert response.provider == ""
