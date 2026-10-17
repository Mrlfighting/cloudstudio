"""拼豆工具独立 API，仅提供受保护的私有图片读取。"""

from typing import Annotated, Any

from fastapi import APIRouter, Depends, Response

from ...infrastructure.auth.dependencies import get_current_user
from ...infrastructure.config.settings import get_settings
from .adapter import get_private_picture
from .cloud_routes import router as cloud_router
from .service import BeadSourceService

router = APIRouter(tags=["拼豆工坊"])


def get_source_service() -> BeadSourceService:
    """创建无状态取图服务。"""
    return BeadSourceService()


@router.get(
    "/sources/private/{picture_id}",
    summary="读取本人的私有图片供拼豆转换",
    dependencies=[Depends(get_current_user)],
    response_class=Response,
)
async def read_private_source(
    picture: Annotated[dict[str, Any], Depends(get_private_picture)],
    service: Annotated[BeadSourceService, Depends(get_source_service)],
) -> Response:
    """归属判断先于下载；失败不暴露 COS URL 或凭据。"""
    data, mime = await service.read(str(picture["url"]), get_settings().COS_BASE_URL)
    return Response(data, media_type=mime, headers={
        "Cache-Control": "private, no-store", "X-Content-Type-Options": "nosniff",
    })


# 固定私有来源接口优先注册，云端作品保持独立子路由。
router.include_router(cloud_router)
