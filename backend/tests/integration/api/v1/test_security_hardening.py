"""上线安全回归：使用临时 PostgreSQL，第三方 COS/AI 均替换为模拟服务。"""

import asyncio
from io import BytesIO
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import FastAPI, UploadFile
from httpx import ASGITransport, AsyncClient
from PIL import Image
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import async_sessionmaker

from src.infrastructure.config.settings import get_settings
from src.infrastructure.image_outpainting import CreateTaskResponse, OutpaintingParameters
from src.interfaces.admin import initialize as admin_initialize
from src.modules.analytics.service import AnalyticsService
from src.modules.common.exceptions import PictureNotFoundError, SpaceBannedError, SpaceExistsError
from src.modules.pictures.models import Picture
from src.modules.pictures.schemas import PictureStatusUpdate
from src.modules.pictures.service import PictureService
from src.modules.space import service as spaces
from src.modules.space.enums import SpaceRole
from src.modules.space.models import Space, SpaceUser
from src.modules.space.service import SpaceService
from src.modules.tier.models import Tier

pytestmark = pytest.mark.asyncio


def png_file() -> UploadFile:
    """小尺寸合法图像，不访问真实对象存储。"""
    buffer = BytesIO()
    Image.new("RGB", (12, 8), "red").save(buffer, format="PNG")
    buffer.seek(0)
    return UploadFile(buffer, filename="test.png")


async def picture(db, user_id, **values):
    """构造最小图库记录。"""
    row = Picture(
        name="安全测试图片",
        url="https://example.invalid/image.png",
        user_id=user_id,
        introduction=None,
        category="风景",
        pic_size=100,
        pic_width=12,
        pic_height=8,
        pic_scale=1.5,
        pic_format="PNG",
        color_mode="RGB",
        primary_color=0xFF0000,
        **values,
    )
    db.add(row)
    await db.commit()
    return row


@pytest.mark.parametrize("field", ["google_id", "github_id", "oauth_provider", "oauth_updated_at"])
async def test_profile_cannot_bind_oauth(auth_client, test_user, field):
    """资料更新不能绕过第三方身份验证。"""
    response = await auth_client.patch(f"/api/v1/users/{test_user['username']}", json={field: "unproved"})
    assert response.status_code == 422


async def test_rate_limit_reads_require_login(client):
    """匿名请求不能读取内部限流配置。"""
    for path in ("/api/v1/rate-limits/", "/api/v1/rate-limits/any"):
        assert (await client.get(path)).status_code == 401


@pytest.mark.parametrize("query", ["page=0", "items_per_page=0", "items_per_page=101"])
async def test_pagination_is_bounded(client, query):
    """分页参数在执行查询前受明确约束。"""
    assert (await client.get("/api/v1/tiers/?" + query)).status_code == 422


async def test_banned_spaces_block_read_edit_and_analysis(db_session, test_user, test_user_2):
    """封禁覆盖图片和分析，仍允许本人查看封禁摘要。"""
    service = SpaceService()
    private = await service.create(db_session, "私有空间", test_user)
    private_picture = await picture(db_session, test_user["id"], space_id=private["id"])
    await service.set_ban(db_session, private["id"], True)
    assert (await service.get_my(db_session, test_user))["status"] == "banned"
    with pytest.raises(SpaceBannedError):
        await service.get_picture(db_session, test_user, private_picture.id)
    with pytest.raises(SpaceBannedError):
        await AnalyticsService().get_my_top_pictures(db_session, test_user["id"], 10)
    team = await service.create_team(db_session, "团队空间", test_user)
    await service.add_member(db_session, team["id"], test_user_2["id"], SpaceRole.EDITOR)
    await service.set_ban(db_session, team["id"], True)
    with pytest.raises(SpaceBannedError):
        await service.list_team_pictures(
            db_session, team["id"], page=1, items_per_page=10, category=None, keyword=None, sort="time"
        )


async def test_team_creation_rolls_back_member_failure(db_session, test_user, monkeypatch):
    """成员创建失败不能留下无管理员的团队。"""
    monkeypatch.setattr(spaces.crud_space_users, "create", AsyncMock(side_effect=RuntimeError("injected")))
    with pytest.raises(RuntimeError):
        await SpaceService().create_team(db_session, "失败团队", test_user)
    assert (await db_session.execute(select(func.count()).select_from(Space))).scalar_one() == 0
    assert (await db_session.execute(select(func.count()).select_from(SpaceUser))).scalar_one() == 0


async def test_unique_constraint_conflict_has_domain_response(db_session, test_user, monkeypatch):
    """数据库最后一道唯一约束冲突也应转为已存在，而非暴露数据库异常。"""
    error = IntegrityError("INSERT", {}, Exception('duplicate key violates constraint "uq_spaces_active_owner_type"'))
    monkeypatch.setattr(spaces.crud_spaces, "create", AsyncMock(side_effect=error))
    with pytest.raises(SpaceExistsError):
        await SpaceService().create(db_session, "重复", test_user)
    assert (await db_session.execute(select(func.count()).select_from(Space))).scalar_one() == 0


