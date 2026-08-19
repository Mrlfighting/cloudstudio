"""图片模块业务逻辑：COS 上传、图像解析、列表/详情/审核/下载。"""

import json
import uuid
from io import BytesIO
from typing import Any, cast

from fastapi import UploadFile
from PIL import Image
from qcloud_cos import CosConfig, CosS3Client
from sqlalchemy import func, or_, select
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.concurrency import run_in_threadpool

from ...infrastructure.cache.method_cache import cached
from ...infrastructure.cache.two_level import get_cache_manager
from ...infrastructure.config.settings import settings
from ...infrastructure.logging import get_logger
from ..common.exceptions import PictureNotFoundError, ValidationError
from .cache import DETAIL_TTL, LIST_KEY_PREFIX, build_detail_key, build_list_key, list_ttl
from .crud import crud_pictures
from .enums import PictureCategory, PictureFormat, PictureStatus
from .models import Picture
from .schemas import (
    PictureCreateInternal,
    PictureListItemRead,
    PictureRead,
    PictureStatusUpdate,
    PictureUpdate,
)

logger = get_logger()

# 上传限制：最大 10MB，白名单格式
MAX_FILE_SIZE = 10 * 1024 * 1024
ALLOWED_FORMATS = {fmt.value for fmt in PictureFormat}
VALID_CATEGORIES = {cat.value for cat in PictureCategory}


def _get_cos_client() -> CosS3Client:
    """构造腾讯云 COS 客户端（同步 SDK，调用方需放入线程池执行）。"""
    return CosS3Client(
        CosConfig(
            Region=settings.COS_REGION,
            SecretId=settings.COS_SECRET_ID,
            SecretKey=settings.COS_SECRET_KEY,
        )
    )


def _parse_tags(tags_str: str) -> list[str]:
    """解析标签：JSON 数组字符串 → list[str]。"""
    try:
        tags = json.loads(tags_str) if tags_str else []
    except json.JSONDecodeError as e:
        raise ValidationError("标签格式错误，应为 JSON 数组字符串，如 [\"风景\",\"自然\"]") from e
    if not isinstance(tags, list) or not all(isinstance(t, str) for t in tags):
        raise ValidationError("标签格式错误，应为字符串数组")
    return tags


def _detail_key(self: Any, db: AsyncSession, picture_id: int, *, require_approved: bool = False) -> str:
    """详情缓存 key 构造器（忽略 self/db/require_approved）。"""
    return build_detail_key(picture_id)


def _user_list_key(
    self: Any,
    db: AsyncSession,
    *,
    page: int,
    items_per_page: int,
    category: str | None,
    keyword: str | None,
    sort: str,
) -> str:
    """用户端列表缓存 key 构造器。"""
    return build_list_key("public", category, keyword, sort, page, items_per_page)


def _user_list_ttl(
    self: Any,
    db: AsyncSession,
    *,
    page: int,
    items_per_page: int,
    category: str | None,
    keyword: str | None,
    sort: str,
) -> int:
    """用户端列表 TTL：按 sort 差异化。"""
    return list_ttl(sort)


async def _invalidate_picture_cache(picture_id: int | None = None) -> None:
    """写操作后失效相关缓存：详情 + 全部列表前缀。"""
    manager = get_cache_manager()
    if manager is None or not manager.enabled:
        return
    if picture_id is not None:
        await manager.evict(build_detail_key(picture_id))
    await manager.invalidate_by_prefix(LIST_KEY_PREFIX + ":")


