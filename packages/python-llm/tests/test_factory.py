"""Unit tests for the LLM provider factory."""
import pytest

from python_llm.anthropic import AnthropicProvider
from python_llm.custom import CustomProvider
from python_llm.factory import LLMProviderFactory
from python_llm.ollama import OllamaProvider
from python_llm.opencode import OpenCodeProvider
from python_llm.openai import OpenAIProvider


def test_create_openai():
    with pytest.MonkeyPatch.context() as mp:
        mp.setattr("python_llm.openai.openai.AsyncOpenAI", lambda **kw: object())
        provider = LLMProviderFactory.create("openai", {"model": "gpt-4"})
        assert isinstance(provider, OpenAIProvider)


def test_create_ollama_case_insensitive():
    with pytest.MonkeyPatch.context() as mp:
        mp.setattr("python_llm.ollama.openai.AsyncOpenAI", lambda **kw: object())
        provider = LLMProviderFactory.create("OLLAMA", {"model": "llama3.2"})
        assert isinstance(provider, OllamaProvider)


def test_create_anthropic():
    with pytest.MonkeyPatch.context() as mp:
        mp.setattr(
            "python_llm.anthropic.anthropic.AsyncAnthropic", lambda **kw: object()
        )
        provider = LLMProviderFactory.create("anthropic", {})
        assert isinstance(provider, AnthropicProvider)


def test_create_custom():
    with pytest.MonkeyPatch.context() as mp:
        mp.setattr("python_llm.custom.openai.AsyncOpenAI", lambda **kw: object())
        provider = LLMProviderFactory.create("custom", {})
        assert isinstance(provider, CustomProvider)


def test_create_opencode():
    provider = LLMProviderFactory.create("opencode", {})
    assert isinstance(provider, OpenCodeProvider)


def test_create_unknown():
    with pytest.raises(ValueError, match="Unknown LLM provider"):
        LLMProviderFactory.create("nope", {})
