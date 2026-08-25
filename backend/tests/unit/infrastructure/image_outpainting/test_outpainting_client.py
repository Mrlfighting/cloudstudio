"""BailianOutpaintingClient 请求/解析/错误翻译单元测试。"""

from unittest.mock import AsyncMock

import httpx
import pytest

from src.infrastructure.image_outpainting.client import BailianOutpaintingClient
from src.infrastructure.image_outpainting.exceptions import (
    OutpaintingParseError,
    OutpaintingRequestError,
    OutpaintingTimeoutError,
)
from src.infrastructure.image_outpainting.models import OutpaintingParameters


def _client_with(request_mock) -> BailianOutpaintingClient:
    client = BailianOutpaintingClient(
        base_url="https://ws-test.cn-beijing.maas.aliyuncs.com", api_key="sk-test"
    )
    client._client = AsyncMock()
    client._client.request = request_mock
    return client


def _resp(status_code: int, payload: dict) -> httpx.Response:
    return httpx.Response(
        status_code,
        json=payload,
        request=httpx.Request("POST", "http://x"),
    )


@pytest.mark.asyncio
async def test_create_task_ok():
    resp = _resp(200, {"output": {"task_id": "t-1", "task_status": "PENDING"}})
    client = _client_with(AsyncMock(return_value=resp))
    result = await client.create_task("http://img", OutpaintingParameters(x_scale=1.5))
    assert result.task_id == "t-1"
    assert result.task_status == "PENDING"


@pytest.mark.asyncio
async def test_create_task_missing_task_id():
    resp = _resp(200, {"output": {"task_status": "PENDING"}})
    client = _client_with(AsyncMock(return_value=resp))
    with pytest.raises(OutpaintingParseError):
        await client.create_task("http://img", OutpaintingParameters())


@pytest.mark.asyncio
async def test_query_task_succeeded():
    resp = _resp(
        200,
        {"output": {"task_id": "t-1", "task_status": "SUCCEEDED", "output_image_url": "http://res/img.jpg"}},
    )
    client = _client_with(AsyncMock(return_value=resp))
    result = await client.query_task("t-1")
    assert result.task_status == "SUCCEEDED"
    assert result.output_image_url == "http://res/img.jpg"
    assert result.code is None


@pytest.mark.asyncio
async def test_query_task_running_no_url():
    resp = _resp(200, {"output": {"task_id": "t-1", "task_status": "RUNNING"}})
    client = _client_with(AsyncMock(return_value=resp))
    result = await client.query_task("t-1")
    assert result.task_status == "RUNNING"
    assert result.output_image_url is None


@pytest.mark.asyncio
async def test_query_task_failed_carries_error():
    resp = _resp(
        200,
        {"output": {"task_id": "t-1", "task_status": "FAILED", "code": "InvalidParameter", "message": "bad input"}},
    )
    client = _client_with(AsyncMock(return_value=resp))
    result = await client.query_task("t-1")
    assert result.task_status == "FAILED"
    assert result.code == "InvalidParameter"
    assert result.message == "bad input"
    assert result.output_image_url is None


@pytest.mark.asyncio
async def test_non_2xx_translated():
    resp = _resp(401, {"code": "InvalidApiKey", "message": "no key"})
    client = _client_with(AsyncMock(return_value=resp))
    with pytest.raises(OutpaintingRequestError):
        await client.query_task("t-1")


@pytest.mark.asyncio
async def test_200_with_top_level_code_translated():
    resp = _resp(200, {"code": "InvalidParameter", "message": "bad", "request_id": "r"})
    client = _client_with(AsyncMock(return_value=resp))
    with pytest.raises(OutpaintingRequestError):
        await client.create_task("http://img", OutpaintingParameters())


@pytest.mark.asyncio
async def test_timeout_translated():
    client = _client_with(AsyncMock(side_effect=httpx.TimeoutException("t")))
    with pytest.raises(OutpaintingTimeoutError):
        await client.query_task("t-1")


@pytest.mark.asyncio
async def test_network_error_translated():
    client = _client_with(AsyncMock(side_effect=httpx.ConnectError("refused")))
    with pytest.raises(OutpaintingRequestError):
        await client.query_task("t-1")
