"""团队空间接口测试（COS 使用 mock）。"""

import io

import pytest
from httpx import AsyncClient
from PIL import Image
from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.space import service as space_service
from src.modules.space.service import SpaceService

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


async def test_create_team_success(auth_client: AsyncClient):
    resp = await auth_client.post("/api/v1/spaces/team", json={"name": "我的团队"})
    assert resp.status_code == 201
    body = resp.json()
    assert body["name"] == "我的团队"
    assert body["space_type"] == 1  # TEAM
    assert body["space_level"] == 0
    assert body["max_size"] == int(2.5 * 1024**3)
    assert body["max_count"] == 500


async def test_create_team_duplicate(auth_client: AsyncClient):
    await auth_client.post("/api/v1/spaces/team", json={"name": "团队A"})
    resp = await auth_client.post("/api/v1/spaces/team", json={"name": "团队B"})
    assert resp.status_code == 422


async def test_get_my_team(auth_client: AsyncClient):
    await auth_client.post("/api/v1/spaces/team", json={"name": "我的团队"})
    resp = await auth_client.get("/api/v1/spaces/team/my")
    assert resp.status_code == 200
    body = resp.json()
    assert body["name"] == "我的团队"
    assert body["space_type"] == 1
    assert body["remaining_count"] == body["max_count"]


async def test_add_member_and_list(auth_client: AsyncClient, test_user_2: dict):
    create = await auth_client.post("/api/v1/spaces/team", json={"name": "团队"})
    team_id = create.json()["id"]

    add = await auth_client.post(
        f"/api/v1/spaces/{team_id}/members", json={"user_id": test_user_2["id"], "space_role": "editor"}
    )
    assert add.status_code == 201
    assert add.json()["space_role"] == "editor"

    resp = await auth_client.get(f"/api/v1/spaces/{team_id}/members")
    assert resp.status_code == 200
    members = resp.json()
    assert len(members) == 2
    assert {m["space_role"] for m in members} == {"admin", "editor"}


async def test_remove_member(auth_client: AsyncClient, test_user_2: dict):
    create = await auth_client.post("/api/v1/spaces/team", json={"name": "团队"})
    team_id = create.json()["id"]
    await auth_client.post(
        f"/api/v1/spaces/{team_id}/members", json={"user_id": test_user_2["id"], "space_role": "editor"}
    )

    resp = await auth_client.delete(f"/api/v1/spaces/{team_id}/members/{test_user_2['id']}")
    assert resp.status_code == 200

    members = (await auth_client.get(f"/api/v1/spaces/{team_id}/members")).json()
    assert len(members) == 1


async def test_upload_team_picture(auth_client: AsyncClient, mocker):
    _mock_cos(mocker)
    create = await auth_client.post("/api/v1/spaces/team", json={"name": "团队"})
    team_id = create.json()["id"]

    files = {"file": ("t.png", make_png_image(), "image/png")}
    data = {"name": "团队图片", "category": "风景", "tags": '["风景"]'}
    resp = await auth_client.post(f"/api/v1/spaces/{team_id}/pictures", files=files, data=data)

    assert resp.status_code == 201
    body = resp.json()
    assert body["name"] == "团队图片"
    assert body["status"] == "approved"  # 团队空间不审核
    assert body["space_id"] == team_id


async def test_list_team_pictures(auth_client: AsyncClient, mocker):
    _mock_cos(mocker)
    create = await auth_client.post("/api/v1/spaces/team", json={"name": "团队"})
    team_id = create.json()["id"]
    files = {"file": ("t.png", make_png_image(), "image/png")}
    data = {"name": "团队图片", "category": "风景"}
    await auth_client.post(f"/api/v1/spaces/{team_id}/pictures", files=files, data=data)

    resp = await auth_client.get(f"/api/v1/spaces/{team_id}/pictures")
    assert resp.status_code == 200
    body = resp.json()
    assert body["total_count"] == 1
    assert body["data"][0]["name"] == "团队图片"


async def test_team_picture_not_in_public_gallery(auth_client: AsyncClient, mocker):
    """团队图片不进入公共图库列表。"""
    _mock_cos(mocker)
    create = await auth_client.post("/api/v1/spaces/team", json={"name": "团队"})
    team_id = create.json()["id"]
    files = {"file": ("t.png", make_png_image(), "image/png")}
    data = {"name": "团队私有图片", "category": "风景"}
    await auth_client.post(f"/api/v1/spaces/{team_id}/pictures", files=files, data=data)

    resp = await auth_client.get("/api/v1/pictures/")
    names = [item["name"] for item in resp.json()["data"]]
    assert "团队私有图片" not in names


async def test_non_member_access_forbidden(
    auth_client_2: AsyncClient, db_session: AsyncSession, test_user: dict
):
    """非团队成员访问团队空间接口 → 403。"""
    team = await SpaceService().create_team(db_session, "团队", test_user)
    resp = await auth_client_2.get(f"/api/v1/spaces/{team['id']}/pictures")
    assert resp.status_code == 403
