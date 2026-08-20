"""Bing 引擎单元测试（is_configured + 解析纯函数）。"""

from types import SimpleNamespace

from src.infrastructure.image_search.engines.bing import (
    BingVisualSearchEngine,
    _parse_visual_search,
    _to_float,
)


def _settings(**kwargs):
    defaults = {
        "IMAGE_SEARCH_BING_ENABLED": False,
        "IMAGE_SEARCH_BING_API_KEY": "",
        "IMAGE_SEARCH_BING_TIMEOUT": 15.0,
    }
    defaults.update(kwargs)
    return SimpleNamespace(**defaults)


def test_is_configured_false_without_key():
    engine = BingVisualSearchEngine(_settings(), http=None)
    assert engine.is_configured() is False


def test_is_configured_false_when_disabled():
    engine = BingVisualSearchEngine(
        _settings(IMAGE_SEARCH_BING_ENABLED=False, IMAGE_SEARCH_BING_API_KEY="k"),
        http=None,
    )
    assert engine.is_configured() is False


def test_is_configured_true_with_key_and_enabled():
    engine = BingVisualSearchEngine(
        _settings(IMAGE_SEARCH_BING_ENABLED=True, IMAGE_SEARCH_BING_API_KEY="k"),
        http=None,
    )
    assert engine.is_configured() is True


def test_parse_visual_search_maps_fields():
    payload = {
        "tags": [
            {
                "actions": [
                    {
                        "actionType": "VisualSearch",
                        "data": {
                            "value": [
                                {
                                    "thumbnailUrl": "http://t1",
                                    "hostPageUrl": "http://s1",
                                    "name": "n1",
                                    "score": 0.9,
                                }
                            ]
                        },
                    }
                ]
            }
        ]
    }
    results = _parse_visual_search(payload, 10, "bing")
    assert len(results) == 1
    assert results[0].thumbnail_url == "http://t1"
    assert results[0].source_url == "http://s1"
    assert results[0].title == "n1"
    assert results[0].score == 0.9
    assert results[0].source_name == "bing"


def test_parse_visual_search_skips_non_similar_actions():
    payload = {
        "tags": [
            {
                "actions": [
                    {"actionType": "PagesIncluding", "data": {"value": [{"thumbnailUrl": "x"}]}}
                ]
            }
        ]
    }
    assert _parse_visual_search(payload, 10, "bing") == []


def test_parse_visual_search_limits_results():
    items = [{"thumbnailUrl": f"t{i}", "hostPageUrl": f"s{i}"} for i in range(10)]
    payload = {"tags": [{"actions": [{"actionType": "VisualSearch", "data": {"value": items}}]}]}
    assert len(_parse_visual_search(payload, 3, "bing")) == 3


def test_parse_visual_search_not_dict():
    assert _parse_visual_search(None, 10, "bing") == []
    assert _parse_visual_search([], 10, "bing") == []


def test_to_float():
    assert _to_float("0.5") == 0.5
    assert _to_float(0.5) == 0.5
    assert _to_float(None) is None
    assert _to_float("abc") is None
