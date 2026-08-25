"""图库分析服务单元测试（真实 Postgres 聚合，testcontainers）。"""

import pytest
from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.analytics.service import AnalyticsService
from src.modules.pictures.crud import crud_pictures
from src.modules.pictures.models import Picture
from src.modules.pictures.schemas import PictureCreateInternal, PictureRead
from src.modules.space.crud import crud_spaces
from src.modules.space.service import SpaceService


@pytest.fixture
def analytics_service() -> AnalyticsService:
    return AnalyticsService()


async def _create_picture(
    db: AsyncSession,
    *,
    name: str,
    user_id: int,
    category: str | None = None,
    tags: list[str] | None = None,
    pic_size: int | None = None,
    space_id: int | None = None,
    status: str = "approved",
    download_count: int = 0,
) -> dict:
    """创建图片（公共图库默认 space_id=None，status=approved）。"""
    internal = PictureCreateInternal(
        url=f"https://example.com/{name}.png",
        name=name,
        category=category,
        tags=tags or [],
        pic_size=pic_size,
        user_id=user_id,
        space_id=space_id,
        status=status,
    )
    pic = await crud_pictures.create(db, object=internal, schema_to_select=PictureRead)
    if download_count:
        await db.execute(
            update(Picture).where(Picture.id == pic["id"]).values(download_count=download_count)
        )
        await db.commit()
    return pic


async def _create_space(db: AsyncSession, name: str, user: dict) -> dict:
    return await SpaceService().create(db, name, user)


@pytest.mark.asyncio
async def test_gallery_overview(analytics_service, db_session, test_user):
    await _create_picture(db_session, name="a", user_id=test_user["id"], pic_size=100, download_count=3)
    await _create_picture(db_session, name="b", user_id=test_user["id"], pic_size=50, download_count=2)

    result = await analytics_service.get_gallery_overview(db_session)

    assert result["total_pictures"] == 2
    assert result["total_size"] == 150
    assert result["total_downloads"] == 5


@pytest.mark.asyncio
async def test_gallery_overview_ignores_non_approved(analytics_service, db_session, test_user):
    # pending/rejected 不计入公共图库统计
    await _create_picture(db_session, name="approved", user_id=test_user["id"], status="approved")
    await _create_picture(db_session, name="pending", user_id=test_user["id"], status="pending")

    result = await analytics_service.get_gallery_overview(db_session)

    assert result["total_pictures"] == 1


@pytest.mark.asyncio
async def test_gallery_category(analytics_service, db_session, test_user):
    await _create_picture(db_session, name="a", user_id=test_user["id"], category="风景")
    await _create_picture(db_session, name="b", user_id=test_user["id"], category="风景")
    await _create_picture(db_session, name="c", user_id=test_user["id"], category="人物")

    result = await analytics_service.get_gallery_category(db_session)

    by_cat = {r["category"]: r for r in result}
    assert by_cat["风景"]["count"] == 2
    assert by_cat["人物"]["count"] == 1
    assert abs(by_cat["风景"]["ratio"] - round(2 / 3, 4)) < 1e-6


@pytest.mark.asyncio
async def test_gallery_tags(analytics_service, db_session, test_user):
    await _create_picture(db_session, name="a", user_id=test_user["id"], tags=["自然", "山水"])
    await _create_picture(db_session, name="b", user_id=test_user["id"], tags=["自然"])

    result = await analytics_service.get_gallery_tags(db_session, 20)

    by_tag = {r["tag"]: r["count"] for r in result}
    assert by_tag["自然"] == 2
    assert by_tag["山水"] == 1


@pytest.mark.asyncio
async def test_gallery_top_uploaders(analytics_service, db_session, test_user, test_user_2):
    await _create_picture(db_session, name="a1", user_id=test_user["id"])
    await _create_picture(db_session, name="a2", user_id=test_user["id"])
    await _create_picture(db_session, name="b1", user_id=test_user_2["id"])

    result = await analytics_service.get_gallery_top_uploaders(db_session, 10)

    assert result[0]["user_id"] == test_user["id"]
    assert result[0]["count"] == 2
    assert result[1]["user_id"] == test_user_2["id"]
    assert result[1]["count"] == 1


@pytest.mark.asyncio
async def test_gallery_trend(analytics_service, db_session, test_user):
    await _create_picture(db_session, name="a", user_id=test_user["id"])
    await _create_picture(db_session, name="b", user_id=test_user["id"])

    trend = await analytics_service.get_gallery_trend(db_session, "day")

    assert sum(r["count"] for r in trend) == 2


@pytest.mark.asyncio
async def test_my_overview_no_space(analytics_service, db_session, test_user):
    result = await analytics_service.get_my_overview(db_session, test_user["id"])

    assert result["space_id"] is None
    assert result["picture_count"] == 0
    assert result["count_usage"] == 0.0


@pytest.mark.asyncio
async def test_my_overview_with_space(analytics_service, db_session, test_user):
    space = await _create_space(db_session, "我的空间", test_user)
    await _create_picture(db_session, name="a", user_id=test_user["id"], pic_size=100, space_id=space["id"])
    await _create_picture(db_session, name="b", user_id=test_user["id"], pic_size=50, space_id=space["id"])
    # 模拟上传后的配额计数（空间模块 upload 会维护 total_count/total_size）
    await crud_spaces.update(db_session, object={"total_count": 2, "total_size": 150}, id=space["id"])

    result = await analytics_service.get_my_overview(db_session, test_user["id"])

    assert result["space_id"] == space["id"]
    assert result["picture_count"] == 2
    assert result["max_count"] == space["max_count"]
    assert result["count_usage"] == round(2 / space["max_count"], 4)


@pytest.mark.asyncio
async def test_my_top_pictures(analytics_service, db_session, test_user):
    space = await _create_space(db_session, "我的空间", test_user)
    await _create_picture(db_session, name="hot", user_id=test_user["id"], space_id=space["id"], download_count=10)
    await _create_picture(db_session, name="cold", user_id=test_user["id"], space_id=space["id"], download_count=1)

    result = await analytics_service.get_my_top_pictures(db_session, test_user["id"], 10)

    assert result[0]["name"] == "hot"
    assert result[0]["download_count"] == 10


@pytest.mark.asyncio
async def test_my_isolation(analytics_service, db_session, test_user, test_user_2):
    """用户 2 看不到用户 1 空间内的图片分析。"""
    space1 = await _create_space(db_session, "用户1空间", test_user)
    space2 = await _create_space(db_session, "用户2空间", test_user_2)
    await _create_picture(db_session, name="u1", user_id=test_user["id"], space_id=space1["id"])
    await _create_picture(db_session, name="u2", user_id=test_user_2["id"], space_id=space2["id"])

    result1 = await analytics_service.get_my_category(db_session, test_user["id"])
    result2 = await analytics_service.get_my_category(db_session, test_user_2["id"])

    assert len(result1) == 1 and result1[0]["category"] == "未分类"
    assert len(result2) == 1
    # 用户 2 的统计不含用户 1 的图片（两张图 category 均为 None，数量各自为 1）
    assert result1[0]["count"] == 1
    assert result2[0]["count"] == 1
