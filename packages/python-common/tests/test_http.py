"""Unit tests for python-common HTTP helpers (mocked httpx)."""
from unittest.mock import AsyncMock, MagicMock, patch

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
