"""ImageSearchSettings 默认值测试。"""

from src.infrastructure.config.settings import get_settings


def test_image_search_defaults():
    s = get_settings()
    assert s.IMAGE_SEARCH_ENABLED is True
    assert s.IMAGE_SEARCH_BAIDU_ENABLED is True
    assert s.IMAGE_SEARCH_BING_ENABLED is False
    assert s.IMAGE_SEARCH_BING_API_KEY == ""
    assert s.IMAGE_SEARCH_TIMEOUT > 0
    assert s.IMAGE_SEARCH_BAIDU_TIMEOUT > 0
    assert s.IMAGE_SEARCH_MAX_RESULTS > 0
