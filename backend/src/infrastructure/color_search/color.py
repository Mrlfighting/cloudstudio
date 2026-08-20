"""颜色匹配纯算法：hex/int/rgb 转换 + 欧几里得距离。"""

import math


def parse_color(value: str) -> int:
    """解析颜色输入（FF0000 / #FF0000 / 0xFF0000）→ 0xRRGGBB 整数。

    非法输入抛 ValueError。
    """
    if not isinstance(value, str):
        raise ValueError("颜色值必须是字符串")
    s = value.strip().lstrip("#")
    if s.lower().startswith("0x"):
        s = s[2:]
    if len(s) != 6:
        raise ValueError(f"颜色格式错误，应为 6 位十六进制（如 FF0000），实际：{value}")
    try:
        return int(s, 16)
    except ValueError as e:
        raise ValueError(f"颜色格式错误，应为 6 位十六进制（如 FF0000），实际：{value}") from e


def hex_to_rgb(color: int) -> tuple[int, int, int]:
    """0xRRGGBB 整数 → (r, g, b)。"""
    return (color >> 16) & 0xFF, (color >> 8) & 0xFF, color & 0xFF


def int_to_hex(color: int) -> str:
    """整数 → "0xRRGGBB" 字符串（6 位补零，用于展示/调试）。"""
    return f"0x{color & 0xFFFFFF:06X}"


def color_distance(c1: int, c2: int) -> float:
    """两个 0xRRGGBB 颜色的欧几里得距离（越小越相近）。"""
    r1, g1, b1 = hex_to_rgb(c1)
    r2, g2, b2 = hex_to_rgb(c2)
    return math.sqrt((r1 - r2) ** 2 + (g1 - g2) ** 2 + (b1 - b2) ** 2)
