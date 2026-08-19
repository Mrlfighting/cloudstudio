"""二级缓存监控路由。"""

from typing import Any

from fastapi import APIRouter

from ....infrastructure.cache.two_level import get_cache_manager
from ....infrastructure.dependencies import CurrentSuperUserDep

router = APIRouter(tags=["Cache"])


@router.get(
    "/stats",
    summary="缓存命中率统计（仅管理员）",
    description="返回二级缓存的本地(L1)/Redis(L2) 各自命中、未命中与命中率。",
    response_description="缓存命中率统计",
)
async def cache_stats(_: CurrentSuperUserDep) -> dict[str, Any]:
    """缓存命中率统计（仅管理员）。"""
    manager = get_cache_manager()
    if manager is None:
        return {"enabled": False, "message": "二级缓存未启用"}
    return {"enabled": manager.enabled, **manager.stats()}
