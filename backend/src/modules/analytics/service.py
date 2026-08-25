"""图库分析业务逻辑：基于现有数据表的只读聚合统计。

统计口径：
- 公共图库图片 = ``space_id IS NULL AND status='approved' AND is_deleted=False``
- 私有空间图片 = ``space_id = 用户空间id AND is_deleted=False``
- 所有查询均带 ``is_deleted == False``（FastCRUD 不自动加）。
"""

from datetime import datetime
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.asyncio import AsyncSession

from ...infrastructure.cache.method_cache import cached
from ..pictures.enums import PictureStatus
from ..pictures.models import Picture
from ..space.models import Space
from ..user.models import User
from .cache import ANALYTICS_TTL
from .schemas import (
    CategoryStat,
    GalleryOverview,
    MySpaceOverview,
    MyTopPicture,
    SpaceRankItem,
    SpacesOverview,
    StorageTrendPoint,
    TagStat,
    TopUploader,
    TrendPoint,
)

# 公共图库图片过滤条件（已发布、未删除）
_PUBLIC = [
    Picture.is_deleted == False,  # noqa: E712
    Picture.space_id.is_(None),
    Picture.status == PictureStatus.APPROVED.value,
]


def _format_period(period: datetime, granularity: str) -> str:
    """把 date_trunc 结果格式化为字符串（day/week→日期，month→年月）。"""
    if granularity == "month":
        return period.strftime("%Y-%m")
    return period.strftime("%Y-%m-%d")