async def test_admin_form_csrf_protects_real_database_write(db_session, test_db_engine, monkeypatch):
    """合法后台表单仍可写入；缺失令牌或跨站提交不会改变数据库。"""
    settings = get_settings()
    for key, value in {
        "ADMIN_ENABLED": True,
        "ADMIN_USERNAME": "test-admin",
        "ADMIN_PASSWORD": "test-only-password",
        "SESSION_SECURE_COOKIES": True,
    }.items():
        monkeypatch.setattr(settings, key, value)
    monkeypatch.setattr(admin_initialize, "engine", test_db_engine)
    monkeypatch.setattr("src.interfaces.admin.auth.increment_and_check", AsyncMock(return_value=(1, False)))
    app = FastAPI()
    admin_initialize.create_admin_interface(app)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="https://test") as client:
        await client.get("/admin/login")
        token = client.cookies.get("atelier_admin_csrf")
        login = await client.post(
            "/admin/login",
            data={"username": "test-admin", "password": "test-only-password", "csrf_token": token},
            headers={"Origin": "https://test"},
        )
        assert login.status_code == 302
        form = {"name": "csrf-test-tier", "description": "安全表单测试", "save": "Save"}
        assert (await client.post("/admin/tier/create", data=form, headers={"Origin": "https://test"})).status_code == 403
        form["csrf_token"] = token
        assert (
            await client.post("/admin/tier/create", data=form, headers={"Origin": "https://evil.invalid"})
        ).status_code == 403
        assert (await db_session.execute(select(func.count()).select_from(Tier))).scalar_one() == 0
        response = await client.post("/admin/tier/create", data=form, headers={"Origin": "https://test"})
        assert response.status_code == 302
        assert (await db_session.execute(select(func.count()).select_from(Tier))).scalar_one() == 1


async def test_concurrent_space_creation_separate_sessions(test_db_engine, test_user):
    """真实独立事务竞争时只能创建一个活跃空间。"""
    sessions = async_sessionmaker(test_db_engine, expire_on_commit=False)

    async def create():
        async with sessions() as db:
            try:
                await SpaceService().create(db, "并发空间", test_user)
                return True
            except SpaceExistsError:
                return False

    assert sum(await asyncio.gather(*(create() for _ in range(5)))) == 1


async def test_download_atomic_increment(test_db_engine, db_session, test_user):
    """并发下载不丢失计数。"""
    row = await picture(db_session, test_user["id"], status="approved")
    sessions = async_sessionmaker(test_db_engine, expire_on_commit=False)

    async def download():
        async with sessions() as db:
            return await PictureService().download(db, row.id)

    assert len(await asyncio.gather(*(download() for _ in range(20)))) == 20
    await db_session.refresh(row)
    assert row.download_count == 20


async def test_rejected_picture_never_served_from_stale_instance(db_session, test_user):
    """已撤回图片不从其他实例旧缓存返回。"""
    row = await picture(db_session, test_user["id"], status="approved")
    service_a, service_b = PictureService(), PictureService()
    assert (await service_b.get(db_session, row.id, require_approved=True))["id"] == row.id
    await service_a.audit(db_session, row.id, PictureStatusUpdate(status="rejected", review_reason="撤回"))
    with pytest.raises(PictureNotFoundError):
        await service_b.get(db_session, row.id, require_approved=True)
    assert not (await service_b.list_user(db_session))["data"]


async def test_upload_quota_failure_rolls_back_and_cleans_cos(db_session, test_user, monkeypatch):
    """配额写入失败时同时回滚图片并清理对象。"""
    service = SpaceService()
    private = await service.create(db_session, "上传空间", test_user)
    cos = MagicMock()
    monkeypatch.setattr(spaces, "_get_cos_client", lambda: cos)
    monkeypatch.setattr(spaces, "extract_primary_color", lambda *args: 0xFF0000)
    monkeypatch.setattr(service, "_add_quota", AsyncMock(side_effect=RuntimeError("injected")))
    with pytest.raises(RuntimeError):
        await service.upload_picture(db_session, test_user, png_file(), "图片", None, "风景", "[]")
    assert (await db_session.execute(select(func.count()).select_from(Picture))).scalar_one() == 0
    await db_session.refresh(await db_session.get(Space, private["id"]))
    cos.delete_object.assert_called_once()


async def test_outpainting_owner_and_legacy_task_isolation(db_session, test_user, test_user_2, monkeypatch):
    """任务 ID 不能替代归属授权，旧任务也不能猜测归属。"""
    service = SpaceService()
    private = await service.create(db_session, "扩图空间", test_user)
    source = await picture(db_session, test_user["id"], space_id=private["id"])
    monkeypatch.setattr(
        spaces,
        "create_outpainting_task",
        AsyncMock(return_value=CreateTaskResponse(task_id="private-task", task_status="PENDING")),
    )
    upstream = AsyncMock()
    monkeypatch.setattr(spaces, "query_outpainting_task", upstream)
    await service.create_outpainting_task(db_session, test_user, source.id, OutpaintingParameters())
    for user, task in ((test_user_2, "private-task"), (test_user, "legacy-task")):
        with pytest.raises(PictureNotFoundError):
            await service.query_outpainting_task(db_session, user, task)
    upstream.assert_not_awaited()
