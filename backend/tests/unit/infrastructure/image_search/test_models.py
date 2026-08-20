"""image_search 数据模型单元测试。"""

from src.infrastructure.image_search.models import (
    ImageSearchResponse,
    SearchResult,
    SourceSearchResult,
)


def test_search_result_defaults():
    r = SearchResult(thumbnail_url="t", source_url="s", source_name="bing")
    assert r.title is None
    assert r.score is None


def test_source_result_defaults():
    s = SourceSearchResult(source_name="bing")
    assert s.results == []
    assert s.error is None
    assert s.skipped is False


def test_image_search_response_assembly():
    resp = ImageSearchResponse(
        query_url="http://img",
        sources=[SourceSearchResult(source_name="bing", skipped=True)],
    )
    assert resp.query_url == "http://img"
    assert len(resp.sources) == 1
    assert resp.sources[0].skipped is True
