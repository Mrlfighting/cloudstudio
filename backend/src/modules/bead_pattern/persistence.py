"""拼豆作品持久化：本人隔离、幂等创建与乐观锁，无对象存储副作用。"""

import hashlib
import json
from datetime import UTC, datetime
from io import BytesIO
from uuid import UUID

from fastapi import HTTPException, UploadFile
from PIL import Image
from sqlalchemy import func, select, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.concurrency import run_in_threadpool

from .models import BeadPattern as B
from .service import MAX_BYTES, inspect_image


def image_info(data: bytes, edge: int) -> tuple[str, int, int]:
    """验证完整解码、边长和格式；不将损坏图片存入数据库。"""
    mime = inspect_image(data)
    with Image.open(BytesIO(data)) as image:
        if max(image.size) > edge:
            raise HTTPException(422, f"图片最长边不能超过 {edge}px")
        try:
            image.load()
        except (OSError, ValueError) as error:
            raise HTTPException(415, "图片无法完整解码") from error
        return mime, image.width, image.height


async def files_data(source: UploadFile | None, thumbnail: UploadFile | None) -> dict:
    """按实际读取字节限制文件；缺省工作源明确保存为空。"""
    values: dict = {
        "source_data": None,
        "source_mime": None,
        "source_width": None,
        "source_height": None,
        "source_size": 0,
        "thumbnail_data": None,
        "thumbnail_mime": None,
    }
    for label, file, edge, limit in [("source", source, 1600, MAX_BYTES), ("thumbnail", thumbnail, 256, 512 * 1024)]:
        if file is None:
            continue
        data = await file.read(limit + 1)
        if len(data) > limit:
            raise HTTPException(413, "工作源或缩略图超过大小限制")
        mime, width, height = await run_in_threadpool(image_info, data, edge)
        values[f"{label}_data"] = data
        values[f"{label}_mime"] = mime
        if label == "source":
            values.update(source_width=width, source_height=height, source_size=len(data))
    return values


def content_hash(project: dict, files: dict) -> str:
    """忽略客户端编辑时间；同一次保存重试不能创建重复作品。"""
    snapshot = {k: v for k, v in project.items() if k != "updatedAt"}
    digest = hashlib.sha256(json.dumps(snapshot, sort_keys=True, ensure_ascii=False).encode())
    for field in ("source_data", "thumbnail_data"):
        digest.update(hashlib.sha256(files[field] or b"").digest())
    return digest.hexdigest()


def columns() -> list:
    """明确选择摘要，避免列表携带 JSONB、BYTEA 大字段。"""
    return [
        B.id,
        B.client_id,
        B.name,
        B.revision,
        B.created_at,
        B.updated_at,
        B.project_data["pattern"]["width"].as_integer().label("width"),
        B.project_data["pattern"]["height"].as_integer().label("height"),
        B.project_data["paletteId"].as_string().label("palette_id"),
        (B.source_size > 0).label("has_source"),
        B.thumbnail_mime.is_not(None).label("has_thumbnail"),
    ]


def serialize(row) -> dict:
    """大整数主键以字符串传给 JS，避免精度损失。"""
    result = dict(row)
    result["id"] = str(result["id"])
    result["client_id"] = str(result["client_id"])
    return result


async def detail(db: AsyncSession, user: int, pattern: int) -> dict:
    """每次读取都包含归属及软删除条件。"""
    row = (
        (
            await db.execute(
                select(*columns(), B.project_data).where(
                    B.id == pattern,
                    B.user_id == user,
                    B.is_deleted.is_(False),
                )
            )
        )
        .mappings()
        .first()
    )
    if row is None:
        raise HTTPException(404, "作品不存在")
    return serialize(row)


async def create(db: AsyncSession, user: int, client: UUID, project: dict, files: dict) -> dict:
    """数据库唯一约束处理并发重试；不同内容不静默覆盖同客户端作品。"""
    digest = content_hash(project, files)
    now = datetime.now(UTC)
    values = dict(
        user_id=user,
        client_id=client,
        name=project["name"],
        project_data=project,
        content_hash=digest,
        revision=1,
        created_at=now,
        updated_at=now,
        is_deleted=False,
        deleted_at=None,
        **files,
    )
    try:
        key = (
            await db.execute(
                insert(B).values(**values).on_conflict_do_nothing(constraint="uq_bead_patterns_user_client").returning(B.id)
            )
        ).scalar_one_or_none()
        if key is None:
            row = (
                await db.execute(select(B.id, B.content_hash, B.is_deleted).where(B.user_id == user, B.client_id == client))
            ).one()
            if row.is_deleted or row.content_hash != digest:
                raise HTTPException(409, "该本地作品已有云端记录，请更新原作品或另存为新作品")
            key = row.id
        await db.commit()
    except Exception:
        await db.rollback()
        raise
    return await detail(db, user, key)


async def write(db: AsyncSession, user: int, pattern: int, revision: int, values: dict) -> dict:
    """比较版本与更新在同一条 SQL 完成，避免先查再写的竞争窗口。"""
    try:
        key = (
            await db.execute(
                update(B)
                .where(
                    B.id == pattern,
                    B.user_id == user,
                    B.is_deleted.is_(False),
                    B.revision == revision,
                )
                .values(**values, revision=B.revision + 1, updated_at=datetime.now(UTC))
                .returning(B.id)
            )
        ).scalar_one_or_none()
        if key is None:
            await detail(db, user, pattern)
            raise HTTPException(409, "作品已被其他设备修改，请重新载入或另存为新作品")
        await db.commit()
    except Exception:
        await db.rollback()
        raise
    if values.get("is_deleted"):
        return {"deleted": True}
    return await detail(db, user, pattern)


async def listing(db: AsyncSession, user: int, page: int, size: int, keyword: str) -> dict:
    """稳定按更新时间和主键倒序分页；搜索转义通配符。"""
    filters = [B.user_id == user, B.is_deleted.is_(False)]
    if keyword:
        escaped = keyword.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
        filters.append(B.name.ilike(f"%{escaped}%", escape="\\"))
    total = (await db.execute(select(func.count()).select_from(B).where(*filters))).scalar_one()
    rows = (
        (
            await db.execute(
                select(*columns())
                .where(*filters)
                .order_by(B.updated_at.desc(), B.id.desc())
                .offset((page - 1) * size)
                .limit(size)
            )
        )
        .mappings()
        .all()
    )
    return {"data": [serialize(row) for row in rows], "total_count": total, "page": page, "items_per_page": size}
