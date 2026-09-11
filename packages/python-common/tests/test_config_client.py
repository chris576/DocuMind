"""Unit tests for the gateway config-client (mocked httpx)."""
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from python_common.config_client import fetch_config_slice, gateway_url


def test_gateway_url_defaults(monkeypatch):
    monkeypatch.delenv("GATEWAY_URL", raising=False)
    assert gateway_url() == "http://localhost:3001"


def test_gateway_url_trims_trailing_slash(monkeypatch):
    monkeypatch.setenv("GATEWAY_URL", "http://gw:3001/")
    assert gateway_url() == "http://gw:3001"


@pytest.mark.anyio
@patch("python_common.config_client.httpx.AsyncClient")
async def test_fetch_slice_returns_dict(mock_client_cls):
    client = AsyncMock()
    resp = MagicMock()
    resp.json.return_value = {"provider": "openai"}
    client.get.return_value = resp
    client.__aenter__.return_value = client
    mock_client_cls.return_value = client

    result = await fetch_config_slice("llm")
    assert result == {"provider": "openai"}
    client.get.assert_awaited_once()


@pytest.mark.anyio
@patch("python_common.config_client.httpx.AsyncClient")
async def test_fetch_slice_returns_none_on_error(mock_client_cls):
    client = AsyncMock()
    client.get.side_effect = Exception("boom")
    client.__aenter__.return_value = client
    mock_client_cls.return_value = client

    result = await fetch_config_slice("llm")
    assert result is None


@pytest.mark.anyio
@patch("python_common.config_client.httpx.AsyncClient")
async def test_fetch_slice_returns_none_on_non_dict(mock_client_cls):
    client = AsyncMock()
    resp = MagicMock()
    resp.json.return_value = ["not", "a", "dict"]
    client.get.return_value = resp
    client.__aenter__.return_value = client
    mock_client_cls.return_value = client

    result = await fetch_config_slice("llm")
    assert result is None
