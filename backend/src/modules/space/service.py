"""空间模块业务逻辑：空间 CRUD + 配额 + 封禁 + 空间图片管理。"""

import asyncio
import uuid
from io import BytesIO
from typing import Any

from fastapi import UploadFile
from PIL import Image
from sqlalchemy import func, or_, select, update
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.concurrency import run_in_threadpool

from ...infrastructure.config.settings import settings
from ...infrastructure.logging import get_logger
from ..common.exceptions import (
    PictureNotFoundError,
    SpaceBannedError,
    SpaceExistsError,
    SpaceNotFoundError,
    ValidationError,
)
from ..pictures.crud import crud_pictures
from ..pictures.enums import PictureStatus
from ..pictures.models import Picture
from ..pictures.schemas import PictureCreateInternal, PictureListItemRead, PictureRead, PictureUpdate
from ..pictures.service import (
    ALLOWED_FORMATS,
    MAX_FILE_SIZE,
    VALID_CATEGORIES,
    _get_cos_client,
    _parse_tags,
)
from .constants import SPACE_LEVEL_LIMITS
from .crud import crud_spaces
from .enums import SpaceLevel, SpaceStatus
from .models import Space
from .schemas import SpaceCreateInternal, SpaceListRead, SpaceRead

logger = get_logger()

# 每个用户的创建锁（本地锁：进程内串行化同一用户的创建，防并发重复创建）
_space_locks: dict[int, asyncio.Lock] = {}


def _get_space_lock(user_id: int) -> asyncio.Lock:
    """按用户取本地锁。"""
    return _space_locks.setdefault(user_id, asyncio.Lock())