class AnalyticsService:
    """图库分析服务（只读聚合）。"""

    # ------------------------------------------------------------------ 公共图库（管理员）

    @cached(key_prefix="analytics:gallery:overview", ttl=ANALYTICS_TTL)
    async def get_gallery_overview(self, db: AsyncSession) -> dict[str, Any]:
        """公共图库总量：图片总数、总存储容量、总下载量。"""
        stmt = (
            select(
                func.count(Picture.id),
                func.coalesce(func.sum(Picture.pic_size), 0),
                func.coalesce(func.sum(Picture.download_count), 0),
            )
            .select_from(Picture)
            .where(*_PUBLIC)
        )
        row = (await db.execute(stmt)).one()
        return GalleryOverview(
            total_pictures=row[0],
            total_size=row[1],
            total_downloads=row[2],
        ).model_dump()

    @cached(key_prefix="analytics:gallery:trend", ttl=ANALYTICS_TTL)
    async def get_gallery_trend(self, db: AsyncSession, granularity: str) -> list[dict[str, Any]]:
        """公共图库上传量增长趋势（按日/周/月分桶）。"""
        period = func.date_trunc(granularity, Picture.created_at).label("period")
        stmt = (
            select(period, func.count(Picture.id))
            .select_from(Picture)
            .where(*_PUBLIC)
            .group_by(period)
            .order_by(period)
        )
        rows = (await db.execute(stmt)).all()
        return [
            TrendPoint(period=_format_period(r[0], granularity), count=r[1]).model_dump()
            for r in rows
        ]

    @cached(key_prefix="analytics:gallery:category", ttl=ANALYTICS_TTL)
    async def get_gallery_category(self, db: AsyncSession) -> list[dict[str, Any]]:
        """公共图库分类分布（数量 + 占比 + 容量）。"""
        stmt = (
            select(
                Picture.category,
                func.count(Picture.id),
                func.coalesce(func.sum(Picture.pic_size), 0),
            )
            .select_from(Picture)
            .where(*_PUBLIC)
            .group_by(Picture.category)
            .order_by(func.count(Picture.id).desc())
        )
        rows = (await db.execute(stmt)).all()
        total = sum(r[1] for r in rows)
        return [
            CategoryStat(
                category=r[0] or "未分类",
                count=r[1],
                total_size=r[2],
                ratio=round(r[1] / total, 4) if total else 0.0,
            ).model_dump()
            for r in rows
        ]

    @cached(key_prefix="analytics:gallery:tags", ttl=ANALYTICS_TTL)
    async def get_gallery_tags(self, db: AsyncSession, limit: int) -> list[dict[str, Any]]:
        """公共图库热门标签 TOP N（JSON→jsonb 拆解聚合）。"""
        tag_expr = func.jsonb_array_elements_text(Picture.tags.cast(JSONB)).label("tag")
        stmt = (
            select(tag_expr, func.count(Picture.id))
            .select_from(Picture)
            .where(*_PUBLIC)
            .group_by(tag_expr)
            .order_by(func.count(Picture.id).desc())
            .limit(limit)
        )
        rows = (await db.execute(stmt)).all()
        return [TagStat(tag=r[0], count=r[1]).model_dump() for r in rows]

    @cached(key_prefix="analytics:gallery:top-uploaders", ttl=ANALYTICS_TTL)
    async def get_gallery_top_uploaders(self, db: AsyncSession, limit: int) -> list[dict[str, Any]]:
        """公共图库上传者排行 TOP N（按上传图片数，join user 取展示名）。"""
        stmt = (
            select(
                Picture.user_id,
                func.count(Picture.id),
                User.name,
                User.username,
            )
            .join(User, User.id == Picture.user_id)
            .where(*_PUBLIC)
            .group_by(Picture.user_id, User.name, User.username)
            .order_by(func.count(Picture.id).desc())
            .limit(limit)
        )
        rows = (await db.execute(stmt)).all()
        return [
            TopUploader(user_id=r[0], name=r[2], username=r[3], count=r[1]).model_dump()
            for r in rows
        ]

    @cached(key_prefix="analytics:gallery:storage-trend", ttl=ANALYTICS_TTL)
    async def get_gallery_storage_trend(
        self, db: AsyncSession, granularity: str
    ) -> list[dict[str, Any]]:
        """公共图库存储容量趋势（按日/周/月分桶）。"""
        period = func.date_trunc(granularity, Picture.created_at).label("period")
        stmt = (
            select(period, func.coalesce(func.sum(Picture.pic_size), 0))
            .select_from(Picture)
            .where(*_PUBLIC)
            .group_by(period)
            .order_by(period)
        )
        rows = (await db.execute(stmt)).all()
        return [
            StorageTrendPoint(period=_format_period(r[0], granularity), total_size=r[1]).model_dump()
            for r in rows
        ]

    # ------------------------------------------------------------------ 空间大盘（管理员）

    @cached(key_prefix="analytics:spaces:overview", ttl=ANALYTICS_TTL)
    async def get_spaces_overview(self, db: AsyncSession) -> dict[str, Any]:
        """空间大盘：空间总数、总容量、总使用、使用率、平均图片数。"""
        stmt = (
            select(
                func.count(Space.id),
                func.coalesce(func.sum(Space.max_size), 0),
                func.coalesce(func.sum(Space.total_size), 0),
                func.coalesce(func.avg(Space.total_count), 0),
            )
            .select_from(Space)
            .where(Space.is_deleted == False)  # noqa: E712
        )
        row = (await db.execute(stmt)).one()
        total_capacity = row[1]
        total_used = row[2]
        return SpacesOverview(
            total_spaces=row[0],
            total_capacity=total_capacity,
            total_used=total_used,
            usage_rate=round(total_used / total_capacity, 4) if total_capacity else 0.0,
            avg_pictures_per_space=round(float(row[3]), 2),
        ).model_dump()

    @cached(key_prefix="analytics:spaces:ranking", ttl=ANALYTICS_TTL)
    async def get_spaces_ranking(
        self, db: AsyncSession, limit: int, sort: str
    ) -> list[dict[str, Any]]:
        """空间排行 TOP N（按图片数量或容量使用量排序）。"""
        order_col = Space.total_count.desc() if sort == "count" else Space.total_size.desc()
        stmt = (
            select(
                Space.id,
                Space.name,
                Space.user_id,
                Space.space_level,
                Space.total_count,
                Space.total_size,
                User.username,
            )
            .join(User, User.id == Space.user_id)
            .where(Space.is_deleted == False)  # noqa: E712
            .order_by(order_col)
            .limit(limit)
        )
        rows = (await db.execute(stmt)).all()
        return [
            SpaceRankItem(
                space_id=r[0],
                name=r[1],
                user_id=r[2],
                space_level=r[3],
                total_count=r[4],
                total_size=r[5],
                username=r[6],
            ).model_dump()
            for r in rows
        ]

    # ------------------------------------------------------------------ 我的空间（用户）

    async def get_my_overview(self, db: AsyncSession, user_id: int) -> dict[str, Any]:
        """个人空间摘要：数量/限额、容量/容量百分比。"""
        space = await self._get_user_space(db, user_id)
        if space is None:
            return MySpaceOverview(
                space_id=None,
                picture_count=0,
                max_count=0,
                count_usage=0.0,
                total_size=0,
                max_size=0,
                size_usage=0.0,
            ).model_dump()
        return MySpaceOverview(
            space_id=space.id,
            picture_count=space.total_count,
            max_count=space.max_count,
            count_usage=round(space.total_count / space.max_count, 4) if space.max_count else 0.0,
            total_size=space.total_size,
            max_size=space.max_size,
            size_usage=round(space.total_size / space.max_size, 4) if space.max_size else 0.0,
        ).model_dump()

    async def get_my_trend(
        self, db: AsyncSession, user_id: int, granularity: str
    ) -> list[dict[str, Any]]:
        """个人上传趋势（按日/周/月分桶）。"""
        space_id = await self._get_user_space_id(db, user_id)
        if space_id is None:
            return []
        period = func.date_trunc(granularity, Picture.created_at).label("period")
        stmt = (
            select(period, func.count(Picture.id))
            .select_from(Picture)
            .where(Picture.is_deleted == False, Picture.space_id == space_id)  # noqa: E712
            .group_by(period)
            .order_by(period)
        )
        rows = (await db.execute(stmt)).all()
        return [
            TrendPoint(period=_format_period(r[0], granularity), count=r[1]).model_dump()
            for r in rows
        ]

    async def get_my_top_pictures(
        self, db: AsyncSession, user_id: int, limit: int
    ) -> list[dict[str, Any]]:
        """个人热门图片 TOP N（按下载量排序）。"""
        space_id = await self._get_user_space_id(db, user_id)
        if space_id is None:
            return []
        stmt = (
            select(Picture.id, Picture.name, Picture.url, Picture.download_count)
            .where(Picture.is_deleted == False, Picture.space_id == space_id)  # noqa: E712
            .order_by(Picture.download_count.desc(), Picture.created_at.desc())
            .limit(limit)
        )
        rows = (await db.execute(stmt)).all()
        return [
            MyTopPicture(picture_id=r[0], name=r[1], url=r[2], download_count=r[3]).model_dump()
            for r in rows
        ]

    async def get_my_category(self, db: AsyncSession, user_id: int) -> list[dict[str, Any]]:
        """个人分类分布。"""
        space_id = await self._get_user_space_id(db, user_id)
        if space_id is None:
            return []
        stmt = (
            select(
                Picture.category,
                func.count(Picture.id),
                func.coalesce(func.sum(Picture.pic_size), 0),
            )
            .select_from(Picture)
            .where(Picture.is_deleted == False, Picture.space_id == space_id)  # noqa: E712
            .group_by(Picture.category)
            .order_by(func.count(Picture.id).desc())
        )
        rows = (await db.execute(stmt)).all()
        total = sum(r[1] for r in rows)
        return [
            CategoryStat(
                category=r[0] or "未分类",
                count=r[1],
                total_size=r[2],
                ratio=round(r[1] / total, 4) if total else 0.0,
            ).model_dump()
            for r in rows
        ]

    async def get_my_tags(self, db: AsyncSession, user_id: int, limit: int) -> list[dict[str, Any]]:
        """个人标签分布 TOP N。"""
        space_id = await self._get_user_space_id(db, user_id)
        if space_id is None:
            return []
        tag_expr = func.jsonb_array_elements_text(Picture.tags.cast(JSONB)).label("tag")
        stmt = (
            select(tag_expr, func.count(Picture.id))
            .select_from(Picture)
            .where(Picture.is_deleted == False, Picture.space_id == space_id)  # noqa: E712
            .group_by(tag_expr)
            .order_by(func.count(Picture.id).desc())
            .limit(limit)
        )
        rows = (await db.execute(stmt)).all()
        return [TagStat(tag=r[0], count=r[1]).model_dump() for r in rows]

    # ------------------------------------------------------------------ 辅助

    async def _get_user_space(self, db: AsyncSession, user_id: int) -> Space | None:
        """取当前用户 active 空间（ORM 对象），无则返回 None。"""
        stmt = select(Space).where(Space.user_id == user_id, Space.is_deleted == False)  # noqa: E712
        return (await db.execute(stmt)).scalar_one_or_none()

    async def _get_user_space_id(self, db: AsyncSession, user_id: int) -> int | None:
        """取当前用户 active 空间 id，无则返回 None。"""
        stmt = select(Space.id).where(Space.user_id == user_id, Space.is_deleted == False)  # noqa: E712
        return (await db.execute(stmt)).scalar_one_or_none()
