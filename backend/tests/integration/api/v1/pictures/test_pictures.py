"""图片列表/详情/下载/管理/编辑/审核/删除 集成测试。"""

import logging
import uuid

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.pictures.models import Picture

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

pytestmark = pytest.mark.asyncio


async def _create_picture(
    db: AsyncSession,
    user_id: int,
    *,
    status: str = "approved",
    name: str = "测试图片",
    category: str = "风景",
    tags: list[str] | None = None,
    download_count: int = 0,
    introduction: str = "简介",
) -> Picture:
    """直接向测试库插入一条图片记录。"""
    pic = Picture(
        url=f"https://example.com/pics/{uuid.uuid4().hex}.jpg",
        name=name,
        introduction=introduction,
        category=category,
        tags=tags or ["风景"],
        pic_size=1024,
        pic_width=100,
        pic_height=50,
        pic_scale=2.0,
        pic_format="JPEG",
        color_mode="RGB",
        user_id=user_id,
        status=status,
        download_count=download_count,
    )
    db.add(pic)
    await db.commit()
    await db.refresh(pic)
    return pic


async def test_list_shows_only_approved(
    client: AsyncClient, auth_client: AsyncClient, db_session: AsyncSession, test_user: dict
):
    """用户列表仅返回已发布图片。"""
    await _create_picture(db_session, test_user["id"], status="approved", name="已发布")
    await _create_picture(db_session, test_user["id"], status="pending", name="待审核")
    await _create_picture(db_session, test_user["id"], status="rejected", name="已拒绝")

    response = await auth_client.get("/api/v1/pictures/")
    assert response.status_code == 200
    data = response.json()
    names = {item["name"] for item in data["data"]}
    assert "已发布" in names
    assert "待审核" not in names
    assert "已拒绝" not in names


async def test_list_requires_auth(client: AsyncClient):
    """未登录访问列表 → 401。"""
    response = await client.get("/api/v1/pictures/")
    assert response.status_code == 401


async def test_list_category_and_keyword_filter(
    auth_client: AsyncClient, db_session: AsyncSession, test_user: dict
):
    """分类筛选 + 关键词（名称/标签）搜索。"""
    await _create_picture(db_session, test_user["id"], name="黄山云海", category="风景", tags=["自然", "山"])
    await _create_picture(db_session, test_user["id"], name="猫咪", category="动物", tags=["宠物"])

    # 分类筛选
    r1 = await auth_client.get("/api/v1/pictures/", params={"category": "风景"})
    assert {i["name"] for i in r1.json()["data"]} == {"黄山云海"}

    # 关键词命中名称
    r2 = await auth_client.get("/api/v1/pictures/", params={"keyword": "黄山"})
    assert {i["name"] for i in r2.json()["data"]} == {"黄山云海"}

    # 关键词命中标签
    r3 = await auth_client.get("/api/v1/pictures/", params={"keyword": "宠物"})
    assert {i["name"] for i in r3.json()["data"]} == {"猫咪"}


async def test_list_sort_popularity(
    auth_client: AsyncClient, db_session: AsyncSession, test_user: dict
):
    """按热度（下载次数）排序。"""
    await _create_picture(db_session, test_user["id"], name="低热度", download_count=1)
    await _create_picture(db_session, test_user["id"], name="高热度", download_count=99)

    response = await auth_client.get("/api/v1/pictures/", params={"sort": "popularity"})
    names = [i["name"] for i in response.json()["data"]]
    assert names[0] == "高热度"


async def test_get_detail_and_pending_hidden(
    auth_client: AsyncClient, db_session: AsyncSession, test_user: dict
):
    """已发布详情可见；待审核详情对普通用户 404。"""
    approved = await _create_picture(db_session, test_user["id"], status="approved")
    pending = await _create_picture(db_session, test_user["id"], status="pending")

    r1 = await auth_client.get(f"/api/v1/pictures/{approved.id}")
    assert r1.status_code == 200
    assert r1.json()["download_count"] == 0
    assert r1.json()["pic_width"] == 100

    r2 = await auth_client.get(f"/api/v1/pictures/{pending.id}")
    assert r2.status_code == 404


