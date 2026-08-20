"""空间模块接口测试（COS 使用 mock）。"""

import io

import pytest
from httpx import AsyncClient
from PIL import Image

from src.modules.space import service as space_service

pytestmark = pytest.mark.asyncio


def make_png_image(width: int = 100, height: int = 50) -> bytes:
    """用 Pillow 内存生成一张 PNG 测试图。"""
    buf = io.BytesIO()
    Image.new("RGB", (width, height), "red").save(buf, format="PNG")
    return buf.getvalue()


def _mock_cos(mocker):
    """将空间服务里 import 的 COS 客户端替换为 mock。"""
    mock_client = mocker.Mock()
    mock_client.put_object.return_value = None
    mocker.patch.object(space_service, "_get_cos_client", return_value=mock_client)
    return mock_client


async def test_create_space_success(auth_client: AsyncClient):
    resp = await auth_client.post("/api/v1/spaces/", json={"name": "我的空间"})
    assert resp.status_code == 201
    body = resp.json()
    assert body["name"] == "我的空间"
    assert body["space_level"] == 0
    assert body["status"] == "active"
    assert body["max_size"] == 500 * 1024 * 1024
    assert body["max_count"] == 100


async def test_create_space_duplicate(auth_client: AsyncClient):
    await auth_client.post("/api/v1/spaces/", json={"name": "空间A"})
    resp = await auth_client.post("/api/v1/spaces/", json={"name": "空间B"})
    assert resp.status_code == 422


async def test_get_my_space(auth_client: AsyncClient):
    await auth_client.post("/api/v1/spaces/", json={"name": "我的空间"})
    resp = await auth_client.get("/api/v1/spaces/my")
    assert resp.status_code == 200
    body = resp.json()
    assert body["name"] == "我的空间"
    assert body["remaining_size"] == body["max_size"]
    assert body["remaining_count"] == body["max_count"]


async def test_upgrade_level(auth_client: AsyncClient):
    await auth_client.post("/api/v1/spaces/", json={"name": "我的空间"})
    resp = await auth_client.patch("/api/v1/spaces/my/level", json={"space_level": 1})
    assert resp.status_code == 200
    body = resp.json()
    assert body["space_level"] == 1
    assert body["max_size"] == 5 * 1024 * 1024 * 1024
    assert body["max_count"] == 1000


async def test_upload_space_picture(auth_client: AsyncClient, mocker):
    """空间上传图片：不审核，直接 approved，且带 space_id。"""
    _mock_cos(mocker)
    await auth_client.post("/api/v1/spaces/", json={"name": "我的空间"})

    files = {"file": ("test.png", make_png_image(), "image/png")}
    data = {"name": "空间图片", "category": "风景", "tags": '["风景"]'}
    resp = await auth_client.post("/api/v1/spaces/my/pictures", files=files, data=data)

    assert resp.status_code == 201
    body = resp.json()
    assert body["name"] == "空间图片"
    assert body["status"] == "approved"  # 不审核
    assert body["space_id"] is not None  # 关联空间
    assert body["pic_width"] == 100
    assert body["pic_height"] == 50


async def test_list_space_pictures(auth_client: AsyncClient, mocker):
    _mock_cos(mocker)
    await auth_client.post("/api/v1/spaces/", json={"name": "我的空间"})
    files = {"file": ("t.png", make_png_image(), "image/png")}
    data = {"name": "空间图片", "category": "风景"}
    await auth_client.post("/api/v1/spaces/my/pictures", files=files, data=data)

    resp = await auth_client.get("/api/v1/spaces/my/pictures")
    assert resp.status_code == 200
    body = resp.json()
    assert body["total_count"] == 1
    assert body["data"][0]["name"] == "空间图片"


async def test_space_isolation_no_space(auth_client_2: AsyncClient):
    """用户 2 无空间时访问 /spaces/my 返回 404（无法查看他人空间）。"""
    resp = await auth_client_2.get("/api/v1/spaces/my")
    assert resp.status_code == 404


async def test_public_gallery_excludes_space_pictures(auth_client: AsyncClient, mocker):
    """空间图片不进入公共图库列表。"""
    _mock_cos(mocker)
    await auth_client.post("/api/v1/spaces/", json={"name": "我的空间"})
    files = {"file": ("t.png", make_png_image(), "image/png")}
    data = {"name": "空间私有图片", "category": "风景"}
    await auth_client.post("/api/v1/spaces/my/pictures", files=files, data=data)

    # 公共图库列表不应包含空间图片
    resp = await auth_client.get("/api/v1/pictures/")
    assert resp.status_code == 200
    names = [item["name"] for item in resp.json()["data"]]
    assert "空间私有图片" not in names


async def test_admin_list_spaces(superuser_auth_client: AsyncClient, auth_client: AsyncClient):
    await auth_client.post("/api/v1/spaces/", json={"name": "普通用户空间"})
    resp = await superuser_auth_client.get("/api/v1/spaces/")
    assert resp.status_code == 200
    body = resp.json()
    assert body["total_count"] >= 1
    names = [s["name"] for s in body["data"]]
    assert "普通用户空间" in names


async def test_admin_ban_then_upload_rejected(superuser_auth_client: AsyncClient, auth_client: AsyncClient, mocker):
    """封禁后用户无法上传。"""
    _mock_cos(mocker)
    create = await auth_client.post("/api/v1/spaces/", json={"name": "我的空间"})
    space_id = create.json()["id"]

    ban = await superuser_auth_client.post(f"/api/v1/spaces/{space_id}/ban")
    assert ban.status_code == 200
    assert ban.json()["status"] == "banned"

    files = {"file": ("t.png", make_png_image(), "image/png")}
    data = {"name": "x", "category": "风景"}
    resp = await auth_client.post("/api/v1/spaces/my/pictures", files=files, data=data)
    assert resp.status_code == 403


async def test_admin_unban(superuser_auth_client: AsyncClient, auth_client: AsyncClient):
    create = await auth_client.post("/api/v1/spaces/", json={"name": "我的空间"})
    space_id = create.json()["id"]
    await superuser_auth_client.post(f"/api/v1/spaces/{space_id}/ban")
    resp = await superuser_auth_client.post(f"/api/v1/spaces/{space_id}/unban")
    assert resp.status_code == 200
    assert resp.json()["status"] == "active"
