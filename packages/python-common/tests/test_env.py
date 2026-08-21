"""Unit tests for python-common env helper."""
from python_common.env import get_env


def test_get_env_returns_value(monkeypatch):
    monkeypatch.setenv("TEST_KEY", "hello")
    assert get_env("TEST_KEY") == "hello"


def test_get_env_missing_returns_default(monkeypatch):
    monkeypatch.delenv("MISSING_KEY", raising=False)
    assert get_env("MISSING_KEY", "default") == "default"


def test_get_env_empty_returns_default(monkeypatch):
    monkeypatch.setenv("EMPTY_KEY", "")
    assert get_env("EMPTY_KEY", "default") == "default"


def test_get_env_missing_no_default_returns_none(monkeypatch):
    monkeypatch.delenv("MISSING_KEY", raising=False)
    assert get_env("MISSING_KEY") is None
