"""图片上传接口测试（COS 使用 mock，不触真实服务）。"""

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
    Image.new("RGB", (width, height), "red").save(buf, format="PNG")
    return buf.getvalue()


def _mock_cos(mocker):
    """将 COS 客户端替换为 mock，put_object 为 no-op。"""
    mock_client = mocker.Mock()
    mock_client.put_object.return_value = None
    mocker.patch.object(picture_service, "_get_cos_client", return_value=mock_client)
    return mock_client


async def test_upload_picture_success(superuser_auth_client: AsyncClient, mocker):
    """管理员上传成功：自动解析宽高/格式/色彩模式，状态为待审核。"""
    _mock_cos(mocker)

    files = {"file": ("test.png", make_png_image(), "image/png")}
    data = {"name": "测试图片", "category": "风景", "tags": '["风景","自然"]'}

    response = await superuser_auth_client.post("/api/v1/pictures/", files=files, data=data)

    assert response.status_code == 201
    body = response.json()
    assert body["name"] == "测试图片"
    assert body["category"] == "风景"
    assert body["tags"] == ["风景", "自然"]
    assert body["pic_width"] == 100
    assert body["pic_height"] == 50
    assert body["pic_scale"] == 2.0
    assert body["pic_format"] == "PNG"
    assert body["color_mode"] == "RGB"
    assert body["status"] == "pending"
    assert body["download_count"] == 0
    assert body["url"].startswith("https://")


async def test_upload_requires_login(client: AsyncClient, mocker):
    """未登录上传 → 401。"""
    _mock_cos(mocker)
    files = {"file": ("t.png", make_png_image(), "image/png")}
    data = {"name": "x", "category": "风景"}

    resp = await client.post("/api/v1/pictures/", files=files, data=data)
    assert resp.status_code == 401


async def test_upload_forbidden_for_regular_user(auth_client: AsyncClient, mocker):
    """普通用户上传 → 403。"""
    _mock_cos(mocker)
    files = {"file": ("t.png", make_png_image(), "image/png")}
    data = {"name": "x", "category": "风景"}

    resp = await auth_client.post("/api/v1/pictures/", files=files, data=data)
    assert resp.status_code == 403


async def test_upload_invalid_category(superuser_auth_client: AsyncClient, mocker):
    """分类不在预置列表 → 422。"""
    _mock_cos(mocker)
    files = {"file": ("t.png", make_png_image(), "image/png")}
    data = {"name": "x", "category": "不存在的分类"}

    response = await superuser_auth_client.post("/api/v1/pictures/", files=files, data=data)
    assert response.status_code == 422


async def test_upload_invalid_file(superuser_auth_client: AsyncClient, mocker):
    """非图片文件 → 422。"""
    _mock_cos(mocker)
    files = {"file": ("a.txt", b"not an image", "text/plain")}
    data = {"name": "x", "category": "风景"}

    response = await superuser_auth_client.post("/api/v1/pictures/", files=files, data=data)
    assert response.status_code == 422
