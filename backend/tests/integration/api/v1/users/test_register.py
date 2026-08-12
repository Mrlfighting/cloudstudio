import logging
import uuid

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.user.models import User

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

pytestmark = pytest.mark.asyncio


def generate_register_data(prefix: str = "user") -> dict:
    """生成唯一的注册数据（账号 + 密码 + 确认密码）。"""
    unique_id = uuid.uuid4().hex[:6]
    return {
        "account": f"{prefix}{unique_id}",
        "password": "Password123!",
        "confirm_password": "Password123!",
    }


async def test_register_success(client: AsyncClient, db_session: AsyncSession):
    """注册成功：账号 + 密码 + 确认密码。"""
    data = generate_register_data()

    logger.info(f"测试注册账号: {data['account']}")
    response = await client.post("/api/v1/users/register", json=data)

    assert response.status_code == 201
    body = response.json()
    assert body["username"] == data["account"]
    assert body["name"] == data["account"]  # 未提供昵称时默认取账号
    assert body["email"] is None
    assert body["user_role"] == "user"
    assert body["is_superuser"] is False
    # 不泄漏密码
    assert "password" not in body
    assert "hashed_password" not in body

    # 数据库落库校验
    user_in_db = await db_session.get(User, body["id"])
    assert user_in_db is not None
    assert user_in_db.username == data["account"]
    assert user_in_db.email is None
    assert user_in_db.user_role == "user"
    assert user_in_db.is_superuser is False


async def test_register_with_nickname_and_profile(client: AsyncClient):
    """注册时提供昵称与简介。"""
    data = generate_register_data()
    data["nickname"] = "张三"
    data["user_profile"] = "这是我的个人简介"

    response = await client.post("/api/v1/users/register", json=data)

    assert response.status_code == 201
    body = response.json()
    assert body["name"] == "张三"
    assert body["user_profile"] == "这是我的个人简介"


async def test_register_password_mismatch(client: AsyncClient):
    """两次密码不一致 → 422。"""
    data = generate_register_data()
    data["confirm_password"] = "Different123!"

    response = await client.post("/api/v1/users/register", json=data)

    assert response.status_code == 422


async def test_register_duplicate_account(client: AsyncClient, test_user: dict):
    """账号已被占用 → 422。"""
    data = generate_register_data()
    data["account"] = test_user["username"]

    logger.info(f"测试重复账号: {data['account']}")
    response = await client.post("/api/v1/users/register", json=data)

    assert response.status_code == 422


async def test_register_invalid_account_pattern(client: AsyncClient):
    """账号格式非法（含大写字母与特殊字符）→ 422。"""
    data = generate_register_data()
    data["account"] = "Invalid-Account!"

    response = await client.post("/api/v1/users/register", json=data)

    assert response.status_code == 422


async def test_register_short_password(client: AsyncClient):
    """密码过短 → 422。"""
    data = generate_register_data()
    data["password"] = "short"
    data["confirm_password"] = "short"

    response = await client.post("/api/v1/users/register", json=data)

    assert response.status_code == 422
