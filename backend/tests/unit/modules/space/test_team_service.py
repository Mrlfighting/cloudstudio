"""团队空间服务单元测试。"""

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.common.exceptions import (
    PermissionDeniedError,
    ResourceExistsError,
    SpaceExistsError,
    SpaceNotFoundError,
    TeamMemberNotFoundError,
    UserNotFoundError,
    ValidationError,
)
from src.modules.space.crud import crud_space_users
from src.modules.space.dependencies import require_team_permission
from src.modules.space.enums import SpaceRole, SpaceType
from src.modules.space.rbac import MANAGE_MEMBERS, READ, WRITE
from src.modules.space.service import SpaceService


@pytest.fixture
def space_service() -> SpaceService:
    return SpaceService()


@pytest.mark.asyncio
async def test_create_team_creator_is_admin(
    space_service: SpaceService, db_session: AsyncSession, test_user: dict
):
    created = await space_service.create_team(db_session, "我的团队", test_user)
    assert created["space_type"] == SpaceType.TEAM
    assert created["user_id"] == test_user["id"]
    # 创建者自动成为管理员
    member = await crud_space_users.get(
        db=db_session, space_id=created["id"], user_id=test_user["id"]
    )
    assert member is not None
    assert member["space_role"] == SpaceRole.ADMIN.value


@pytest.mark.asyncio
async def test_create_team_duplicate_raises(
    space_service: SpaceService, db_session: AsyncSession, test_user: dict
):
    await space_service.create_team(db_session, "团队A", test_user)
    with pytest.raises(SpaceExistsError):
        await space_service.create_team(db_session, "团队B", test_user)


@pytest.mark.asyncio
async def test_private_and_team_coexist(
    space_service: SpaceService, db_session: AsyncSession, test_user: dict
):
    """同一用户可同时拥有 1 个私有空间 + 1 个团队空间，互不串扰。"""
    private = await space_service.create(db_session, "私有空间", test_user)
    team = await space_service.create_team(db_session, "团队空间", test_user)

    assert private["space_type"] == SpaceType.PRIVATE
    assert team["space_type"] == SpaceType.TEAM
    # 私有空间查询只返回私有，团队查询只返回团队
    info = await space_service.get_my(db_session, test_user)
    assert info["id"] == private["id"]
    team_info = await space_service.get_my_team(db_session, test_user)
    assert team_info["id"] == team["id"]


@pytest.mark.asyncio
async def test_get_my_team_not_found(
    space_service: SpaceService, db_session: AsyncSession, test_user: dict
):
    with pytest.raises(SpaceNotFoundError):
        await space_service.get_my_team(db_session, test_user)


@pytest.mark.asyncio
async def test_add_member_success(
    space_service: SpaceService, db_session: AsyncSession, test_user: dict, test_user_2: dict
):
    team = await space_service.create_team(db_session, "团队", test_user)
    await space_service.add_member(db_session, team["id"], test_user_2["id"], SpaceRole.EDITOR)

    members = await space_service.list_members(db_session, team["id"])
    assert len(members) == 2
    roles = {m["user_id"]: m["space_role"] for m in members}
    assert roles[test_user["id"]] == SpaceRole.ADMIN.value
    assert roles[test_user_2["id"]] == SpaceRole.EDITOR.value


@pytest.mark.asyncio
async def test_add_member_duplicate_raises(
    space_service: SpaceService, db_session: AsyncSession, test_user: dict, test_user_2: dict
):
    team = await space_service.create_team(db_session, "团队", test_user)
    await space_service.add_member(db_session, team["id"], test_user_2["id"], SpaceRole.EDITOR)
    with pytest.raises(ResourceExistsError):
        await space_service.add_member(db_session, team["id"], test_user_2["id"], SpaceRole.VIEWER)


@pytest.mark.asyncio
async def test_add_member_nonexistent_user_raises(
    space_service: SpaceService, db_session: AsyncSession, test_user: dict
):
    team = await space_service.create_team(db_session, "团队", test_user)
    with pytest.raises(UserNotFoundError):
        await space_service.add_member(db_session, team["id"], 999999, SpaceRole.VIEWER)


@pytest.mark.asyncio
async def test_remove_member_success(
    space_service: SpaceService, db_session: AsyncSession, test_user: dict, test_user_2: dict
):
    team = await space_service.create_team(db_session, "团队", test_user)
    await space_service.add_member(db_session, team["id"], test_user_2["id"], SpaceRole.EDITOR)
    await space_service.remove_member(db_session, team["id"], test_user_2["id"])

    members = await space_service.list_members(db_session, team["id"])
    assert len(members) == 1
    assert members[0]["user_id"] == test_user["id"]


