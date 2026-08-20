"""搜索源抽象基类。"""

from abc import ABC, abstractmethod
from typing import ClassVar

from .models import SearchResult


class SearchEngine(ABC):
    """搜索源统一接口。

    每个搜索源（Bing / 百度 / 未来 Google 等）实现本类并注册到门面，
    门面并发调用各源、按源分组返回结果，单源失败不影响其他源。
    """

    name: ClassVar[str] = ""  # 引擎标识，如 "bing" / "baidu"

    def __init__(self, timeout: float) -> None:
        """各引擎在构造时传入自己的独立超时秒数。"""
        self._timeout = timeout

    @property
    def timeout(self) -> float:
        """该源的独立超时秒数（门面用 asyncio.wait_for 包裹）。"""
        return self._timeout

    @abstractmethod
    def is_configured(self) -> bool:
        """是否已配置且可用；返回 False 时门面跳过该源（不调用 search）。"""

    @abstractmethod
    async def search(self, image_url: str) -> list[SearchResult]:
        """以图搜图，返回该源的相似图片列表。

        失败时抛 ImageSearchException 子类，由门面统一捕获降级。
        """
