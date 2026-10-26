"""图片模块业务逻辑：COS 上传、图像解析、列表/详情/审核/下载。"""

import json
import uuid
from typing import Any, cast

from fastapi import UploadFile
from qcloud_cos import CosConfig, CosS3Client
from sqlalchemy import func, or_, select, update
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.concurrency import run_in_threadpool

from ...infrastructure.cache.two_level import get_cache_manager
from ...infrastructure.config.settings import settings
from ...infrastructure.image_search import ImageSearchResponse, search_image
from ...infrastructure.images import CONTENT_TYPES, read_upload_image
from ...infrastructure.logging import get_logger
from ..common.exceptions import PictureNotFoundError, ValidationError
from .cache import LIST_KEY_PREFIX, build_detail_key
from .crud import crud_pictures
from .enums import PictureCategory, PictureStatus
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
VALID_CATEGORIES = {cat.value for cat in PictureCategory}


def _get_cos_client() -> CosS3Client:
    """构造腾讯云 COS 客户端（同步 SDK，调用方需放入线程池执行）。"""
    return CosS3Client(
        CosConfig(
            Region=settings.COS_REGION,
            SecretId=settings.COS_SECRET_ID,
            SecretKey=settings.COS_SECRET_KEY,
            Timeout=10,
        ),
        retry=1,
    )


def _parse_tags(tags_str: str) -> list[str]:
    """解析标签：JSON 数组字符串 → list[str]。"""
    try:
        tags = json.loads(tags_str) if tags_str else []
    except json.JSONDecodeError as e:
        raise ValidationError('标签格式错误，应为 JSON 数组字符串，如 ["风景","自然"]') from e
    if not isinstance(tags, list) or not all(isinstance(t, str) for t in tags):
        raise ValidationError("标签格式错误，应为字符串数组")
    return tags


async def _invalidate_picture_cache(picture_id: int | None = None) -> None:
    """写操作后失效相关缓存：详情 + 全部列表前缀。"""
    manager = get_cache_manager()
    if manager is None or not manager.enabled:
        return
    try:
        if picture_id is not None:
            await manager.evict(build_detail_key(picture_id))
        await manager.invalidate_by_prefix(LIST_KEY_PREFIX + ":")
    except Exception:
        # 已提交的写入不因辅助缓存故障返回失败；公共可见性直接以数据库为准。
        logger.warning("图片缓存失效失败，将依赖过期回收")


async def _remove_failed_upload(cos: CosS3Client, key: str) -> None:
    """数据库写入失败时补偿删除刚上传的对象，不覆盖原始异常。"""
    try:
        await run_in_threadpool(cos.delete_object, Bucket=settings.COS_BUCKET, Key=key)
    except Exception:
        logger.error("上传回滚的对象清理失败，需按对象键人工核查", extra={"object_key": key})


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
        if category not in VALID_CATEGORIES:
            raise ValidationError(f"分类必须在预置列表内：{'、'.join(VALID_CATEGORIES)}")
        tags = _parse_tags(tags_str)
        image = await read_upload_image(file)
        data, width, height, pic_format = image.data, image.width, image.height, image.format
        color_mode = image.mode
        image.preview.close()
        pic_scale = round(width / height, 4)

        # 上传 COS（同步 SDK 放线程池，避免阻塞事件循环）
        ext = pic_format.lower()
        key = f"pictures/{uuid.uuid4().hex}.{ext}"
        cos = _get_cos_client()
        try:
            await run_in_threadpool(
                cos.put_object,
                Bucket=settings.COS_BUCKET,
                Key=key,
                Body=data,
                ContentType=CONTENT_TYPES[pic_format],
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
                color_mode=color_mode,
                user_id=current_user["id"],
            )
            created = await crud_pictures.create(db=db, object=internal, schema_to_select=PictureRead, commit=False)
            if not created:
                raise ValidationError("创建图片记录失败")
            await db.commit()
        except Exception:
            await db.rollback()
            await _remove_failed_upload(cos, key)
            raise
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
        # 公共图库隔离：仅展示 space_id 为 NULL 的图片，空间图片不进入公共列表/搜索
        conditions = [Picture.is_deleted == False, Picture.space_id.is_(None)]  # noqa: E712
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

    async def list_user(
        self,
        db: AsyncSession,
        *,
        page: int = 1,
        items_per_page: int = 10,
        category: str | None = None,
        keyword: str | None = None,
        sort: str = "time",
    ) -> dict[str, Any]:
        """公共列表直接读取数据库，保证审核撤回在所有实例即时生效。"""
        return await self._list(
            db,
            page=page,
            items_per_page=items_per_page,
            status=PictureStatus.APPROVED.value,
            category=category,
            keyword=keyword,
            sort=sort,
        )

    async def list_admin(
        self,
        db: AsyncSession,
        *,
        page: int = 1,
        items_per_page: int = 10,
        category: str | None = None,
        keyword: str | None = None,
        sort: str = "time",
        status: str | None = None,
    ) -> dict[str, Any]:
        """管理端：全状态列表，可选按状态过滤。"""
        return await self._list(
            db,
            page=page,
            items_per_page=items_per_page,
            status=status,
            category=category,
            keyword=keyword,
            sort=sort,
        )

    async def list_my(
        self,
        db: AsyncSession,
        user_id: int,
        *,
        page: int = 1,
        items_per_page: int = 10,
        category: str | None = None,
        keyword: str | None = None,
        sort: str = "time",
        status: str | None = None,
    ) -> dict[str, Any]:
        """我的上传：当前用户上传的全部图片（全状态，含拒绝理由）。"""
        return await self._list(
            db,
            page=page,
            items_per_page=items_per_page,
            status=status,
            category=category,
            keyword=keyword,
            sort=sort,
            user_id=user_id,
        )

    async def get(self, db: AsyncSession, picture_id: int, *, require_approved: bool = False) -> dict[str, Any]:
        """详情以数据库为准，不从可能过期的进程缓存读取权限状态。"""
        # 公共图库隔离：仅访问 space_id 为 NULL 的图片
        filters: dict[str, Any] = {"id": picture_id, "is_deleted": False, "space_id": None}
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
        """下载：下载次数 +1，返回 COS URL（仅已发布，公共图库隔离）。"""
        # 数据库内原子递增，避免并发读改写丢失下载次数。
        result = await db.execute(
            update(Picture)
            .where(
                Picture.id == picture_id,
                Picture.is_deleted.is_(False),
                Picture.status == PictureStatus.APPROVED.value,
                Picture.space_id.is_(None),
            )
            .values(download_count=Picture.download_count + 1)
            .returning(Picture.url)
        )
        url = result.scalar_one_or_none()
        if url is None:
            raise PictureNotFoundError(f"图片 {picture_id} 不存在或未发布")
        await db.commit()
        await _invalidate_picture_cache(picture_id)
        return str(url)

    async def search_similar(self, db: AsyncSession, picture_id: int) -> ImageSearchResponse:
        """以图搜图：对已发布公共图库图片搜索相似图片。"""
        picture = await self.get(db, picture_id, require_approved=True)
        return await search_image(picture["url"])
