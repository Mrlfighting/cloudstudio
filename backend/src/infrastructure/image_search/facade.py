"""以图搜图门面（Facade）：统一入口，并发调用各源，按源分组返回。"""

import asyncio
import threading
import time

from ..config.settings import get_settings
from ..logging import get_logger
from .base import SearchEngine
from .engines import build_engines
from .exceptions import ImageSearchException
from .http import AsyncHTTPClient
from .models import ImageSearchResponse, SourceSearchResult

logger = get_logger()


class ImageSearchFacade:
    """多源以图搜图门面。

    统一对外暴露 ``search(image_url)``，内部并发调用各搜索源，
    单源失败/超时降级为该源的 error 组，不影响其他源。
    """

    def __init__(
        self, engines: list[SearchEngine], http: AsyncHTTPClient | None = None
    ) -> None:
        self._engines = engines
        self._http = http

    async def search(self, image_url: str) -> ImageSearchResponse:
        """并发搜索所有源，按源分组返回结果。"""
        sources = await asyncio.gather(*(self._run(e, image_url) for e in self._engines))
        return ImageSearchResponse(query_url=image_url, sources=list(sources))

    async def _run(self, engine: SearchEngine, image_url: str) -> SourceSearchResult:
        """运行单个源，把跳过/异常统一转为 SourceSearchResult 降级，绝不向上抛。"""
        if not engine.is_configured():
            logger.info(
                f"以图搜图源 {engine.name} 未配置，跳过",
                extra={"source": engine.name, "reason": "skipped"},
            )
            return SourceSearchResult(source_name=engine.name, skipped=True)

        start = time.perf_counter()
        try:
            results = await asyncio.wait_for(engine.search(image_url), timeout=engine.timeout)
        except TimeoutError:
            logger.warning(
                f"以图搜图源 {engine.name} 超时",
                extra={"source": engine.name, "reason": "timeout"},
            )
            return SourceSearchResult(source_name=engine.name, error="timeout")
        except ImageSearchException as e:
            logger.warning(
                f"以图搜图源 {engine.name} 失败: {e}",
                extra={"source": engine.name, "reason": "engine_error"},
            )
            return SourceSearchResult(source_name=engine.name, error=str(e))
        except Exception as e:  # 兜底，绝不向上抛
            logger.warning(
                f"以图搜图源 {engine.name} 未预期错误: {e}",
                extra={"source": engine.name, "reason": "unexpected"},
            )
            return SourceSearchResult(source_name=engine.name, error=type(e).__name__)

        elapsed_ms = int((time.perf_counter() - start) * 1000)
        logger.info(
            f"以图搜图源 {engine.name} 完成",
            extra={"source": engine.name, "count": len(results), "elapsed_ms": elapsed_ms},
        )
        return SourceSearchResult(source_name=engine.name, results=results)

    async def close(self) -> None:
        """关闭门面持有的 HTTP 连接池。"""
        if self._http is not None:
            await self._http.close()


# 模块级单例（惰性构建）
_facade: ImageSearchFacade | None = None
_build_lock = threading.Lock()


def get_image_search_facade() -> ImageSearchFacade | None:
    """获取门面单例；未初始化时惰性构建（幂等），总开关关闭时返回 None。"""
    global _facade
    facade = _facade
    if facade is not None:
        return facade

    settings = get_settings()
    if not settings.IMAGE_SEARCH_ENABLED:
        return None

    with _build_lock:
        facade = _facade
        if facade is None:
            http = AsyncHTTPClient(
                default_timeout=settings.IMAGE_SEARCH_TIMEOUT,
                max_retries=settings.IMAGE_SEARCH_RETRY,
            )
            facade = ImageSearchFacade(engines=build_engines(settings, http), http=http)
            _facade = facade
    return facade


def set_image_search_facade(facade: ImageSearchFacade | None) -> None:
    """设置 / 清空门面单例（测试注入用）。"""
    global _facade
    _facade = facade
