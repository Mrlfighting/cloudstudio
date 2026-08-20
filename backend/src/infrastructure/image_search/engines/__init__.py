"""搜索源工厂：登记各搜索引擎，供门面并发调用。"""

from ...config.settings import Settings
from ..base import SearchEngine
from ..http import AsyncHTTPClient
from .baidu import BaiduImageSearchEngine
from .bing import BingVisualSearchEngine

__all__ = ["BaiduImageSearchEngine", "BingVisualSearchEngine", "build_engines"]


def build_engines(settings: Settings, http: AsyncHTTPClient) -> list[SearchEngine]:
    """构建已注册的搜索源列表（新增源在此登记，如未来 Google/Yandex）。"""
    return [
        BaiduImageSearchEngine(settings, http),
        BingVisualSearchEngine(settings, http),
    ]
