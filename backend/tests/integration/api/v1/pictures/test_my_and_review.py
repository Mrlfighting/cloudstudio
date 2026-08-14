"""我的上传列表与审核理由测试（COS 使用 mock）。"""

import io
import logging

import pytest
from httpx import AsyncClient
from PIL import Image

from src.modules.pictures import service as picture_service

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

pytestmark = pytest.mark.asyncio


def make_png_image(width: int = 100, height: int = 50) -> bytes:
    """用 Pillow 内存生成一张 PNG 测试图。"""
    buf = io.BytesIO()
    Image.new("RGB", (width, height), "blue").save(buf, format="PNG")
    return buf.getvalue()


def _mock_cos(mocker):
    """将 COS 客户端替换为 mock。"""
    mock_client = mocker.Mock()
    mock_client.put_object.return_value = None
    mocker.patch.object(picture_service, "_get_cos_client", return_value=mock_client)


async def _upload(auth_client: AsyncClient, name: str = "测试图") -> int:
    """上传一张图并返回 id。"""
    files = {"file": ("t.png", make_png_image(), "image/png")}
    data = {"name": name, "category": "风景"}
    resp = await auth_client.post("/api/v1/pictures/", files=files, data=data)
    assert resp.status_code == 201
    return resp.json()["id"]


async def test_my_list_isolated_by_user(
    auth_client: AsyncClient,
    auth_client_2: AsyncClient,
    superuser_auth_client: AsyncClient,
    mocker,
):
    """我的上传只含当前用户上传的图片。"""
    _mock_cos(mocker)
    mine = await _upload(auth_client, "我的图")
    await _upload(auth_client_2, "别人的图")

    resp = await auth_client.get("/api/v1/pictures/my")
    assert resp.status_code == 200
    ids = [p["id"] for p in resp.json()["data"]]
    assert mine in ids
    assert all(p["user_id"] for p in resp.json()["data"])


async def test_reject_requires_reason(
    auth_client: AsyncClient,
    superuser_auth_client: AsyncClient,
    mocker,
):
    """拒绝无理由 → 422；带理由 → 200 且我的上传可见理由。"""
    _mock_cos(mocker)
    pid = await _upload(auth_client)

    resp = await superuser_auth_client.patch(
        f"/api/v1/pictures/{pid}/status", json={"status": "rejected"},
    )
    assert resp.status_code == 422

    resp = await superuser_auth_client.patch(
        f"/api/v1/pictures/{pid}/status",
        json={"status": "rejected", "review_reason": "内容违规"},
    )
    assert resp.status_code == 200

    resp = await auth_client.get("/api/v1/pictures/my")
    mine = [p for p in resp.json()["data"] if p["id"] == pid][0]
    assert mine["status"] == "rejected"
    assert mine["review_reason"] == "内容违规"


async def test_approve_clears_reason(
    auth_client: AsyncClient,
    superuser_auth_client: AsyncClient,
    mocker,
):
    """通过后 review_reason 清空，用户列表可见。"""
    _mock_cos(mocker)
    pid = await _upload(auth_client)

    await superuser_auth_client.patch(
        f"/api/v1/pictures/{pid}/status",
        json={"status": "rejected", "review_reason": "先拒绝"},
    )
    resp = await superuser_auth_client.patch(
        f"/api/v1/pictures/{pid}/status", json={"status": "approved"},
    )
    assert resp.status_code == 200

    resp = await auth_client.get(f"/api/v1/pictures/{pid}")
    assert resp.status_code == 200
    assert resp.json()["review_reason"] is None

    resp = await auth_client.get("/api/v1/pictures/")
    assert any(p["id"] == pid for p in resp.json()["data"])
