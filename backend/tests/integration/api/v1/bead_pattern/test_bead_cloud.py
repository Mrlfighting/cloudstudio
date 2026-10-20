"""拼豆云端真实 PostgreSQL 回归：权限、事务、幂等、版本和迁移。"""

import asyncio
import importlib.util
import json
import re
from io import BytesIO
from pathlib import Path
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from alembic.migration import MigrationContext
from alembic.operations import Operations
from fastapi import HTTPException
from PIL import Image
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.infrastructure.auth.dependencies import get_current_user
from src.interfaces.main import app
from src.modules.bead_pattern import persistence
from src.modules.bead_pattern.models import BeadPattern
from src.modules.bead_pattern.schemas import PALETTE_COUNTS, PALETTE_REVISION

pytestmark = pytest.mark.asyncio
URL = "/api/v1/bead-patterns/"


def project(name="云端图纸"):
    """最小合法协议包含透明格，保持与首版 JSON 一致。"""
    return {
        "format": "cloudatelier-bead-pattern",
        "version": 1,
        "engineVersion": "ciede2000-lanczos3-v1",
        "paletteRevision": PALETTE_REVISION,
        "paletteId": "mard-291-github",
        "name": name,
        "updatedAt": "2026-10-16T00:00:00Z",
        "params": {
            "longEdge": 100,
            "maxColors": 40,
            "removeBackground": False,
            "backgroundColor": None,
            "tolerance": 8,
            "denoise": 0,
        },
        "pattern": {"width": 2, "height": 2, "cells": [0, 1, -1, 0]},
    }


def png(edge=20):
    """动态生成真实 PNG，不提交二进制测试数据。"""
    stream = BytesIO()
    Image.new("RGB", (edge, edge), "pink").save(stream, "PNG")
    return stream.getvalue()


async def create(client, client_id=None, value=None, source=None):
    """显式 multipart；user_id 为伪造值，服务端必须忽略。"""
    me = await client.get("/api/v1/users/me")
    if me.status_code == 200:
        client.headers["X-Bead-Owner"] = str(me.json()["id"])
    return await client.post(
        URL,
        data={"client_id": str(client_id or uuid4()), "project": json.dumps(value or project()), "user_id": "999999"},
        files={"source": ("工作源.png", source or png(), "image/png"), "thumbnail": ("预览.png", png(), "image/png")},
    )


async def test_cloud_roundtrip_and_soft_delete(auth_client, test_user, db_session):
    """创建、摘要、图片、版本更新、重命名和软删除均使用真实表。"""
    res = await create(auth_client)
    assert res.status_code == 200, res.text
    row = res.json()
    assert row["revision"] == 1 and isinstance(row["id"], str)
    listing = (await auth_client.get(URL)).json()
    assert listing["total_count"] == 1 and "project_data" not in listing["data"][0]
    assert not any("data" in key for key in listing["data"][0])
    for kind in ("source", "thumbnail"):
        image = await auth_client.get(f"{URL}{row['id']}/{kind}")
        assert image.content == png() and "no-store" in image.headers["cache-control"]
    replaced = await auth_client.put(URL + row["id"], data={"revision": 1, "project": json.dumps(project("新版本"))})
    assert replaced.status_code == 200, replaced.text
    assert replaced.json()["revision"] == 2 and not replaced.json()["has_source"]
    assert (await auth_client.get(f"{URL}{row['id']}/source")).status_code == 404
    conflict = await auth_client.patch(URL + row["id"], json={"name": "过时写入", "revision": 1})
    assert conflict.status_code == 409
    renamed = await auth_client.patch(URL + row["id"], json={"name": "重命名", "revision": 2})
    assert renamed.json()["project_data"]["name"] == "重命名" and renamed.json()["revision"] == 3
    deleted = await auth_client.delete(URL + row["id"], params={"revision": 3})
    assert deleted.status_code == 200
    assert (await auth_client.get(URL + row["id"])).status_code == 404
    assert (await auth_client.get(URL)).json()["total_count"] == 0
    record = (await db_session.execute(select(BeadPattern).where(BeadPattern.id == int(row["id"])))).scalar_one()
    assert record.is_deleted and record.deleted_at and record.user_id == test_user["id"]


