"""颜色匹配纯算法单元测试。"""

import pytest

from src.infrastructure.color_search.color import (
    color_distance,
    hex_to_rgb,
    int_to_hex,
    parse_color,
)


def test_parse_color_no_prefix():
    assert parse_color("FF0000") == 0xFF0000


def test_parse_color_hash_prefix():
    assert parse_color("#00FF00") == 0x00FF00


def test_parse_color_0x_prefix():
    assert parse_color("0x0000FF") == 0x0000FF


def test_parse_color_invalid():
    with pytest.raises(ValueError):
        parse_color("FF00")  # 长度不对
    with pytest.raises(ValueError):
        parse_color("GGGGGG")  # 非十六进制
    with pytest.raises(ValueError):
        parse_color("")  # 空串


def test_hex_to_rgb():
    assert hex_to_rgb(0xFF0000) == (255, 0, 0)
    assert hex_to_rgb(0x00FF00) == (0, 255, 0)
    assert hex_to_rgb(0x0000FF) == (0, 0, 255)
    assert hex_to_rgb(0x000000) == (0, 0, 0)


def test_int_to_hex():
    assert int_to_hex(0x736246) == "0x736246"
    assert int_to_hex(0xFF0000) == "0xFF0000"
    assert int_to_hex(0x0000FF) == "0x0000FF"


def test_color_distance_same_is_zero():
    assert color_distance(0xFF0000, 0xFF0000) == 0.0


def test_color_distance_positive_and_ordered():
    assert color_distance(0x000000, 0xFFFFFF) > 0
    # 红色更接近深红而非黑色
    assert color_distance(0xFF0000, 0xEE0000) < color_distance(0xFF0000, 0x000000)
