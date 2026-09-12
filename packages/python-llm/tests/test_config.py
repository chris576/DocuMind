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
        opencode_base_url="http://opencode:4096",
        opencode_username="oc",
        opencode_password="pw",
        opencode_model="opencode/gpt-5",
    )
    assert cfg.to_provider_config() == {
        "model": "gpt-4",
        "openai_api_key": "sk-123",
        "anthropic_api_key": "ant-123",
        "ollama_base_url": "http://localhost:11434",
        "custom_base_url": "http://custom:8000",
        "custom_api_key": "cust-key",
        "custom_model": "mymodel",
        "opencode_base_url": "http://opencode:4096",
        "opencode_username": "oc",
        "opencode_password": "pw",
        "opencode_model": "opencode/gpt-5",
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
        "OPENCODE_BASE_URL",
        "OPENCODE_USERNAME",
        "OPENCODE_PASSWORD",
        "OPENCODE_MODEL",
    ):
        monkeypatch.delenv(var, raising=False)

    cfg = load_llm_config()
    assert cfg.provider == "ollama"
    assert cfg.model == "llama3.2"
    assert cfg.base_url == "http://localhost:11434"
    assert cfg.api_key is None
    assert cfg.opencode_base_url == "http://127.0.0.1:4096"
    assert cfg.opencode_username == "opencode"
    assert cfg.opencode_password is None
    assert cfg.opencode_model is None


def test_load_llm_config_from_env(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "openai")
    monkeypatch.setenv("LLM_MODEL", "gpt-4")
    monkeypatch.setenv("OPENAI_API_KEY", "sk-123")

    cfg = load_llm_config()
    assert cfg.provider == "openai"
    assert cfg.model == "gpt-4"
    assert cfg.api_key == "sk-123"


def test_load_llm_config_opencode_from_env(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "opencode")
    monkeypatch.setenv("OPENCODE_BASE_URL", "http://host:1234")
    monkeypatch.setenv("OPENCODE_USERNAME", "user")
    monkeypatch.setenv("OPENCODE_PASSWORD", "secret")
    monkeypatch.setenv("OPENCODE_MODEL", "opencode/gpt-5")

    cfg = load_llm_config()
    assert cfg.provider == "opencode"
    assert cfg.opencode_base_url == "http://host:1234"
    assert cfg.opencode_username == "user"
    assert cfg.opencode_password == "secret"
    assert cfg.opencode_model == "opencode/gpt-5"
