import logging
import uuid

import pytest
from httpx import AsyncClient

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

pytestmark = pytest.mark.asyncio


def generate_register_data(prefix: str = "flow") -> dict:
    """生成唯一的注册数据。"""
    unique_id = uuid.uuid4().hex[:6]
    return {
        "account": f"{prefix}{unique_id}",
        "password": "Password123!",
        "confirm_password": "Password123!",
    }


async def test_register_login_me_logout_flow(client: AsyncClient):
    """完整用户链路：注册 → 登录获取会话 → 获取当前用户（免重复登录）→ 注销。"""
    data = generate_register_data()

    # 1. 注册
    reg = await client.post("/api/v1/users/register", json=data)
    assert reg.status_code == 201

    # 2. 登录（表单字段名为 username，即账号）
    login = await client.post(
        "/api/v1/auth/login",
        data={"username": data["account"], "password": data["password"]},
    )
    assert login.status_code == 200
    csrf_token = login.json()["csrf_token"]
    assert csrf_token
    assert "session_id" in login.cookies

    # 3. 获取当前用户（带会话 cookie，无需重复登录）
    me = await client.get("/api/v1/users/me")
    assert me.status_code == 200
    me_data = me.json()
    assert me_data["username"] == data["account"]
    assert me_data["user_role"] == "user"
    assert me_data["is_superuser"] is False

    # 4. 注销（需要 CSRF 头）
    logout = await client.post("/api/v1/auth/logout", headers={"X-CSRF-Token": csrf_token})
    assert logout.status_code == 200

    # 5. 注销后会话失效，/me 返回 401
    me_after = await client.get("/api/v1/users/me")
    assert me_after.status_code == 401


async def test_register_me_before_login(client: AsyncClient):
    """注册后未登录时访问 /me 返回 401。"""
    data = generate_register_data()
    reg = await client.post("/api/v1/users/register", json=data)
    assert reg.status_code == 201

    me = await client.get("/api/v1/users/me")
    assert me.status_code == 401
