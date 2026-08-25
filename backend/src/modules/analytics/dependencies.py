"""图库分析模块依赖注入。"""

from typing import Annotated

from fastapi import Depends

from .service import AnalyticsService


def get_analytics_service() -> AnalyticsService:
    return AnalyticsService()


AnalyticsServiceDep = Annotated[AnalyticsService, Depends(get_analytics_service)]
