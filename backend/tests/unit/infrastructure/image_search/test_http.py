"""AsyncHTTPClient 错误翻译单元测试。"""

from unittest.mock import AsyncMock

import httpx
import pytest

from src.infrastructure.image_search.exceptions import EngineRequestError, EngineTimeoutError
from src.infrastructure.image_search.http import AsyncHTTPClient


def _client_with(request_mock) -> AsyncHTTPClient:
    http = AsyncHTTPClient()
    http._client = AsyncMock()
    http._client.request = request_mock
    return http


@pytest.mark.asyncio
async def test_timeout_translated():
    http = _client_with(AsyncMock(side_effect=httpx.TimeoutException("t")))
    with pytest.raises(EngineTimeoutError):
        await http.get_json("http://x")


@pytest.mark.asyncio
async def test_4xx_translated():
    resp = httpx.Response(404, request=httpx.Request("GET", "http://x"))
    http = _client_with(AsyncMock(return_value=resp))
    with pytest.raises(EngineRequestError):
        await http.get_json("http://x")


@pytest.mark.asyncio
async def test_non_json_translated():
    resp = httpx.Response(200, text="<html>", request=httpx.Request("GET", "http://x"))
    http = _client_with(AsyncMock(return_value=resp))
    with pytest.raises(EngineRequestError):
        await http.get_json("http://x")


@pytest.mark.asyncio
async def test_get_bytes_ok():
    resp = httpx.Response(200, content=b"data", request=httpx.Request("GET", "http://x"))
    http = _client_with(AsyncMock(return_value=resp))
    assert await http.get_bytes("http://x") == b"data"


@pytest.mark.asyncio
async def test_network_error_translated():
    http = _client_with(AsyncMock(side_effect=httpx.ConnectError("refused")))
    with pytest.raises(EngineRequestError):
        await http.get_json("http://x")
