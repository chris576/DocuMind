"""Unit tests for python-common HTTP helpers (mocked httpx)."""
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from python_common.http import post_json


@pytest.mark.anyio
@patch("python_common.http.httpx.AsyncClient")
async def test_post_json_returns_json(mock_client_cls):
    client = AsyncMock()
    resp = MagicMock()
    resp.json.return_value = {"ok": True}
    client.post.return_value = resp
    client.__aenter__.return_value = client
    mock_client_cls.return_value = client

    result = await post_json("http://svc/endpoint", {"a": 1})
    assert result == {"ok": True}
    client.post.assert_awaited_once_with("http://svc/endpoint", json={"a": 1})


@pytest.mark.anyio
@patch("python_common.http.httpx.AsyncClient")
async def test_post_json_returns_none_on_error(mock_client_cls):
    client = AsyncMock()
    client.post.side_effect = Exception("boom")
    client.__aenter__.return_value = client
    mock_client_cls.return_value = client

    result = await post_json("http://svc/endpoint", {"a": 1})
    assert result is None


@pytest.mark.anyio
@patch("python_common.http.httpx.AsyncClient")
async def test_post_json_returns_none_on_non_2xx(mock_client_cls):
    client = AsyncMock()
    resp = MagicMock()
    request = httpx.Request("POST", "http://svc/endpoint")
    response = httpx.Response(500, request=request)
    resp.raise_for_status.side_effect = httpx.HTTPStatusError(
        "Server error", request=request, response=response
    )
    client.post.return_value = resp
    client.__aenter__.return_value = client
    mock_client_cls.return_value = client

    result = await post_json("http://svc/endpoint", {"a": 1})
    assert result is None
    resp.raise_for_status.assert_called_once()


@pytest.mark.anyio
@patch("python_common.http.httpx.AsyncClient")
async def test_post_json_returns_none_on_non_dict_body(mock_client_cls):
    client = AsyncMock()
    resp = MagicMock()
    resp.raise_for_status.return_value = None
    resp.json.return_value = ["not", "a", "dict"]
    client.post.return_value = resp
    client.__aenter__.return_value = client
    mock_client_cls.return_value = client

    result = await post_json("http://svc/endpoint", {"a": 1})
    assert result is None


@pytest.mark.anyio
@patch("python_common.http.httpx.AsyncClient")
async def test_post_json_propagates_timeout(mock_client_cls):
    client = AsyncMock()
    resp = MagicMock()
    resp.json.return_value = {"ok": True}
    client.post.return_value = resp
    client.__aenter__.return_value = client
    mock_client_cls.return_value = client

    await post_json("http://svc/endpoint", {"a": 1}, timeout=5.0)
    mock_client_cls.assert_called_once_with(timeout=5.0)
