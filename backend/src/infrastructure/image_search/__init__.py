"""以图搜图多源聚合工具包（基础设施层）。

对外提供门面、数据模型与异常，与主业务代码解耦。
"""

from .base import SearchEngine
from .exceptions import (
    EngineParseError,
    EngineRequestError,
    EngineTimeoutError,
    ImageSearchException,
)
from .facade import (
    ImageSearchFacade,
    get_image_search_facade,
    search_image,
    set_image_search_facade,
)
from .models import ImageSearchResponse, SearchResult, SourceSearchResult

__all__ = [
    "SearchEngine",
    "ImageSearchFacade",
    "ImageSearchResponse",
    "SearchResult",
    "SourceSearchResult",
    "ImageSearchException",
    "EngineRequestError",
    "EngineTimeoutError",
    "EngineParseError",
    "get_image_search_facade",
    "set_image_search_facade",
    "search_image",
]
