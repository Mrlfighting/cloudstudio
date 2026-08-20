"""ImageSearchFacade 并发/降级单元测试。"""

import asyncio

import pytest

from src.infrastructure.image_search.base import SearchEngine
from src.infrastructure.image_search.exceptions import EngineRequestError
from src.infrastructure.image_search.facade import ImageSearchFacade
from src.infrastructure.image_search.models import SearchResult


class FakeEngine(SearchEngine):
    """可控行为的假引擎：可配置/可抛错/可延迟。"""

    name = "fake"

    def __init__(
        self,
        *,
        configured: bool = True,
        results: list[SearchResult] | None = None,
        error: Exception | None = None,
        timeout: float = 1.0,
        delay: float = 0.0,
    ) -> None:
        super().__init__(timeout=timeout)
        self._configured = configured
        self._results = results or []
        self._error = error
        self._delay = delay
        self.search_called = False

    def is_configured(self) -> bool:
        return self._configured

    async def search(self, image_url: str) -> list[SearchResult]:
        self.search_called = True
        if self._delay:
            await asyncio.sleep(self._delay)
        if self._error:
            raise self._error
        return self._results


def _result(source_name: str, i: int) -> SearchResult:
    return SearchResult(thumbnail_url=f"t{i}", source_url=f"s{i}", source_name=source_name)


@pytest.mark.asyncio
async def test_all_success_grouped_by_source():
    a = FakeEngine(results=[_result("a", 1)])
    a.name = "a"
    b = FakeEngine(results=[_result("b", 1), _result("b", 2)])
    b.name = "b"

    resp = await ImageSearchFacade([a, b]).search("http://img")

    by_name = {s.source_name: s for s in resp.sources}
    assert set(by_name) == {"a", "b"}
    assert len(by_name["a"].results) == 1
    assert len(by_name["b"].results) == 2
    assert all(s.error is None and s.skipped is False for s in resp.sources)


@pytest.mark.asyncio
async def test_single_engine_failure_does_not_affect_others():
    bad = FakeEngine(error=EngineRequestError("boom"))
    bad.name = "bad"
    good = FakeEngine(results=[_result("good", 1)])
    good.name = "good"

    resp = await ImageSearchFacade([bad, good]).search("http://img")

    by_name = {s.source_name: s for s in resp.sources}
    assert by_name["bad"].error is not None
    assert by_name["bad"].results == []
    assert by_name["good"].error is None
    assert len(by_name["good"].results) == 1


@pytest.mark.asyncio
async def test_unconfigured_engine_skipped_without_search():
    engine = FakeEngine(configured=False)
    engine.name = "x"

    resp = await ImageSearchFacade([engine]).search("http://img")

    assert resp.sources[0].skipped is True
    assert resp.sources[0].results == []
    assert engine.search_called is False


@pytest.mark.asyncio
async def test_slow_engine_times_out():
    slow = FakeEngine(timeout=0.01, delay=0.1)
    slow.name = "slow"
    fast = FakeEngine(results=[_result("fast", 1)])
    fast.name = "fast"

    resp = await ImageSearchFacade([slow, fast]).search("http://img")

    by_name = {s.source_name: s for s in resp.sources}
    assert by_name["slow"].error == "timeout"
    assert len(by_name["fast"].results) == 1


@pytest.mark.asyncio
async def test_unexpected_exception_captured():
    engine = FakeEngine(error=RuntimeError("unexpected"))
    engine.name = "x"

    resp = await ImageSearchFacade([engine]).search("http://img")

    assert resp.sources[0].error == "RuntimeError"


@pytest.mark.asyncio
async def test_empty_engines():
    resp = await ImageSearchFacade([]).search("http://img")
    assert resp.sources == []
    assert resp.query_url == "http://img"
