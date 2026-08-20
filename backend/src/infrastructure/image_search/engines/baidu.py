"""百度以图搜图引擎（graph.baidu.com 抓取）。"""

import asyncio
import time
from typing import Any
from urllib.parse import parse_qs, urlparse

import httpx

from ...config.settings import Settings
from ..base import SearchEngine
from ..exceptions import EngineParseError
from ..http import AsyncHTTPClient
from ..models import SearchResult


class BaiduImageSearchEngine(SearchEngine):
    """百度以图搜图（上传 → 取 sign → 相似列表 JSON）。"""

    name = "baidu"

    def __init__(self, settings: Settings, http: AsyncHTTPClient) -> None:
        super().__init__(timeout=settings.IMAGE_SEARCH_BAIDU_TIMEOUT)
        self._settings = settings
        self._http = http
        self._lock = asyncio.Lock()
        self._last_request_at = 0.0

    def is_configured(self) -> bool:
        return self._settings.IMAGE_SEARCH_BAIDU_ENABLED

    async def search(self, image_url: str) -> list[SearchResult]:
        settings = self._settings
        headers = self._base_headers()

        if settings.IMAGE_SEARCH_BAIDU_UPLOAD_MODE == "url":
            upload_resp = await self._upload_by_url(image_url, headers)
        else:
            upload_resp = await self._upload_by_bytes(image_url, headers)

        try:
            upload_json = upload_resp.json()
        except ValueError as e:
            raise EngineParseError(f"百度上传响应非 JSON: {e}") from e

        # 百度识图接口反爬：status=1 且 msg=Reject 表示服务端拒绝（data 为 null）
        if isinstance(upload_json, dict) and upload_json.get("status") not in (None, 0):
            msg = upload_json.get("msg") or upload_json.get("status")
            raise EngineParseError(f"百度识图接口拒绝请求：{msg}（可能被反爬拦截，接口已失效）")

        sign = _extract_sign(upload_json)
        if not sign:
            raise EngineParseError("百度识图接口未返回有效结果（可能被反爬拦截）")

        similar_url = f"{settings.IMAGE_SEARCH_BAIDU_SIMILAR_URL}?sign={sign}"
        payload = await self._http.get_json(
            similar_url, timeout=self.timeout, headers=self._base_headers()
        )
        return _parse_similar_list(payload, settings.IMAGE_SEARCH_MAX_RESULTS, self.name)

    def _base_headers(self) -> dict[str, str]:
        """构造反爬请求头（UA + Referer + 可选 Cookie）。"""
        headers = {
            "User-Agent": self._settings.IMAGE_SEARCH_USER_AGENT,
            "Referer": self._settings.IMAGE_SEARCH_BAIDU_REFERER,
        }
        if self._settings.IMAGE_SEARCH_BAIDU_COOKIE:
            headers["Cookie"] = self._settings.IMAGE_SEARCH_BAIDU_COOKIE
        return headers

    async def _throttle(self) -> None:
        """请求间隔控制：发请求前补齐最小间隔，防反爬封禁。"""
        interval = self._settings.IMAGE_SEARCH_BAIDU_REQUEST_INTERVAL
        if interval <= 0:
            return
        async with self._lock:
            now = time.monotonic()
            wait = interval - (now - self._last_request_at)
            if wait > 0:
                await asyncio.sleep(wait)
            self._last_request_at = time.monotonic()

    async def _upload_by_bytes(self, image_url: str, headers: dict[str, str]) -> httpx.Response:
        """下载图片字节后以 multipart 上传（默认，最稳）。"""
        await self._throttle()
        data = await self._http.get_bytes(
            image_url,
            timeout=self.timeout,
            headers={"User-Agent": self._settings.IMAGE_SEARCH_USER_AGENT},
        )
        files = {"image": ("query.jpg", data, "image/jpeg")}
        return await self._http.post_multipart(
            self._settings.IMAGE_SEARCH_BAIDU_UPLOAD_URL,
            files=files,
            timeout=self.timeout,
            headers=headers,
        )

    async def _upload_by_url(self, image_url: str, headers: dict[str, str]) -> httpx.Response:
        """直接以表单字段上传图片 URL（备选，省一次下载但可能被拦）。"""
        await self._throttle()
        return await self._http.post_form(
            self._settings.IMAGE_SEARCH_BAIDU_UPLOAD_URL,
            data={"image": image_url},
            timeout=self.timeout,
            headers=headers,
        )


def _extract_sign(upload_json: Any) -> str | None:
    """从百度上传响应中提取 sign 参数（用于拉取相似图列表）。"""
    data = upload_json.get("data") if isinstance(upload_json, dict) else None
    url = data.get("url") if isinstance(data, dict) else None
    if not url:
        return None
    return parse_qs(urlparse(url).query).get("sign", [None])[0]


def _parse_similar_list(payload: Any, limit: int, source_name: str) -> list[SearchResult]:
    """解析百度相似图 JSON（data.list），提取 thumbUrl/fromUrl。"""
    data = payload.get("data") if isinstance(payload, dict) else None
    items = data.get("list") if isinstance(data, dict) else None
    if not isinstance(items, list):
        return []

    results: list[SearchResult] = []
    for item in items:
        if not isinstance(item, dict):
            continue
        thumbnail = item.get("thumbUrl") or item.get("objUrl") or ""
        source = item.get("fromUrl") or item.get("objUrl") or ""
        if not thumbnail and not source:
            continue
        results.append(
            SearchResult(
                thumbnail_url=thumbnail,
                source_url=source,
                source_name=source_name,
                title=item.get("fromUrlHost"),
                score=None,
            )
        )
        if len(results) >= limit:
            break
    return results
