"""图片服务单元测试：纯函数（标签解析）。"""

import pytest

from src.modules.common.exceptions import ValidationError
from src.modules.pictures.service import _parse_tags


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
