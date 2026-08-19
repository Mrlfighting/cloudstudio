"""图片模块缓存 key 构造器单元测试。"""

from src.modules.pictures.cache import build_detail_key, build_list_key, list_ttl


def test_build_detail_key():
    assert build_detail_key(123) == "pic:detail:123"


def test_build_list_key_keyword_compressed():
    key = build_list_key("public", None, "a-very-long-keyword", "time", 1, 20)
    assert key.startswith("pic:list:public:all:time:1:20:")
    # 关键词被 md5 压缩为 8 位 hex
    assert len(key.rsplit(":", 1)[-1]) == 8


def test_build_list_key_no_keyword():
    assert build_list_key("public", "scenery", None, "popularity", 2, 10) == (
        "pic:list:public:scenery:popularity:2:10:-"
    )


def test_list_ttl_differentiated():
    assert list_ttl("popularity") == 30
    assert list_ttl("time") == 300
