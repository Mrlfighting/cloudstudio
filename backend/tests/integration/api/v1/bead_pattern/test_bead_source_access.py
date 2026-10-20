"""真实数据库与现有私有空间查询服务的隔离回归，原图传输用 mock。"""

from unittest.mock import AsyncMock

import pytest

from src.interfaces.main import app
from src.modules.bead_pattern.routes import get_source_service
from src.modules.pictures.models import Picture
from src.modules.space.models import Space

pytestmark = pytest.mark.asyncio


async def test_anonymous_source_denied(client):
    """匿名请求取图仍需登录。"""
    response = await client.get("/api/v1/bead-patterns/sources/private/1")
    assert response.status_code == 401


@pytest.mark.parametrize(
    "kind,expected",
    [("own", 200), ("other", 404), ("public", 404), ("team", 404), ("deleted", 404), ("banned", 403)],
)
async def test_private_source_boundaries(auth_client, db_session, test_user, test_user_2, kind, expected):
    """本人之外的图片不会触发下载，成功也不更新图库计数。"""
    own = Space(name="本人空间", user_id=test_user["id"], total_count=1, total_size=123)
    other = Space(name="他人空间", user_id=test_user_2["id"])
    team = Space(name="本人团队", user_id=test_user["id"], space_type=1)
    if kind == "banned":
        own.status = "banned"
    db_session.add_all([own, other, team])
    await db_session.flush()
    space_id = other.id if kind == "other" else team.id if kind == "team" else None if kind == "public" else own.id
    picture = Picture(
        url="https://example.cos.ap-guangzhou.myqcloud.com/pictures/test.png", name="拼豆原图",
        introduction=None, category="风景", pic_size=123, pic_width=10, pic_height=10,
        pic_scale=1, pic_format="PNG", color_mode="RGB", primary_color=None,
        user_id=test_user["id"], space_id=space_id, status="approved",
    )
    if kind == "deleted":
        picture.is_deleted = True
    db_session.add(picture)
    await db_session.commit()
    service = AsyncMock()
    service.read.return_value = (b"verified image", "image/png")
    app.dependency_overrides[get_source_service] = lambda: service
    auth_client.headers["X-Bead-Owner"] = str(test_user["id"])
    try:
        response = await auth_client.get(f"/api/v1/bead-patterns/sources/private/{picture.id}")
        assert response.status_code == expected, response.text
        if expected == 200:
            assert response.content == b"verified image"
            assert "private" in response.headers["cache-control"]
            assert "no-store" in response.headers["cache-control"]
            assert response.headers["content-type"] == "image/png"
            service.read.assert_awaited_once()
        else:
            service.read.assert_not_awaited()
        await db_session.refresh(own)
        await db_session.refresh(picture)
        assert own.total_count == 1 and own.total_size == 123
        assert picture.download_count == 0
    finally:
        app.dependency_overrides.pop(get_source_service, None)
