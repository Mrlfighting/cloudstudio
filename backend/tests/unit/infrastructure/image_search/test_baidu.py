"""百度引擎解析纯函数单元测试。"""

from src.infrastructure.image_search.engines.baidu import _extract_sign, _parse_similar_list


def test_extract_sign():
    payload = {"data": {"url": "https://graph.baidu.com/s?sign=abc123&x=1"}}
    assert _extract_sign(payload) == "abc123"


def test_extract_sign_missing():
    assert _extract_sign({"data": {}}) is None
    assert _extract_sign({"data": {"url": "https://graph.baidu.com/s"}}) is None
    assert _extract_sign("not-a-dict") is None
    assert _extract_sign(None) is None


def test_parse_similar_list_maps_fields():
    payload = {
        "data": {
            "list": [
                {"thumbUrl": "http://t1", "fromUrl": "http://s1", "fromUrlHost": "host1"},
                {"thumbUrl": "http://t2", "fromUrl": "http://s2"},
            ]
        }
    }
    results = _parse_similar_list(payload, 10, "baidu")
    assert len(results) == 2
    assert results[0].thumbnail_url == "http://t1"
    assert results[0].source_url == "http://s1"
    assert results[0].source_name == "baidu"
    assert results[0].title == "host1"
    assert results[0].score is None


def test_parse_similar_list_limits_results():
    items = [{"thumbUrl": f"t{i}", "fromUrl": f"s{i}"} for i in range(10)]
    payload = {"data": {"list": items}}
    assert len(_parse_similar_list(payload, 3, "baidu")) == 3


def test_parse_similar_list_empty_or_malformed():
    assert _parse_similar_list({}, 10, "baidu") == []
    assert _parse_similar_list({"data": {}}, 10, "baidu") == []
    assert _parse_similar_list({"data": {"list": []}}, 10, "baidu") == []
    assert _parse_similar_list(None, 10, "baidu") == []


def test_parse_similar_list_skips_items_without_urls():
    payload = {"data": {"list": [{"foo": "bar"}, {"thumbUrl": "http://t1", "fromUrl": "http://s1"}]}}
    results = _parse_similar_list(payload, 10, "baidu")
    assert len(results) == 1
    assert results[0].thumbnail_url == "http://t1"