@pytest.mark.asyncio
async def test_remove_member_not_found_raises(
    space_service: SpaceService, db_session: AsyncSession, test_user: dict, test_user_2: dict
):
    team = await space_service.create_team(db_session, "团队", test_user)
    with pytest.raises(TeamMemberNotFoundError):
        await space_service.remove_member(db_session, team["id"], test_user_2["id"])


@pytest.mark.asyncio
async def test_remove_owner_raises(
    space_service: SpaceService, db_session: AsyncSession, test_user: dict
):
    team = await space_service.create_team(db_session, "团队", test_user)
    with pytest.raises(ValidationError):
        await space_service.remove_member(db_session, team["id"], test_user["id"])


@pytest.mark.asyncio
async def test_update_member_role_success(
    space_service: SpaceService, db_session: AsyncSession, test_user: dict, test_user_2: dict
):
    team = await space_service.create_team(db_session, "团队", test_user)
    await space_service.add_member(db_session, team["id"], test_user_2["id"], SpaceRole.VIEWER)
    updated = await space_service.update_member_role(db_session, team["id"], test_user_2["id"], SpaceRole.EDITOR)
    assert updated["space_role"] == SpaceRole.EDITOR.value


@pytest.mark.asyncio
async def test_update_owner_role_raises(
    space_service: SpaceService, db_session: AsyncSession, test_user: dict
):
    team = await space_service.create_team(db_session, "团队", test_user)
    with pytest.raises(ValidationError):
        await space_service.update_member_role(db_session, team["id"], test_user["id"], SpaceRole.VIEWER)


@pytest.mark.asyncio
async def test_team_settings_upgrade(
    space_service: SpaceService, db_session: AsyncSession, test_user: dict
):
    team = await space_service.create_team(db_session, "团队", test_user)
    updated = await space_service.update_team_settings(db_session, team["id"], name=None, space_level=1)
    assert updated["space_level"] == 1
    assert updated["max_size"] == 25 * 1024**3
    assert updated["max_count"] == 5000


@pytest.mark.asyncio
async def test_require_team_permission_matrix(
    space_service: SpaceService, db_session: AsyncSession, test_user: dict, test_user_2: dict
):
    """权限矩阵：viewer 无写权限，editor 有写权限，admin 有成员管理权限，非成员全拒。"""
    team = await space_service.create_team(db_session, "团队", test_user)  # test_user = admin
    await space_service.add_member(db_session, team["id"], test_user_2["id"], SpaceRole.VIEWER)
    admin_user = {"id": test_user["id"]}
    viewer_user = {"id": test_user_2["id"]}
    non_member = {"id": 999999}

    write_dep = require_team_permission(WRITE)
    manage_dep = require_team_permission(MANAGE_MEMBERS)
    read_dep = require_team_permission(READ)

    # admin 可写、可管理成员
    await write_dep(space_id=team["id"], db=db_session, current_user=admin_user)
    await manage_dep(space_id=team["id"], db=db_session, current_user=admin_user)
    # viewer 只可读，不可写、不可管理成员
    await read_dep(space_id=team["id"], db=db_session, current_user=viewer_user)
    with pytest.raises(PermissionDeniedError):
        await write_dep(space_id=team["id"], db=db_session, current_user=viewer_user)
    with pytest.raises(PermissionDeniedError):
        await manage_dep(space_id=team["id"], db=db_session, current_user=viewer_user)
    # 非成员全拒
    with pytest.raises(PermissionDeniedError):
        await read_dep(space_id=team["id"], db=db_session, current_user=non_member)


@pytest.mark.asyncio
async def test_list_joined_teams(
    space_service: SpaceService, db_session: AsyncSession, test_user: dict, test_user_2: dict
):
    """我加入（含我创建）的团队空间列表：创建者为 admin，被邀请成员为对应角色。"""
    team = await space_service.create_team(db_session, "团队", test_user)
    await space_service.add_member(db_session, team["id"], test_user_2["id"], SpaceRole.EDITOR)

    mine = await space_service.list_joined_teams(db_session, test_user)
    assert len(mine) == 1
    assert mine[0]["id"] == team["id"]
    assert mine[0]["space_role"] == SpaceRole.ADMIN.value

    joined = await space_service.list_joined_teams(db_session, test_user_2)
    assert len(joined) == 1
    assert joined[0]["space_role"] == SpaceRole.EDITOR.value
