"""空间服务单元测试。"""

import asyncio
from unittest.mock import AsyncMock

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from src.infrastructure.image_search.models import ImageSearchResponse
from src.modules.common.exceptions import (
    PictureNotFoundError,
    SpaceExistsError,
    SpaceNotFoundError,
    ValidationError,
)
from src.modules.pictures.crud import crud_pictures
from src.modules.pictures.schemas import PictureCreateInternal, PictureRead
from src.modules.space.crud import crud_spaces
from src.modules.space.enums import SpaceLevel, SpaceStatus
from src.modules.space.service import SpaceService


@pytest.fixture
def space_service() -> SpaceService:
    return SpaceService()


@pytest.mark.asyncio
async def test_create_space(space_service: SpaceService, db_session: AsyncSession, test_user: dict):
    created = await space_service.create(db_session, "我的空间", test_user)
    assert created["name"] == "我的空间"
    assert created["space_level"] == SpaceLevel.NORMAL
    assert created["max_size"] == 500 * 1024 * 1024
    assert created["max_count"] == 100
    assert created["total_size"] == 0
    assert created["total_count"] == 0
    assert created["status"] == SpaceStatus.ACTIVE.value
    assert created["user_id"] == test_user["id"]


@pytest.mark.asyncio
async def test_create_duplicate_raises(space_service: SpaceService, db_session: AsyncSession, test_user: dict):
    await space_service.create(db_session, "空间A", test_user)
    with pytest.raises(SpaceExistsError):
        await space_service.create(db_session, "空间B", test_user)


@pytest.mark.asyncio
async def test_create_concurrent_only_one_succeeds(space_service: SpaceService, db_session: AsyncSession, test_user: dict):
    """并发创建：本地锁保证只有一个成功。"""

    async def _try_create() -> bool:
        try:
            await space_service.create(db_session, "并发空间", test_user)
            return True
        except SpaceExistsError:
            return False

    results = await asyncio.gather(*(_try_create() for _ in range(5)))
    assert sum(results) == 1


@pytest.mark.asyncio
async def test_get_my_not_found(space_service: SpaceService, db_session: AsyncSession, test_user: dict):
    with pytest.raises(SpaceNotFoundError):
        await space_service.get_my(db_session, test_user)


@pytest.mark.asyncio
async def test_get_my_info(space_service: SpaceService, db_session: AsyncSession, test_user: dict):
    await space_service.create(db_session, "我的空间", test_user)
    info = await space_service.get_my(db_session, test_user)
    assert info["name"] == "我的空间"
    assert info["remaining_size"] == info["max_size"]
    assert info["remaining_count"] == info["max_count"]


@pytest.mark.asyncio
async def test_upgrade_level(space_service: SpaceService, db_session: AsyncSession, test_user: dict):
    await space_service.create(db_session, "我的空间", test_user)
    info = await space_service.change_level(db_session, test_user, SpaceLevel.PRO)
    assert info["space_level"] == SpaceLevel.PRO
    assert info["max_size"] == 5 * 1024 * 1024 * 1024
    assert info["max_count"] == 1000


@pytest.mark.asyncio
async def test_downgrade_over_limit_rejected(space_service: SpaceService, db_session: AsyncSession, test_user: dict):
    await space_service.create(db_session, "我的空间", test_user)
    await space_service.change_level(db_session, test_user, SpaceLevel.PRO)
    info = await space_service.get_my(db_session, test_user)
    # 用量调到 150 张，超过普通版上限 100
    await crud_spaces.update(db_session, object={"total_count": 150}, id=info["id"])
    with pytest.raises(ValidationError):
        await space_service.change_level(db_session, test_user, SpaceLevel.NORMAL)


@pytest.mark.asyncio
async def test_ban_and_unban(space_service: SpaceService, db_session: AsyncSession, test_user: dict):
    created = await space_service.create(db_session, "我的空间", test_user)
    banned = await space_service.set_ban(db_session, created["id"], banned=True)
    assert banned["status"] == SpaceStatus.BANNED.value
    unbanned = await space_service.set_ban(db_session, created["id"], banned=False)
    assert unbanned["status"] == SpaceStatus.ACTIVE.value


@pytest.mark.asyncio
async def test_delete_admin_soft_deletes(space_service: SpaceService, db_session: AsyncSession, test_user: dict):
    created = await space_service.create(db_session, "我的空间", test_user)
    await space_service.delete_admin(db_session, created["id"])
    with pytest.raises(SpaceNotFoundError):
        await space_service.get_admin(db_session, created["id"])


@pytest.mark.asyncio
async def test_list_admin(space_service: SpaceService, db_session: AsyncSession, test_user: dict):
    await space_service.create(db_session, "空间A", test_user)
    result = await space_service.list_admin(db_session)
    assert result["total_count"] == 1
    assert result["data"][0]["name"] == "空间A"


@pytest.mark.asyncio
async def test_space_picture_isolation(
    space_service: SpaceService, db_session: AsyncSession, test_user: dict, test_user_2: dict
):
    """用户 2 无法访问用户 1 空间的图片。"""
    space1 = await space_service.create(db_session, "用户1空间", test_user)
    await space_service.create(db_session, "用户2空间", test_user_2)

    internal = PictureCreateInternal(
        url="https://example.com/x.png",
        name="用户1图片",
        user_id=test_user["id"],
        status="approved",
        space_id=space1["id"],
    )
    pic = await crud_pictures.create(db_session, object=internal, schema_to_select=PictureRead)

    with pytest.raises(PictureNotFoundError):
        await space_service.get_picture(db_session, test_user_2, pic["id"])


@pytest.mark.asyncio
async def test_search_similar_delegates_to_search_image(space_service: SpaceService, monkeypatch):
    async def fake_get_picture(db, current_user, picture_id):
        return {"id": picture_id, "url": "http://img/space.jpg", "space_id": 1}

    monkeypatch.setattr(space_service, "get_picture", fake_get_picture)
    search_mock = AsyncMock(
        return_value=ImageSearchResponse(query_url="http://img/space.jpg", sources=[])
    )
    monkeypatch.setattr("src.modules.space.service.search_image", search_mock)

    result = await space_service.search_similar(db=None, current_user={"id": 1}, picture_id=1)

    search_mock.assert_awaited_once_with("http://img/space.jpg")
    assert result.query_url == "http://img/space.jpg"


@pytest.mark.asyncio
async def test_search_by_color_sorted(
    space_service: SpaceService, db_session: AsyncSession, test_user: dict
):
    space = await space_service.create(db_session, "颜色空间", test_user)
    for i, color in enumerate([0xFF0000, 0xEE0000, 0x0000FF]):
        internal = PictureCreateInternal(
            url=f"https://example.com/{i}.png",
            name=f"图{i}",
            user_id=test_user["id"],
            status="approved",
            space_id=space["id"],
            primary_color=color,
        )
        await crud_pictures.create(db_session, object=internal, schema_to_select=PictureRead)

    result = await space_service.search_by_color(db_session, test_user, "FF0000", 10)

    assert len(result) == 3
    assert result[0].primary_color == 0xFF0000
    assert result[0].color_distance == 0.0
    distances = [r.color_distance for r in result]
    assert distances == sorted(distances)


@pytest.mark.asyncio
async def test_search_by_color_invalid_color(
    space_service: SpaceService, db_session: AsyncSession, test_user: dict
):
    await space_service.create(db_session, "颜色空间", test_user)
    with pytest.raises(ValidationError):
        await space_service.search_by_color(db_session, test_user, "INVALID", 10)
