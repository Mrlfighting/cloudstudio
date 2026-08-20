"""图片服务单元测试：纯函数（标签解析） + 以图搜图编排。"""

from unittest.mock import AsyncMock

import pytest

from src.infrastructure.image_search.models import ImageSearchResponse
from src.modules.common.exceptions import ValidationError
from src.modules.pictures.service import PictureService, _parse_tags


def test_parse_tags_valid():
    assert _parse_tags('["风景", "自然"]') == ["风景", "自然"]


def test_parse_tags_empty():
    assert _parse_tags("") == []
    assert _parse_tags("[]") == []


def test_parse_tags_invalid_json():
    with pytest.raises(ValidationError):
        _parse_tags("not-json")


def test_parse_tags_not_string_list():
    with pytest.raises(ValidationError):
        _parse_tags('"just-a-string"')
    with pytest.raises(ValidationError):
        _parse_tags("[1, 2, 3]")


@pytest.mark.asyncio
async def test_search_similar_delegates_to_search_image(monkeypatch):
    service = PictureService()

    async def fake_get(db, picture_id, require_approved=False):
        return {"id": picture_id, "url": "http://img/cos.jpg"}

    monkeypatch.setattr(service, "get", fake_get)
    search_mock = AsyncMock(
        return_value=ImageSearchResponse(query_url="http://img/cos.jpg", sources=[])
    )
    monkeypatch.setattr("src.modules.pictures.service.search_image", search_mock)

    result = await service.search_similar(db=None, picture_id=1)

    search_mock.assert_awaited_once_with("http://img/cos.jpg")
    assert result.query_url == "http://img/cos.jpg"
