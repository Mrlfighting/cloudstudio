"""图库分析 API 路由。

权限：
- 公共图库 / 空间大盘：仅管理员（CurrentSuperUserDep）
- 我的空间：仅登录用户（CurrentUserDep），只返回自己的空间数据
"""

from typing import Any

from fastapi import APIRouter, Query

from ...infrastructure.dependencies import AsyncSessionDep, CurrentSuperUserDep, CurrentUserDep
from .dependencies import AnalyticsServiceDep
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

router = APIRouter(tags=["Analytics"])

_GRANULARITY = Query("day", pattern="^(day|week|month)$")


# --------------------------------------------------------------------------- 公共图库分析（管理员）


@router.get(
    "/gallery/overview",
    response_model=GalleryOverview,
    summary="公共图库总量统计（仅管理员）",
)
async def gallery_overview(
    db: AsyncSessionDep,
    analytics_service: AnalyticsServiceDep,
    _: CurrentSuperUserDep,
) -> dict[str, Any]:
    """图片总数 / 总存储容量 / 总下载量。"""
    return await analytics_service.get_gallery_overview(db)


@router.get(
    "/gallery/trend",
    response_model=list[TrendPoint],
    summary="公共图库上传量增长趋势（仅管理员）",
)
async def gallery_trend(
    db: AsyncSessionDep,
    analytics_service: AnalyticsServiceDep,
    _: CurrentSuperUserDep,
    granularity: str = _GRANULARITY,
) -> list[dict[str, Any]]:
    """按日/周/月统计上传量变化。"""
    return await analytics_service.get_gallery_trend(db, granularity)


@router.get(
    "/gallery/category",
    response_model=list[CategoryStat],
    summary="公共图库分类分布（仅管理员）",
)
async def gallery_category(
    db: AsyncSessionDep,
    analytics_service: AnalyticsServiceDep,
    _: CurrentSuperUserDep,
) -> list[dict[str, Any]]:
    """各分类图片数量及占比。"""
    return await analytics_service.get_gallery_category(db)


@router.get(
    "/gallery/tags",
    response_model=list[TagStat],
    summary="公共图库热门标签 TOP N（仅管理员）",
)
async def gallery_tags(
    db: AsyncSessionDep,
    analytics_service: AnalyticsServiceDep,
    _: CurrentSuperUserDep,
    limit: int = Query(20, ge=1, le=100),
) -> list[dict[str, Any]]:
    """热门标签及使用次数。"""
    return await analytics_service.get_gallery_tags(db, limit)


@router.get(
    "/gallery/top-uploaders",
    response_model=list[TopUploader],
    summary="公共图库上传者排行 TOP N（仅管理员）",
)
async def gallery_top_uploaders(
    db: AsyncSessionDep,
    analytics_service: AnalyticsServiceDep,
    _: CurrentSuperUserDep,
    limit: int = Query(10, ge=1, le=100),
) -> list[dict[str, Any]]:
    """上传图片最多的用户。"""
    return await analytics_service.get_gallery_top_uploaders(db, limit)


@router.get(
    "/gallery/storage-trend",
    response_model=list[StorageTrendPoint],
    summary="公共图库存储容量趋势（仅管理员）",
)
async def gallery_storage_trend(
    db: AsyncSessionDep,
    analytics_service: AnalyticsServiceDep,
    _: CurrentSuperUserDep,
    granularity: str = _GRANULARITY,
) -> list[dict[str, Any]]:
    """总存储容量随时间变化。"""
    return await analytics_service.get_gallery_storage_trend(db, granularity)


# --------------------------------------------------------------------------- 空间大盘（管理员）


@router.get(
    "/spaces/overview",
    response_model=SpacesOverview,
    summary="空间大盘（仅管理员）",
)
async def spaces_overview(
    db: AsyncSessionDep,
    analytics_service: AnalyticsServiceDep,
    _: CurrentSuperUserDep,
) -> dict[str, Any]:
    """空间总数 / 总容量使用率 / 平均图片数。"""
    return await analytics_service.get_spaces_overview(db)


@router.get(
    "/spaces/ranking",
    response_model=list[SpaceRankItem],
    summary="空间排行 TOP N（仅管理员）",
)
async def spaces_ranking(
    db: AsyncSessionDep,
    analytics_service: AnalyticsServiceDep,
    _: CurrentSuperUserDep,
    limit: int = Query(10, ge=1, le=100),
    sort: str = Query("count", pattern="^(count|size)$"),
) -> list[dict[str, Any]]:
    """按图片数量或容量使用量排序的空间。"""
    return await analytics_service.get_spaces_ranking(db, limit, sort)


# --------------------------------------------------------------------------- 我的空间（登录用户）


@router.get(
    "/my/overview",
    response_model=MySpaceOverview,
    summary="个人空间摘要（登录用户）",
)
async def my_overview(
    db: AsyncSessionDep,
    analytics_service: AnalyticsServiceDep,
    current_user: CurrentUserDep,
) -> dict[str, Any]:
    """我的空间：图片数量/限额、容量/容量百分比。"""
    return await analytics_service.get_my_overview(db, current_user["id"])


@router.get(
    "/my/trend",
    response_model=list[TrendPoint],
    summary="个人上传趋势（登录用户）",
)
async def my_trend(
    db: AsyncSessionDep,
    analytics_service: AnalyticsServiceDep,
    current_user: CurrentUserDep,
    granularity: str = _GRANULARITY,
) -> list[dict[str, Any]]:
    """我空间内上传量随时间变化。"""
    return await analytics_service.get_my_trend(db, current_user["id"], granularity)


@router.get(
    "/my/top-pictures",
    response_model=list[MyTopPicture],
    summary="个人热门图片 TOP N（登录用户）",
)
async def my_top_pictures(
    db: AsyncSessionDep,
    analytics_service: AnalyticsServiceDep,
    current_user: CurrentUserDep,
    limit: int = Query(10, ge=1, le=100),
) -> list[dict[str, Any]]:
    """我空间内按下载量排序的热门图片。"""
    return await analytics_service.get_my_top_pictures(db, current_user["id"], limit)


@router.get(
    "/my/category",
    response_model=list[CategoryStat],
    summary="个人分类分布（登录用户）",
)
async def my_category(
    db: AsyncSessionDep,
    analytics_service: AnalyticsServiceDep,
    current_user: CurrentUserDep,
) -> list[dict[str, Any]]:
    """我空间内图片分类分布。"""
    return await analytics_service.get_my_category(db, current_user["id"])


@router.get(
    "/my/tags",
    response_model=list[TagStat],
    summary="个人标签分布 TOP N（登录用户）",
)
async def my_tags(
    db: AsyncSessionDep,
    analytics_service: AnalyticsServiceDep,
    current_user: CurrentUserDep,
    limit: int = Query(20, ge=1, le=100),
) -> list[dict[str, Any]]:
    """我空间内图片标签分布。"""
    return await analytics_service.get_my_tags(db, current_user["id"], limit)
