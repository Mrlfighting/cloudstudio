"""图片模块二级缓存：key 构造器与 TTL 常量。"""

import hashlib

# TTL 常量（秒）
DETAIL_TTL = 300
LIST_TIME_TTL = 300
LIST_POPULARITY_TTL = 30

LIST_KEY_PREFIX = "pic:list"
DETAIL_KEY_PREFIX = "pic:detail"


def _kw8(keyword: str | None) -> str:
    """关键词压缩：md5 取前 8 位，无关键词用 '-'。"""
    if not keyword:
        return "-"
    return hashlib.md5(keyword.encode("utf-8")).hexdigest()[:8]


def build_detail_key(picture_id: int) -> str:
    """详情缓存 key：pic:detail:{id}。"""
    return f"{DETAIL_KEY_PREFIX}:{picture_id}"


def build_list_key(
    scope: str,
    category: str | None,
    keyword: str | None,
    sort: str,
    page: int,
    items_per_page: int,
) -> str:
    """列表缓存 key：pic:list:{scope}:{category}:{sort}:{page}:{size}:{kw8}。"""
    cat = category or "all"
    return f"{LIST_KEY_PREFIX}:{scope}:{cat}:{sort}:{page}:{items_per_page}:{_kw8(keyword)}"


def list_ttl(sort: str) -> int:
    """列表 TTL：popularity 排序短 TTL，time 排序长 TTL。"""
    return LIST_POPULARITY_TTL if sort == "popularity" else LIST_TIME_TTL
