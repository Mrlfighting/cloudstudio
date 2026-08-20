"""共享 HTTP 客户端封装（httpx）。

统一超时、默认头、轻量重试与异常翻译（httpx 异常 → ImageSearchException），
单连接池复用，由门面持有并传给各引擎。
"""

from typing import Any

import httpx

from ..logging import get_logger
from .exceptions import EngineRequestError, EngineTimeoutError

logger = get_logger()


class AsyncHTTPClient:
    """基于 httpx 的轻量异步 HTTP 客户端。

    所有方法把底层 httpx 异常翻译为 ImageSearchException 子类，
    引擎只需处理业务语义，不直接接触 httpx。
    """

    def __init__(
        self,
        *,
        default_timeout: float = 10.0,
        default_headers: dict[str, str] | None = None,
        max_retries: int = 0,
    ) -> None:
        self._client = httpx.AsyncClient(
            timeout=default_timeout,
            headers=default_headers,
            follow_redirects=True,
        )
        self._max_retries = max(0, max_retries)

    async def _request(self, method: str, url: str, **kwargs: Any) -> httpx.Response:
        """发起请求，对超时/5xx 做轻量重试，非 2xx 抛 EngineRequestError。"""
        attempts = self._max_retries + 1
        last_exc: Exception | None = None

        for attempt in range(attempts):
            try:
                resp = await self._client.request(method, url, **kwargs)
            except httpx.TimeoutException as e:
                last_exc = EngineTimeoutError(f"{method} {url} 超时: {e}")
                logger.warning(f"HTTP 超时 {method} {url}", extra={"reason": "http_timeout"})
                continue
            except httpx.HTTPError as e:
                raise EngineRequestError(f"{method} {url} 请求失败: {e}") from e

            if resp.status_code >= 500:
                last_exc = EngineRequestError(f"{method} {url} 返回 {resp.status_code}")
                logger.warning(
                    f"HTTP 5xx {method} {url}",
                    extra={"reason": "http_5xx", "status_code": resp.status_code},
                )
                if attempt < attempts - 1:
                    continue
                raise last_exc

            if resp.status_code >= 400:
                raise EngineRequestError(
                    f"{method} {url} 返回 {resp.status_code}: {resp.text[:200]}"
                )
            return resp

        raise last_exc or EngineRequestError(f"{method} {url} 请求失败")

    async def get_bytes(
        self,
        url: str,
        *,
        timeout: float | None = None,
        headers: dict[str, str] | None = None,
    ) -> bytes:
        """GET 返回响应字节（用于下载图片）。"""
        resp = await self._request("GET", url, timeout=timeout, headers=headers)
        return resp.content

    async def get_json(
        self,
        url: str,
        *,
        timeout: float | None = None,
        headers: dict[str, str] | None = None,
    ) -> Any:
        """GET 返回解析后的 JSON。"""
        resp = await self._request("GET", url, timeout=timeout, headers=headers)
        try:
            return resp.json()
        except ValueError as e:
            raise EngineRequestError(f"{url} 返回非 JSON: {e}") from e

    async def post_multipart(
        self,
        url: str,
        *,
        files: dict[str, Any],
        data: dict[str, Any] | None = None,
        timeout: float | None = None,
        headers: dict[str, str] | None = None,
    ) -> httpx.Response:
        """POST multipart 表单，返回原始 Response（由引擎自行解析 JSON）。"""
        return await self._request(
            "POST", url, files=files, data=data, timeout=timeout, headers=headers
        )

    async def post_form(
        self,
        url: str,
        *,
        data: dict[str, Any],
        timeout: float | None = None,
        headers: dict[str, str] | None = None,
    ) -> httpx.Response:
        """POST urlencoded 表单，返回原始 Response。"""
        return await self._request("POST", url, data=data, timeout=timeout, headers=headers)

    @property
    def cookies(self) -> httpx.Cookies:
        """当前连接池的 cookie jar（跨请求自动携带 Set-Cookie）。"""
        return self._client.cookies

    async def close(self) -> None:
        """关闭连接池。"""
        await self._client.aclose()
