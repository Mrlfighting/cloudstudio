"""独立云端作品接口，沿用 Session 和 CSRF，不提供公开图片地址。"""

import hashlib
from datetime import UTC, datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, File, Form, HTTPException, Query, Response, UploadFile
from sqlalchemy import select

from ...infrastructure.dependencies import AsyncSessionDep, CurrentUserDep
from . import persistence as service
from .models import BeadPattern as B
from .schemas import RenameRequest, parse_project

router = APIRouter()


@router.post("/")
async def create_pattern(
    db: AsyncSessionDep,
    current_user: CurrentUserDep,
    project: Annotated[str, Form()],
    client_id: Annotated[UUID, Form()],
    source: Annotated[UploadFile | None, File()] = None,
    thumbnail: Annotated[UploadFile | None, File()] = None,
) -> dict:
    """创建/幂等重试，身份不从表单取得。"""
    parsed = parse_project(project)
    files = await service.files_data(source, thumbnail)
    return await service.create(db, current_user["id"], client_id, parsed, files)


@router.get("/")
async def list_patterns(
    db: AsyncSessionDep,
    current_user: CurrentUserDep,
    page: int = Query(1, ge=1),
    items_per_page: int = Query(20, ge=1, le=100),
    keyword: str = Query("", max_length=128),
) -> dict:
    """仅返回本人未删除作品摘要。"""
    return await service.listing(db, current_user["id"], page, items_per_page, keyword.strip())


@router.get("/{pattern_id}")
async def get_pattern(pattern_id: int, db: AsyncSessionDep, current_user: CurrentUserDep) -> dict:
    """取得版本化图纸，图片通过独立鉴权响应读取。"""
    return await service.detail(db, current_user["id"], pattern_id)


@router.put("/{pattern_id}")
async def replace_pattern(
    pattern_id: int,
    db: AsyncSessionDep,
    current_user: CurrentUserDep,
    project: Annotated[str, Form()],
    revision: Annotated[int, Form(ge=1)],
    source: Annotated[UploadFile | None, File()] = None,
    thumbnail: Annotated[UploadFile | None, File()] = None,
) -> dict:
    """完整快照更新；文件省略表示新快照没有该文件。"""
    parsed = parse_project(project)
    files = await service.files_data(source, thumbnail)
    return await service.write(
        db,
        current_user["id"],
        pattern_id,
        revision,
        {
            "name": parsed["name"],
            "project_data": parsed,
            "content_hash": service.content_hash(parsed, files),
            **files,
        },
    )


@router.patch("/{pattern_id}")
async def rename_pattern(
    pattern_id: int,
    body: RenameRequest,
    db: AsyncSessionDep,
    current_user: CurrentUserDep,
) -> dict:
    """只更改名称，不加载图片；使旧创建请求无法把名称改回去。"""
    if not body.name.strip():
        raise HTTPException(422, "名称不能为空")
    old = await service.detail(db, current_user["id"], pattern_id)
    project = {**old["project_data"], "name": body.name.strip(), "updatedAt": datetime.now(UTC).isoformat()}
    return await service.write(
        db,
        current_user["id"],
        pattern_id,
        body.revision,
        {
            "name": project["name"],
            "project_data": project,
            "content_hash": hashlib.sha256(f"rename:{pattern_id}:{body.revision}".encode()).hexdigest(),
        },
    )


@router.delete("/{pattern_id}")
async def delete_pattern(
    pattern_id: int,
    db: AsyncSessionDep,
    current_user: CurrentUserDep,
    revision: int = Query(..., ge=1),
) -> dict:
    """软删除不销毁文件，不提供回收站或恢复 API。"""
    return await service.write(
        db,
        current_user["id"],
        pattern_id,
        revision,
        {
            "is_deleted": True,
            "deleted_at": datetime.now(UTC),
        },
    )


async def image_response(pattern_id: int, db, user: int, kind: str) -> Response:
    """直接选择所需二进制列，不泄露其他文件和原始来源。"""
    row = (
        await db.execute(
            select(getattr(B, f"{kind}_data"), getattr(B, f"{kind}_mime")).where(
                B.id == pattern_id,
                B.user_id == user,
                B.is_deleted.is_(False),
            )
        )
    ).first()
    if row is None or row[0] is None:
        raise HTTPException(404, "图片不存在")
    return Response(
        row[0], media_type=row[1], headers={"Cache-Control": "private, no-store", "X-Content-Type-Options": "nosniff"}
    )


@router.get("/{pattern_id}/source")
async def get_source(pattern_id: int, db: AsyncSessionDep, current_user: CurrentUserDep) -> Response:
    """只读本人工作源。"""
    return await image_response(pattern_id, db, current_user["id"], "source")


@router.get("/{pattern_id}/thumbnail")
async def get_thumbnail(pattern_id: int, db: AsyncSessionDep, current_user: CurrentUserDep) -> Response:
    """缩略图也需登录，不产生永久公开地址。"""
    return await image_response(pattern_id, db, current_user["id"], "thumbnail")