async def test_cloud_idempotency_and_tombstone(auth_client, db_session):
    """相同请求重复创建只一条；同标识不同内容或软删后不复活。"""
    client_id = uuid4()
    first = (await create(auth_client, client_id)).json()
    again = await create(auth_client, client_id)
    assert again.json()["id"] == first["id"]
    assert (await create(auth_client, client_id, project("不同内容"))).status_code == 409
    await auth_client.delete(URL + first["id"], params={"revision": 1})
    assert (await create(auth_client, client_id)).status_code == 409
    assert (await db_session.execute(select(func.count()).select_from(BeadPattern))).scalar_one() == 1


async def test_cloud_other_user_even_admin_denied(auth_client, test_user_2):
    """管理员也不能读/改别人的拼豆作品。"""
    row = (await create(auth_client)).json()

    async def other():
        return {**test_user_2, "user_role": "admin", "is_superuser": True}

    app.dependency_overrides[get_current_user] = other
    auth_client.headers["X-Bead-Owner"] = str(test_user_2["id"])
    for suffix in ("", "/source", "/thumbnail"):
        assert (await auth_client.get(URL + row["id"] + suffix)).status_code == 404
    assert (await auth_client.patch(URL + row["id"], json={"name": "越权", "revision": 1})).status_code == 404
    assert (await auth_client.delete(URL + row["id"], params={"revision": 1})).status_code == 404
    assert (await auth_client.get(URL)).json()["total_count"] == 0


@pytest.mark.parametrize(
    "change", ["indices", "length", "colors", "palette", "version", "extra", "boolean", "version_bool", "denoise_bool"]
)
async def test_cloud_invalid_project_rolls_back(auth_client, db_session, change):
    """无效 JSON 协议不得创建部分文件或作品。"""
    value = project()
    if change == "indices":
        value["pattern"]["cells"][0] = 291
    if change == "length":
        value["pattern"]["cells"] = [0]
    if change == "colors":
        value["pattern"]["cells"] = [0, 1, 2, 3]
        value["params"]["maxColors"] = 2
    if change == "palette":
        value["paletteId"] = "不存在"
    if change == "version":
        value["engineVersion"] = "未来版本"
    if change == "extra":
        value["original_image_url"] = "https://not-allowed.invalid"
    if change == "boolean":
        value["pattern"]["cells"][0] = True
    if change == "version_bool":
        value["version"] = True
    if change == "denoise_bool":
        value["params"]["denoise"] = True
    assert (await create(auth_client, value=value)).status_code == 422
    assert (await db_session.execute(select(func.count()).select_from(BeadPattern))).scalar_one() == 0


@pytest.mark.parametrize(
    "data,status",
    [(b"not an image", 415), (b"x" * (10 * 1024 * 1024 + 1), 413), (png(1601), 422)],
    ids=["corrupt", "oversize", "edge"],
)
async def test_cloud_invalid_source(auth_client, data, status):
    """真实文件、大小和边长都必须符合工作源上限。"""
    assert (await create(auth_client, source=data)).status_code == status


async def test_cloud_search_and_pagination(auth_client):
    """名称搜索按字面处理通配符，列表稳定分页。"""
    for name in ["花_100%", "花朵", "海边"]:
        assert (await create(auth_client, value=project(name))).status_code == 200
    found = (await auth_client.get(URL, params={"keyword": "_100%"})).json()
    assert found["total_count"] == 1 and found["data"][0]["name"] == "花_100%"
    first = (await auth_client.get(URL, params={"items_per_page": 2})).json()
    second = (await auth_client.get(URL, params={"items_per_page": 2, "page": 2})).json()
    assert len(first["data"]) == 2 and len(second["data"]) == 1


async def test_cloud_real_auth_and_csrf(client, test_user):
    """真实 Session/CSRF 请求，不用鉴权 override。"""
    assert (await client.get(URL)).status_code == 401
    login = await client.post("/api/v1/auth/login", data={"username": test_user["username"], "password": test_user["password"]})
    assert login.status_code == 200, login.text
    missing = await create(client)
    assert missing.status_code == 403
    client.headers["X-CSRF-Token"] = login.json()["csrf_token"]
    assert (await create(client)).status_code == 200


