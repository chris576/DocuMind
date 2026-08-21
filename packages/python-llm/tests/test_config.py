"""Unit tests for python-llm config."""

from python_llm.config import LLMConfig, load_llm_config


def test_llm_config_to_provider_config():
    cfg = LLMConfig(
        provider="openai",
        model="gpt-4",
        api_key="sk-123",
        base_url="http://localhost:11434",
        anthropic_api_key="ant-123",
        custom_base_url="http://custom:8000",
        custom_api_key="cust-key",
        custom_model="mymodel",
    )
    assert cfg.to_provider_config() == {
        "model": "gpt-4",
        "openai_api_key": "sk-123",
        "anthropic_api_key": "ant-123",
        "ollama_base_url": "http://localhost:11434",
        "custom_base_url": "http://custom:8000",
        "custom_api_key": "cust-key",
        "custom_model": "mymodel",
    }


def test_load_llm_config_defaults(monkeypatch):
    for var in (
        "LLM_PROVIDER",
        "LLM_MODEL",
        "OPENAI_API_KEY",
        "OLLAMA_BASE_URL",
        "ANTHROPIC_API_KEY",
        "CUSTOM_BASE_URL",
        "CUSTOM_API_KEY",
        "CUSTOM_MODEL",
    ):
        monkeypatch.delenv(var, raising=False)

    cfg = load_llm_config()
    assert cfg.provider == "ollama"
    assert cfg.model == "llama3.2"
    assert cfg.base_url == "http://localhost:11434"
    assert cfg.api_key is None


def test_load_llm_config_from_env(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "openai")
    monkeypatch.setenv("LLM_MODEL", "gpt-4")
    monkeypatch.setenv("OPENAI_API_KEY", "sk-123")

    cfg = load_llm_config()
    assert cfg.provider == "openai"
    assert cfg.model == "gpt-4"
    assert cfg.api_key == "sk-123"