async def test_download_increments_count(
    auth_client: AsyncClient, db_session: AsyncSession, test_user: dict
):
    """下载：返回 302，下载次数 +1。"""
    pic = await _create_picture(db_session, test_user["id"], status="approved", download_count=0)

    response = await auth_client.get(f"/api/v1/pictures/{pic.id}/download")
    assert response.status_code == 302
    assert response.headers["location"].startswith("https://")

    refreshed = await db_session.get(Picture, pic.id)
    assert refreshed.download_count == 1


async def test_manage_list_admin(
    superuser_auth_client: AsyncClient, db_session: AsyncSession, test_user: dict
):
    """管理端列表展示全状态（含待审核）。"""
    await _create_picture(db_session, test_user["id"], status="pending", name="待审核")
    await _create_picture(db_session, test_user["id"], status="approved", name="已发布")

    response = await superuser_auth_client.get("/api/v1/pictures/manage")
    assert response.status_code == 200
    names = {i["name"] for i in response.json()["data"]}
    assert "待审核" in names
    assert "已发布" in names


async def test_edit_metadata_admin(
    superuser_auth_client: AsyncClient, db_session: AsyncSession, test_user: dict
):
    """管理员编辑元信息（不含文件）。"""
    pic = await _create_picture(db_session, test_user["id"], name="旧名称", category="风景")

    response = await superuser_auth_client.patch(
        f"/api/v1/pictures/{pic.id}",
        json={"name": "新名称", "category": "动物", "tags": ["新标签"]},
    )
    assert response.status_code == 200

    refreshed = await db_session.get(Picture, pic.id)
    assert refreshed.name == "新名称"
    assert refreshed.category == "动物"
    assert refreshed.tags == ["新标签"]


async def test_audit_approve_makes_visible(
    superuser_auth_client: AsyncClient,
    auth_client: AsyncClient,
    db_session: AsyncSession,
    test_user: dict,
):
    """审核通过后，用户列表可见。"""
    pic = await _create_picture(db_session, test_user["id"], status="pending", name="待审核")

    # 审核前用户不可见
    r_before = await auth_client.get("/api/v1/pictures/")
    assert pic.name not in {i["name"] for i in r_before.json()["data"]}

    resp = await superuser_auth_client.patch(f"/api/v1/pictures/{pic.id}/status", json={"status": "approved"})
    assert resp.status_code == 200

    r_after = await auth_client.get("/api/v1/pictures/")
    assert pic.name in {i["name"] for i in r_after.json()["data"]}


async def test_delete_soft_delete(
    superuser_auth_client: AsyncClient, auth_client: AsyncClient, db_session: AsyncSession, test_user: dict
):
    """软删除后列表不再展示。"""
    pic = await _create_picture(db_session, test_user["id"], status="approved", name="将被删除")

    response = await superuser_auth_client.delete(f"/api/v1/pictures/{pic.id}")
    assert response.status_code == 200

    r_list = await auth_client.get("/api/v1/pictures/")
    assert pic.name not in {i["name"] for i in r_list.json()["data"]}

    refreshed = await db_session.get(Picture, pic.id)
    assert refreshed.is_deleted is True


async def test_admin_endpoints_forbidden_for_regular_user(
    auth_client: AsyncClient, db_session: AsyncSession, test_user: dict
):
    """普通用户访问管理端接口 → 403。"""
    pic = await _create_picture(db_session, test_user["id"], status="approved")

    assert (await auth_client.get("/api/v1/pictures/manage")).status_code == 403
    assert (await auth_client.patch(f"/api/v1/pictures/{pic.id}", json={"name": "x"})).status_code == 403
    assert (
        await auth_client.patch(f"/api/v1/pictures/{pic.id}/status", json={"status": "approved"})
    ).status_code == 403
    assert (await auth_client.delete(f"/api/v1/pictures/{pic.id}")).status_code == 403