async def test_cloud_migration_up_down(test_db_engine):
    """在临时 PostgreSQL 的既有基础表上执行本次迁移升/降/升。"""
    file = Path(__file__).parents[5] / "migrations/versions/e2b3c4d5f6a7_拼豆工坊_新增独立作品表.py"
    spec = importlib.util.spec_from_file_location("bead_migration", file)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    def run(connection):
        context = MigrationContext.configure(connection)
        with Operations.context(context):
            module.downgrade()
            module.upgrade()
            module.downgrade()
            module.upgrade()

    async with test_db_engine.begin() as connection:
        await connection.run_sync(run)


async def test_backend_palette_manifest_parity():
    """固定色卡可用数与后端校验一致，不复制上游原始色卡进后端。"""
    root = Path(__file__).parents[6] / "frontend/src/features/bead-pattern/palettes"
    for name, count in PALETTE_COUNTS.items():
        raw = json.loads((root / f"{name}.json").read_text(encoding="utf-8"))
        seen = set()
        for color in raw["colors"]:
            code, hex_value = color["code"].strip(), color["hex"].upper()
            if (
                not code
                or re.fullmatch(r"(-|\?|UNKNOWN.*)", code, re.I)
                or color.get("unidentified")
                or color.get("transparency")
            ):
                continue
            if re.fullmatch(r"#[0-9A-F]{6}", hex_value):
                seen.add(hex_value)
        assert len(seen) == count


async def test_cloud_concurrent_update(auth_client, test_user, test_db_engine):
    """独立数据库连接同时提交同版本，只有一个可成功。"""
    row = (await create(auth_client)).json()

    async def update_one(name):
        async with AsyncSession(test_db_engine) as db:
            try:
                await persistence.write(db, test_user["id"], int(row["id"]), 1, {"name": name})
                return 200
            except HTTPException as error:
                return error.status_code

    statuses = await asyncio.gather(update_one("设备一"), update_one("设备二"))
    assert sorted(statuses) == [200, 409]
    assert (await auth_client.get(URL + row["id"])).json()["revision"] == 2


async def test_cloud_commit_failure_rolls_back(auth_client, db_session, monkeypatch):
    """即使 INSERT 已执行，提交失败也不留下半条作品。"""
    original = db_session.commit
    monkeypatch.setattr(db_session, "commit", AsyncMock(side_effect=RuntimeError("模拟提交失败")))
    assert (await create(auth_client)).status_code == 500
    monkeypatch.setattr(db_session, "commit", original)
    assert (await db_session.execute(select(func.count()).select_from(BeadPattern))).scalar_one() == 0


async def test_expected_owner_rejects_shared_cookie_switch(client, test_user, test_user_2, db_session, monkeypatch):
    """真实会话属于B、旧标签页预期A时，所有拼豆接口拒绝，文件校验和数据库写入均不执行。"""
    login = await client.post(
        "/api/v1/auth/login", data={"username": test_user_2["username"], "password": test_user_2["password"]}
    )
    client.headers.update({"X-CSRF-Token": login.json()["csrf_token"], "X-Bead-Owner": str(test_user["id"])})
    files = AsyncMock()
    monkeypatch.setattr(persistence, "files_data", files)
    responses = [
        await client.post(URL, data={"client_id": str(uuid4()), "project": json.dumps(project())}),
        await client.get(URL),
        await client.get(URL + "1"),
        await client.put(URL + "1", data={"revision": 1, "project": json.dumps(project())}),
        await client.patch(URL + "1", json={"name": "旧账号误写", "revision": 1}),
        await client.delete(URL + "1", params={"revision": 1}),
        await client.get(URL + "1/source"),
        await client.get(URL + "sources/private/1"),
    ]
    for response in responses:
        assert response.status_code == 409, response.text
        assert response.headers["x-bead-session-changed"] == "1"
    files.assert_not_awaited()
    assert (await db_session.execute(select(func.count()).select_from(BeadPattern))).scalar_one() == 0
    del client.headers["X-Bead-Owner"]
    assert (await client.get(URL)).status_code == 428
    assert (await client.get(URL + "1/thumbnail", params={"owner": test_user["id"]})).status_code == 409
    assert (await client.get(URL + "1/thumbnail")).status_code == 428
    assert (await client.get(URL + "1/thumbnail", params={"owner": test_user_2["id"]})).status_code == 404
    client.headers["X-Bead-Owner"] = str(test_user_2["id"])
    assert (await client.get(URL)).status_code == 200