class PictureService:
    """图片业务服务。"""

    async def upload(
        self,
        file: UploadFile,
        name: str,
        introduction: str | None,
        category: str,
        tags_str: str,
        db: AsyncSession,
        current_user: dict[str, Any],
    ) -> dict[str, Any]:
        """上传图片：校验 → 解析基础信息 → 上传 COS → 落库（pending）。"""
        data = await file.read()
        if not data:
            raise ValidationError("图片文件为空")
        if len(data) > MAX_FILE_SIZE:
            raise ValidationError("图片大小不能超过 10MB")

        if category not in VALID_CATEGORIES:
            raise ValidationError(f"分类必须在预置列表内：{'、'.join(VALID_CATEGORIES)}")

        # Pillow 实际解析（校验真实格式 + 提取宽高/格式/色彩模式）
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

        # 上传 COS（同步 SDK 放线程池，避免阻塞事件循环）
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
        logger.info(f"图片已上传 COS: {key}（{len(data)} bytes）")

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
        )
        created = await crud_pictures.create(db=db, object=internal, schema_to_select=PictureRead)
        if not created:
            raise ValidationError("创建图片记录失败")
        await _invalidate_picture_cache()
        return created

    async def _list(
        self,
        db: AsyncSession,
        *,
        page: int,
        items_per_page: int,
        status: str | None,
        category: str | None,
        keyword: str | None,
        sort: str,
        user_id: int | None = None,
    ) -> dict[str, Any]:
        """通用列表查询，返回 fastcrud GetMultiResponseDict 形状。"""
        conditions = [Picture.is_deleted == False]  # noqa: E712
        if status:
            conditions.append(Picture.status == status)
        if category:
            conditions.append(Picture.category == category)
        if user_id is not None:
            conditions.append(Picture.user_id == user_id)
        if keyword:
            kw = f"%{keyword}%"
            conditions.append(
                or_(
                    Picture.name.ilike(kw),
                    Picture.introduction.ilike(kw),
                    # 标签用 JSONB @> 结构匹配：JSON 列可能被 ensure_ascii 转义，ILIKE 匹配不到中文
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
        # 注意：返回 key 用 total_count（与 fastcrud paginated_response 读取的 key 一致）
        return {"data": data, "total_count": total, "has_more": (page * items_per_page) < total}

    @cached(key_prefix="pic:list", ttl=_user_list_ttl, key_builder=_user_list_key)
    async def list_user(
        self, db: AsyncSession, *, page: int = 1, items_per_page: int = 10,
        category: str | None = None, keyword: str | None = None, sort: str = "time",
    ) -> dict[str, Any]:
        """用户端：仅已发布（approved）+ 未删除（二级缓存）。"""
        return await self._list(
            db, page=page, items_per_page=items_per_page,
            status=PictureStatus.APPROVED.value, category=category, keyword=keyword, sort=sort,
        )

    async def list_admin(
        self, db: AsyncSession, *, page: int = 1, items_per_page: int = 10,
        category: str | None = None, keyword: str | None = None, sort: str = "time",
        status: str | None = None,
    ) -> dict[str, Any]:
        """管理端：全状态列表，可选按状态过滤。"""
        return await self._list(
            db, page=page, items_per_page=items_per_page,
            status=status, category=category, keyword=keyword, sort=sort,
        )

    async def list_my(
        self, db: AsyncSession, user_id: int, *, page: int = 1, items_per_page: int = 10,
        category: str | None = None, keyword: str | None = None, sort: str = "time",
        status: str | None = None,
    ) -> dict[str, Any]:
        """我的上传：当前用户上传的全部图片（全状态，含拒绝理由）。"""
        return await self._list(
            db, page=page, items_per_page=items_per_page,
            status=status, category=category, keyword=keyword, sort=sort, user_id=user_id,
        )

    @cached(key_prefix="pic:detail", ttl=DETAIL_TTL, key_builder=_detail_key, track_hot=True)
    async def get(self, db: AsyncSession, picture_id: int, *, require_approved: bool = False) -> dict[str, Any]:
        """详情。用户端 require_approved=True 只读已发布（二级缓存 + 热key探测）。"""
        filters: dict[str, Any] = {"id": picture_id, "is_deleted": False}
        if require_approved:
            filters["status"] = PictureStatus.APPROVED.value
        picture = await crud_pictures.get(db=db, schema_to_select=PictureRead, **filters)
        if not picture:
            raise PictureNotFoundError(f"图片 {picture_id} 不存在")
        return cast(dict[str, Any], picture)

    async def update(self, db: AsyncSession, picture_id: int, data: PictureUpdate) -> dict[str, Any]:
        """编辑图片元信息（不含文件）。"""
        existing = await crud_pictures.get(db=db, id=picture_id, is_deleted=False)
        if not existing:
            raise PictureNotFoundError(f"图片 {picture_id} 不存在")

        update_dict = data.model_dump(exclude_unset=True)
        if "tags" in update_dict and update_dict["tags"] is None:
            update_dict["tags"] = []
        # 已确认图片存在；FastCRUD update 未指定 return_columns 时可能返回 None，不代表失败
        await crud_pictures.update(db=db, object=update_dict, id=picture_id)
        await _invalidate_picture_cache(picture_id)
        return existing

    async def audit(self, db: AsyncSession, picture_id: int, data: PictureStatusUpdate) -> dict[str, Any]:
        """管理员审核：approved / rejected。通过时清空 review_reason，拒绝时保存理由。"""
        existing = await crud_pictures.get(db=db, id=picture_id, is_deleted=False)
        if not existing:
            raise PictureNotFoundError(f"图片 {picture_id} 不存在")
        update_dict: dict[str, Any] = {"status": data.status}
        if data.status == PictureStatus.APPROVED.value:
            update_dict["review_reason"] = None
        else:
            update_dict["review_reason"] = data.review_reason
        await crud_pictures.update(db=db, object=update_dict, id=picture_id)
        await _invalidate_picture_cache(picture_id)
        return existing

    async def delete(self, db: AsyncSession, picture_id: int) -> None:
        """软删除（is_deleted=True）。"""
        existing = await crud_pictures.get(db=db, id=picture_id, is_deleted=False)
        if not existing:
            raise PictureNotFoundError(f"图片 {picture_id} 不存在")
        await crud_pictures.delete(db=db, id=picture_id)
        await _invalidate_picture_cache(picture_id)

    async def download(self, db: AsyncSession, picture_id: int) -> str:
        """下载：下载次数 +1，返回 COS URL（仅已发布）。"""
        picture = await crud_pictures.get(
            db=db, id=picture_id, is_deleted=False, status=PictureStatus.APPROVED.value,
        )
        if not picture:
            raise PictureNotFoundError(f"图片 {picture_id} 不存在或未发布")
        new_count = (picture.get("download_count") or 0) + 1
        await crud_pictures.update(db=db, object={"download_count": new_count}, id=picture_id)
        # 下载计数变化，失效详情缓存；popularity 列表靠短 TTL 自愈
        await _invalidate_picture_cache(picture_id)
        return cast(str, picture["url"])
