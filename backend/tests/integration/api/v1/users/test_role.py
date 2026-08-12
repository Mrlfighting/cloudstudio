import logging
import uuid

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.user.models import User

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

pytestmark = pytest.mark.asyncio


def generate_register_data(prefix: str = "role") -> dict:
    """生成唯一的注册数据。"""
    unique_id = uuid.uuid4().hex[:6]
    return {
        "account": f"{prefix}{unique_id}",
        "password": "Password123!",
        "confirm_password": "Password123!",
    }


async def test_admin_update_role_to_admin(
    client: AsyncClient,
    superuser_auth_client: AsyncClient,
    db_session: AsyncSession,
):
    """管理员可将普通用户提升为 admin，is_superuser 同步为 True。"""
    data = generate_register_data()
    reg_resp = await client.post("/api/v1/users/register", json=data)
    assert reg_resp.status_code == 201
    user_id = reg_resp.json()["id"]
    username = reg_resp.json()["username"]

    resp = await superuser_auth_client.patch(f"/api/v1/users/{username}/role", json={"user_role": "admin"})
    assert resp.status_code == 200

    # 数据库校验 user_role 与 is_superuser 已同步
    user_in_db = await db_session.get(User, user_id)
    assert user_in_db is not None
    assert user_in_db.user_role == "admin"
    assert user_in_db.is_superuser is True


async def test_admin_update_role_back_to_user(
    client: AsyncClient,
    superuser_auth_client: AsyncClient,
    db_session: AsyncSession,
):
    """管理员将 admin 降级为 user，is_superuser 同步为 False。"""
    data = generate_register_data()
    reg_resp = await client.post("/api/v1/users/register", json=data)
    assert reg_resp.status_code == 201
    user_id = reg_resp.json()["id"]
    username = reg_resp.json()["username"]

    # 先提升为 admin
    resp = await superuser_auth_client.patch(f"/api/v1/users/{username}/role", json={"user_role": "admin"})
    assert resp.status_code == 200
    # 再降级为 user
    resp = await superuser_auth_client.patch(f"/api/v1/users/{username}/role", json={"user_role": "user"})
    assert resp.status_code == 200

    user_in_db = await db_session.get(User, user_id)
    assert user_in_db.user_role == "user"
    assert user_in_db.is_superuser is False


async def test_regular_user_cannot_change_role(
    client: AsyncClient,
    auth_client: AsyncClient,
    test_user: dict,
):
    """普通用户调用角色修改接口 → 403。"""
    resp = await auth_client.patch(f"/api/v1/users/{test_user['username']}/role", json={"user_role": "admin"})
    assert resp.status_code == 403


async def test_invalid_role_value(
    client: AsyncClient,
    superuser_auth_client: AsyncClient,
):
    """非法角色值 → 422。"""
    data = generate_register_data()
    reg_resp = await client.post("/api/v1/users/register", json=data)
    assert reg_resp.status_code == 201

    resp = await superuser_auth_client.patch(
        f"/api/v1/users/{reg_resp.json()['username']}/role",
        json={"user_role": "superadmin"},
    )
    assert resp.status_code == 422


async def test_update_role_user_not_found(superuser_auth_client: AsyncClient):
    """目标用户不存在 → 404。"""
    resp = await superuser_auth_client.patch("/api/v1/users/nonexistent123/role", json={"user_role": "admin"})
    assert resp.status_code == 404
