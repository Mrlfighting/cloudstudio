"""Bing 以图搜图引擎（Azure Bing Visual Search API）。"""

import json
from typing import Any

from ...config.settings import Settings
from ..base import SearchEngine
from ..exceptions import EngineParseError
from ..http import AsyncHTTPClient
from ..models import SearchResult

# Bing Visual Search 中表示「相似图片」的 actionType 取值
_SIMILAR_ACTION_TYPES = {"VisualSearch", "SimilarImages"}


class BingVisualSearchEngine(SearchEngine):
    """Bing 以图搜图（官方 API，需付费 API Key）。"""

    name = "bing"

    def __init__(self, settings: Settings, http: AsyncHTTPClient) -> None:
        super().__init__(timeout=settings.IMAGE_SEARCH_BING_TIMEOUT)
        self._settings = settings
        self._http = http

    def is_configured(self) -> bool:
        """有 Key 且开关打开才算已配置；无 Key 时门面自动跳过。"""
        return self._settings.IMAGE_SEARCH_BING_ENABLED and bool(
            self._settings.IMAGE_SEARCH_BING_API_KEY
        )

    async def search(self, image_url: str) -> list[SearchResult]:
        settings = self._settings
        headers = {"Ocp-Apim-Subscription-Key": settings.IMAGE_SEARCH_BING_API_KEY}
        files = {
            "knowledgeRequest": (
                None,
                json.dumps({"imageInfo": {"url": image_url}}),
                "application/json",
            )
        }
        resp = await self._http.post_multipart(
            settings.IMAGE_SEARCH_BING_ENDPOINT,
            files=files,
            timeout=self.timeout,
            headers=headers,
        )
        try:
            payload = resp.json()
        except ValueError as e:
            raise EngineParseError(f"Bing 返回非 JSON: {e}") from e
        return _parse_visual_search(payload, settings.IMAGE_SEARCH_MAX_RESULTS, self.name)


def _parse_visual_search(payload: Any, limit: int, source_name: str) -> list[SearchResult]:
    """解析 Bing Visual Search 响应，提取相似图片列表。"""
    if not isinstance(payload, dict):
        return []

    results: list[SearchResult] = []
    for tag in payload.get("tags", []):
        if not isinstance(tag, dict):
            continue
        for action in tag.get("actions", []):
            if not isinstance(action, dict):
                continue
            if action.get("actionType") not in _SIMILAR_ACTION_TYPES:
                continue
            for item in action.get("data", {}).get("value", []):
                if not isinstance(item, dict):
                    continue
                thumbnail = item.get("thumbnailUrl") or item.get("contentUrl") or ""
                source = (
                    item.get("hostPageUrl")
                    or item.get("webSearchUrl")
                    or item.get("contentUrl")
                    or ""
                )
                if not thumbnail and not source:
                    continue
                results.append(
                    SearchResult(
                        thumbnail_url=thumbnail,
                        source_url=source,
                        source_name=source_name,
                        title=item.get("name"),
                        score=_to_float(item.get("score")),
                    )
                )
                if len(results) >= limit:
                    return results
    return results


def _to_float(value: Any) -> float | None:
    """安全地把 Bing 的 score（可能是字符串数字）转为 float。"""
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None