class SpaceService:
    """空间业务服务。"""

    # ------------------------------------------------------------------ 用户功能

    async def create(self, db: AsyncSession, name: str, current_user: dict[str, Any]) -> dict[str, Any]:
        """创建私有空间（每用户仅一个，本地锁 + 事务防并发重复创建）。"""
        user_id = current_user["id"]
        lock = _get_space_lock(user_id)
        async with lock:
            existing = await crud_spaces.get(db=db, user_id=user_id, is_deleted=False)
            if existing:
                raise SpaceExistsError("用户已创建私有空间，每个用户只能创建一个")

            limits = SPACE_LEVEL_LIMITS[SpaceLevel.NORMAL]
            internal = SpaceCreateInternal(
                name=name,
                space_level=SpaceLevel.NORMAL,
                max_size=limits["max_size"],
                max_count=limits["max_count"],
                user_id=user_id,
                status=SpaceStatus.ACTIVE.value,
            )
            created = await crud_spaces.create(db=db, object=internal, schema_to_select=SpaceRead)
            if not created:
                raise ValidationError("创建空间失败")
            return created

    async def get_my(self, db: AsyncSession, current_user: dict[str, Any]) -> dict[str, Any]:
        """我的空间信息（含剩余量）。"""
        space = await self._get_user_space(db, current_user["id"])
        return self._space_info(space)

    async def change_level(self, db: AsyncSession, current_user: dict[str, Any], space_level: int) -> dict[str, Any]:
        """用户自助升级/降级空间级别（预留付费接口）。"""
        space = await self._get_user_space(db, current_user["id"])
        target = int(space_level)
        if target not in SPACE_LEVEL_LIMITS:
            raise ValidationError("无效的空间级别")
        limits = SPACE_LEVEL_LIMITS[target]
        # 降级（或任意级别变更）时，当前用量超过目标级别上限则拒绝
        if space.total_size > limits["max_size"] or space.total_count > limits["max_count"]:
            raise ValidationError("当前空间用量已超过目标级别上限，请先清理后再降级")
        # TODO: 付费接口预留——后续升级需在此处先完成付费校验
        await crud_spaces.update(
            db=db,
            object={"space_level": target, "max_size": limits["max_size"], "max_count": limits["max_count"]},
            id=space.id,
        )
        return self._space_info(await self._get_user_space(db, current_user["id"]))

    # ------------------------------------------------------------------ 管理员功能

    async def list_admin(
        self,
        db: AsyncSession,
        *,
        page: int = 1,
        items_per_page: int = 10,
        name: str | None = None,
        user_id: int | None = None,
        space_level: int | None = None,
    ) -> dict[str, Any]:
        """管理员：分页列表，按名称/所属用户/级别筛选，创建时间倒序。"""
        conditions = [Space.is_deleted == False]  # noqa: E712
        if name:
            conditions.append(Space.name.ilike(f"%{name}%"))
        if user_id is not None:
            conditions.append(Space.user_id == user_id)
        if space_level is not None:
            conditions.append(Space.space_level == space_level)

        count_stmt = select(func.count()).select_from(Space).where(*conditions)
        total = (await db.execute(count_stmt)).scalar() or 0

        stmt = select(Space).where(*conditions).order_by(Space.created_at.desc())
        stmt = stmt.offset((page - 1) * items_per_page).limit(items_per_page)
        rows = (await db.execute(stmt)).scalars().all()
        data = [SpaceListRead.model_validate(s).model_dump() for s in rows]
        return {"data": data, "total_count": total, "has_more": (page * items_per_page) < total}

    async def get_admin(self, db: AsyncSession, space_id: int) -> dict[str, Any]:
        """管理员：空间详情。"""
        space = await self._get_space_or_404(db, space_id)
        return SpaceRead.model_validate(space).model_dump()

    async def update_admin(
        self, db: AsyncSession, space_id: int, name: str | None, space_level: int | None
    ) -> dict[str, Any]:
        """管理员：编辑空间（名称 / 级别）。"""
        space = await self._get_space_or_404(db, space_id)
        update_dict: dict[str, Any] = {}
        if name is not None:
            update_dict["name"] = name
        if space_level is not None:
            target = int(space_level)
            limits = SPACE_LEVEL_LIMITS[target]
            if space.total_size > limits["max_size"] or space.total_count > limits["max_count"]:
                raise ValidationError("当前空间用量已超过目标级别上限，无法降级")
            update_dict["space_level"] = target
            update_dict["max_size"] = limits["max_size"]
            update_dict["max_count"] = limits["max_count"]
        if update_dict:
            await crud_spaces.update(db=db, object=update_dict, id=space_id)
        return SpaceRead.model_validate(await self._get_space_or_404(db, space_id)).model_dump()

    async def delete_admin(self, db: AsyncSession, space_id: int) -> None:
        """管理员：软删除空间 + 级联软删除其下所有图片。"""
        await self._get_space_or_404(db, space_id)
        await db.execute(
            update(Picture)
            .where(Picture.space_id == space_id, Picture.is_deleted == False)  # noqa: E712
            .values(is_deleted=True)
        )
        await crud_spaces.delete(db=db, id=space_id)

    async def set_ban(self, db: AsyncSession, space_id: int, banned: bool) -> dict[str, Any]:
        """管理员：封禁 / 解封。"""
        await self._get_space_or_404(db, space_id)
        status = SpaceStatus.BANNED.value if banned else SpaceStatus.ACTIVE.value
        await crud_spaces.update(db=db, object={"status": status}, id=space_id)
        return SpaceRead.model_validate(await self._get_space_or_404(db, space_id)).model_dump()

    # ------------------------------------------------------------------ 空间图片管理（用户，仅限自己空间）

    async def upload_picture(
        self,
        db: AsyncSession,
        current_user: dict[str, Any],
        file: UploadFile,
        name: str,
        introduction: str | None,
        category: str,
        tags_str: str,
    ) -> dict[str, Any]:
        """空间内上传图片（不审核，直接 approved；软配额不预先阻断）。"""
        space = await self._get_user_space(db, current_user["id"])
        self._check_active(space)

        data = await file.read()
        if not data:
            raise ValidationError("图片文件为空")
        if len(data) > MAX_FILE_SIZE:
            raise ValidationError("图片大小不能超过 10MB")
        if category not in VALID_CATEGORIES:
            raise ValidationError(f"分类必须在预置列表内：{'、'.join(VALID_CATEGORIES)}")

        try:
            img = Image.open(BytesIO(data))
            img.load()
        except Exception as e:
            raise ValidationError("无法解析该图片，仅支持 JPEG/PNG/WebP/GIF") from e
        width, height = img.size
        pic_format = (img.format or "").upper()
        if pic_format not in ALLOWED_FORMATS:
            raise ValidationError(f"不支持的图片格式：{pic_format}")
        pic_scale = round(width / height, 4) if height else None

        tags = _parse_tags(tags_str)

        ext = pic_format.lower()
        key = f"pictures/{uuid.uuid4().hex}.{ext}"
        cos = _get_cos_client()
        await run_in_threadpool(
            cos.put_object,
            Bucket=settings.COS_BUCKET,
            Key=key,
            Body=data,
            ContentType=file.content_type or "application/octet-stream",
        )
        url = f"{settings.COS_BASE_URL}/{key}"
        logger.info(f"空间图片已上传 COS: {key}（{len(data)} bytes，space={space.id}）")

        internal = PictureCreateInternal(
            url=url,
            name=name,
            introduction=introduction,
            category=category,
            tags=tags,
            pic_size=len(data),
            pic_width=width,
            pic_height=height,
            pic_scale=pic_scale,
            pic_format=pic_format,
            color_mode=img.mode,
            user_id=current_user["id"],
            status=PictureStatus.APPROVED.value,
            space_id=space.id,
        )
        created = await crud_pictures.create(db=db, object=internal, schema_to_select=PictureRead)
        if not created:
            raise ValidationError("创建图片记录失败")

        # 软配额：上传后原子更新用量（允许超限，超限软提示）
        await self._add_quota(db, space.id, len(data), 1)
        return created

    async def list_pictures(
        self,
        db: AsyncSession,
        current_user: dict[str, Any],
        *,
        page: int = 1,
        items_per_page: int = 10,
        category: str | None = None,
        keyword: str | None = None,
        sort: str = "time",
    ) -> dict[str, Any]:
        """空间图片列表。"""
        space = await self._get_user_space(db, current_user["id"])
        conditions = [Picture.is_deleted == False, Picture.space_id == space.id]  # noqa: E712
        if category:
            conditions.append(Picture.category == category)
        if keyword:
            kw = f"%{keyword}%"
            conditions.append(
                or_(
                    Picture.name.ilike(kw),
                    Picture.introduction.ilike(kw),
                    Picture.tags.cast(JSONB).contains([keyword]),
                )
            )

        count_stmt = select(func.count()).select_from(Picture).where(*conditions)
        total = (await db.execute(count_stmt)).scalar() or 0

        stmt = select(Picture).where(*conditions)
        if sort == "popularity":
            stmt = stmt.order_by(Picture.download_count.desc(), Picture.created_at.desc())
        else:
            stmt = stmt.order_by(Picture.created_at.desc())
        stmt = stmt.offset((page - 1) * items_per_page).limit(items_per_page)
        rows = (await db.execute(stmt)).scalars().all()
        data = [PictureListItemRead.model_validate(p).model_dump() for p in rows]
        return {"data": data, "total_count": total, "has_more": (page * items_per_page) < total}

    async def get_picture(self, db: AsyncSession, current_user: dict[str, Any], picture_id: int) -> dict[str, Any]:
        """空间图片详情。"""
        space = await self._get_user_space(db, current_user["id"])
        picture = await crud_pictures.get(
            db=db, schema_to_select=PictureRead, id=picture_id, space_id=space.id, is_deleted=False
        )
        if not picture:
            raise PictureNotFoundError(f"图片 {picture_id} 不存在")
        return picture

    async def update_picture(
        self, db: AsyncSession, current_user: dict[str, Any], picture_id: int, data: PictureUpdate
    ) -> dict[str, Any]:
        """编辑空间图片元信息。"""
        space = await self._get_user_space(db, current_user["id"])
        existing = await crud_pictures.get(db=db, id=picture_id, space_id=space.id, is_deleted=False)
        if not existing:
            raise PictureNotFoundError(f"图片 {picture_id} 不存在")
        update_dict = data.model_dump(exclude_unset=True)
        if "tags" in update_dict and update_dict["tags"] is None:
            update_dict["tags"] = []
        await crud_pictures.update(db=db, object=update_dict, id=picture_id)
        return existing

    async def delete_picture(self, db: AsyncSession, current_user: dict[str, Any], picture_id: int) -> None:
        """删除空间图片（回退配额）。"""
        space = await self._get_user_space(db, current_user["id"])
        picture = await crud_pictures.get(db=db, id=picture_id, space_id=space.id, is_deleted=False)
        if not picture:
            raise PictureNotFoundError(f"图片 {picture_id} 不存在")
        await crud_pictures.delete(db=db, id=picture_id)
        await self._add_quota(db, space.id, -(picture.get("pic_size") or 0), -1)

    # ------------------------------------------------------------------ 辅助

    async def _get_user_space(self, db: AsyncSession, user_id: int) -> Space:
        """获取用户 active 空间（ORM 对象），不存在抛 SpaceNotFoundError。"""
        stmt = select(Space).where(Space.user_id == user_id, Space.is_deleted == False)  # noqa: E712
        space = (await db.execute(stmt)).scalar_one_or_none()
        if space is None:
            raise SpaceNotFoundError("用户尚未创建空间")
        return space

    async def _get_space_or_404(self, db: AsyncSession, space_id: int) -> Space:
        """按 id 获取 active 空间（ORM 对象），不存在抛 SpaceNotFoundError。"""
        stmt = select(Space).where(Space.id == space_id, Space.is_deleted == False)  # noqa: E712
        space = (await db.execute(stmt)).scalar_one_or_none()
        if space is None:
            raise SpaceNotFoundError(f"空间 {space_id} 不存在")
        return space

    def _check_active(self, space: Space) -> None:
        """封禁校验。"""
        if space.status == SpaceStatus.BANNED.value:
            raise SpaceBannedError("空间已被封禁")

    def _space_info(self, space: Space) -> dict[str, Any]:
        """构造空间信息（含剩余量，超限时为负）。"""
        return {
            "id": space.id,
            "name": space.name,
            "space_level": space.space_level,
            "max_size": space.max_size,
            "max_count": space.max_count,
            "total_size": space.total_size,
            "total_count": space.total_count,
            "status": space.status,
            "remaining_size": space.max_size - space.total_size,
            "remaining_count": space.max_count - space.total_count,
            "created_at": space.created_at,
        }

    async def _add_quota(self, db: AsyncSession, space_id: int, size_delta: int, count_delta: int) -> None:
        """原子更新空间用量（size/count 增量）。"""
        await db.execute(
            update(Space)
            .where(Space.id == space_id)
            .values(total_size=Space.total_size + size_delta, total_count=Space.total_count + count_delta)
        )
