"""空间模块 API 路由。"""

from typing import Any

from fastapi import APIRouter, File, Form, Query, UploadFile, status
from fastcrud import PaginatedListResponse, paginated_response

from ...infrastructure.auth.http_exceptions import HTTPException
from ...infrastructure.dependencies import AsyncSessionDep, CurrentSuperUserDep, CurrentUserDep
from ...infrastructure.image_outpainting import CreateTaskResponse, OutpaintingParameters, QueryTaskResponse
from ...infrastructure.image_search import ImageSearchResponse
from ..common.utils.error_handler import handle_exception
from ..pictures.schemas import PictureListItemRead, PictureRead, PictureUpdate
from .dependencies import SpaceServiceDep
from .schemas import ColorSearchItem, SpaceCreate, SpaceInfoRead, SpaceLevelUpdate, SpaceListRead, SpaceRead, SpaceUpdate

router = APIRouter(tags=["Spaces"])


# --------------------------------------------------------------------------- 用户：空间


@router.post(
    "/",
    status_code=status.HTTP_201_CREATED,
    response_model=SpaceRead,
    summary="创建私有空间（登录用户）",
    description="每个用户仅能创建一个私有空间。若已存在则返回错误。",
)
async def create_space(
    payload: SpaceCreate,
    db: AsyncSessionDep,
    current_user: CurrentUserDep,
    space_service: SpaceServiceDep,
) -> dict[str, Any]:
    """创建私有空间。"""
    try:
        return await space_service.create(db, payload.name, current_user)
    except Exception as e:
        http_exception = handle_exception(e)
        if http_exception:
            raise http_exception
        raise HTTPException(status_code=500, detail="创建空间失败")


@router.get(
    "/my",
    response_model=SpaceInfoRead,
    summary="我的空间信息（登录用户）",
    description="返回自己空间的基本信息：名称、当前/总容量、当前/总数、级别、剩余量。",
)
async def get_my_space(
    db: AsyncSessionDep,
    current_user: CurrentUserDep,
    space_service: SpaceServiceDep,
) -> dict[str, Any]:
    """我的空间信息。"""
    try:
        return await space_service.get_my(db, current_user)
    except Exception as e:
        http_exception = handle_exception(e)
        if http_exception:
            raise http_exception
        raise HTTPException(status_code=500, detail="获取空间信息失败")


@router.patch(
    "/my/level",
    response_model=SpaceInfoRead,
    summary="升级/降级空间级别（登录用户）",
    description="用户可自助升级；降级时若当前用量超过目标级别上限则拒绝。",
)
async def change_space_level(
    payload: SpaceLevelUpdate,
    db: AsyncSessionDep,
    current_user: CurrentUserDep,
    space_service: SpaceServiceDep,
) -> dict[str, Any]:
    """升级/降级空间级别。"""
    try:
        return await space_service.change_level(db, current_user, payload.space_level)
    except Exception as e:
        http_exception = handle_exception(e)
        if http_exception:
            raise http_exception
        raise HTTPException(status_code=500, detail="变更空间级别失败")


# --------------------------------------------------------------------------- 用户：空间图片


@router.post(
    "/my/pictures",
    status_code=status.HTTP_201_CREATED,
    response_model=PictureRead,
    summary="上传图片到我的空间（登录用户）",
    description="空间内上传图片（不审核，直接可见）。name/introduction/category/tags 与公共图库一致。",
)
async def upload_space_picture(
    db: AsyncSessionDep,
    current_user: CurrentUserDep,
    space_service: SpaceServiceDep,
    file: UploadFile = File(...),
    name: str = Form(..., min_length=1, max_length=128),
    introduction: str | None = Form(None, max_length=512),
    category: str = Form(...),
    tags: str = Form("[]"),
) -> dict[str, Any]:
    """上传图片到空间。"""
    try:
        return await space_service.upload_picture(
            db=db, current_user=current_user, file=file, name=name,
            introduction=introduction, category=category, tags_str=tags,
        )
    except Exception as e:
        http_exception = handle_exception(e)
        if http_exception:
            raise http_exception
        raise HTTPException(status_code=500, detail="上传空间图片失败")


@router.get(
    "/my/pictures",
    response_model=PaginatedListResponse[PictureListItemRead],
    summary="我的空间图片列表（登录用户）",
    description="分页展示自己空间内的图片（category/keyword/sort 筛选）。",
)
async def list_space_pictures(
    db: AsyncSessionDep,
    current_user: CurrentUserDep,
    space_service: SpaceServiceDep,
    page: int = Query(1, ge=1),
    items_per_page: int = Query(10, ge=1, le=100),
    category: str | None = Query(None),
    keyword: str | None = Query(None),
    sort: str = Query("time", pattern="^(time|popularity)$"),
) -> dict[str, Any]:
    """我的空间图片列表。"""
    try:
        data = await space_service.list_pictures(
            db, current_user, page=page, items_per_page=items_per_page,
            category=category, keyword=keyword, sort=sort,
        )
        return paginated_response(crud_data=data, page=page, items_per_page=items_per_page)
    except Exception as e:
        http_exception = handle_exception(e)
        if http_exception:
            raise http_exception
        raise HTTPException(status_code=500, detail="获取空间图片列表失败")


@router.get(
    "/my/pictures/search-by-color",
    response_model=list[ColorSearchItem],
    summary="按颜色搜索（登录用户，空间内）",
    description="输入一个颜色（如 FF0000），返回自己空间内主色调最相近的图片，按颜色距离升序。",
)
async def search_pictures_by_color(
    db: AsyncSessionDep,
    current_user: CurrentUserDep,
    space_service: SpaceServiceDep,
    color: str = Query(..., min_length=3, max_length=9),
    limit: int = Query(20, ge=1, le=100),
) -> list[ColorSearchItem]:
    """按颜色搜索（空间内图片）。"""
    try:
        return await space_service.search_by_color(db, current_user, color, limit)
    except Exception as e:
        http_exception = handle_exception(e)
        if http_exception:
            raise http_exception
        raise HTTPException(status_code=500, detail="按颜色搜索失败")


@router.get(
    "/my/pictures/{picture_id}",
    response_model=PictureRead,
    summary="我的空间图片详情（登录用户）",
)
async def get_space_picture(
    picture_id: int,
    db: AsyncSessionDep,
    current_user: CurrentUserDep,
    space_service: SpaceServiceDep,
) -> dict[str, Any]:
    """我的空间图片详情。"""
    try:
        return await space_service.get_picture(db, current_user, picture_id)
    except Exception as e:
        http_exception = handle_exception(e)
        if http_exception:
            raise http_exception
        raise HTTPException(status_code=500, detail="获取空间图片详情失败")


@router.get(
    "/my/pictures/{picture_id}/similar",
    response_model=ImageSearchResponse,
    summary="以图搜图（登录用户，空间内）",
    description="对空间内图片搜索全网相似图片，返回多源聚合结果（按来源分组）。",
)
async def search_similar_space_picture(
    picture_id: int,
    db: AsyncSessionDep,
    current_user: CurrentUserDep,
    space_service: SpaceServiceDep,
) -> ImageSearchResponse:
    """以图搜图（空间内图片）。"""
    try:
        return await space_service.search_similar(db, current_user, picture_id)
    except Exception as e:
        http_exception = handle_exception(e)
        if http_exception:
            raise http_exception
        raise HTTPException(status_code=500, detail="以图搜图失败")


# --------------------------------------------------------------------------- 用户：空间图片 AI 扩图


@router.post(
    "/my/pictures/{picture_id}/outpaint",
    response_model=CreateTaskResponse,
    summary="AI 扩图：创建扩图任务（登录用户）",
    description="对空间内图片创建百炼图像画面扩展任务，返回 task_id（供前端轮询查询结果）。",
)
async def create_outpainting_task(
    picture_id: int,
    params: OutpaintingParameters,
    db: AsyncSessionDep,
    current_user: CurrentUserDep,
    space_service: SpaceServiceDep,
) -> CreateTaskResponse:
    """创建扩图任务。"""
    try:
        return await space_service.create_outpainting_task(db, current_user, picture_id, params)
    except Exception as e:
        http_exception = handle_exception(e)
        if http_exception:
            raise http_exception
        raise HTTPException(status_code=500, detail="创建扩图任务失败")


@router.get(
    "/my/outpaint/{task_id}",
    response_model=QueryTaskResponse,
    summary="AI 扩图：查询扩图任务结果（登录用户，前端轮询）",
    description="轮询查询扩图任务状态；task_status 为 SUCCEEDED 时返回 output_image_url。",
)
async def query_outpainting_task(
    task_id: str,
    current_user: CurrentUserDep,
    space_service: SpaceServiceDep,
) -> QueryTaskResponse:
    """查询扩图任务结果。"""
    try:
        return await space_service.query_outpainting_task(task_id)
    except Exception as e:
        http_exception = handle_exception(e)
        if http_exception:
            raise http_exception
        raise HTTPException(status_code=500, detail="查询扩图任务失败")


@router.patch(
    "/my/pictures/{picture_id}",
    summary="编辑空间图片信息（登录用户）",
)
async def update_space_picture(
    picture_id: int,
    values: PictureUpdate,
    db: AsyncSessionDep,
    current_user: CurrentUserDep,
    space_service: SpaceServiceDep,
) -> dict[str, str]:
    """编辑空间图片元信息。"""
    try:
        await space_service.update_picture(db, current_user, picture_id, values)
        return {"message": "图片信息修改成功"}
    except Exception as e:
        http_exception = handle_exception(e)
        if http_exception:
            raise http_exception
        raise HTTPException(status_code=500, detail="修改空间图片失败")


@router.delete(
    "/my/pictures/{picture_id}",
    summary="删除空间图片（登录用户）",
)
async def delete_space_picture(
    picture_id: int,
    db: AsyncSessionDep,
    current_user: CurrentUserDep,
    space_service: SpaceServiceDep,
) -> dict[str, str]:
    """删除空间图片（回退配额）。"""
    try:
        await space_service.delete_picture(db, current_user, picture_id)
        return {"message": "图片已删除"}
    except Exception as e:
        http_exception = handle_exception(e)
        if http_exception:
            raise http_exception
        raise HTTPException(status_code=500, detail="删除空间图片失败")


# --------------------------------------------------------------------------- 管理员：空间


@router.get(
    "/",
    response_model=PaginatedListResponse[SpaceListRead],
    summary="空间列表（仅管理员）",
    description="分页展示所有空间，按名称/所属用户/级别筛选，创建时间倒序。",
)
async def list_spaces(
    db: AsyncSessionDep,
    space_service: SpaceServiceDep,
    _: CurrentSuperUserDep,
    page: int = Query(1, ge=1),
    items_per_page: int = Query(10, ge=1, le=100),
    name: str | None = Query(None),
    user_id: int | None = Query(None),
    space_level: int | None = Query(None, ge=0, le=2),
) -> dict[str, Any]:
    """空间列表（管理员）。"""
    try:
        data = await space_service.list_admin(
            db, page=page, items_per_page=items_per_page,
            name=name, user_id=user_id, space_level=space_level,
        )
        return paginated_response(crud_data=data, page=page, items_per_page=items_per_page)
    except Exception as e:
        http_exception = handle_exception(e)
        if http_exception:
            raise http_exception
        raise HTTPException(status_code=500, detail="获取空间列表失败")


@router.get(
    "/{space_id}",
    response_model=SpaceRead,
    summary="空间详情（仅管理员）",
)
async def get_space(
    space_id: int,
    db: AsyncSessionDep,
    space_service: SpaceServiceDep,
    _: CurrentSuperUserDep,
) -> dict[str, Any]:
    """空间详情（管理员）。"""
    try:
        return await space_service.get_admin(db, space_id)
    except Exception as e:
        http_exception = handle_exception(e)
        if http_exception:
            raise http_exception
        raise HTTPException(status_code=500, detail="获取空间详情失败")


@router.patch(
    "/{space_id}",
    response_model=SpaceRead,
    summary="编辑空间（仅管理员）",
    description="修改空间名称、空间级别。",
)
async def update_space(
    space_id: int,
    values: SpaceUpdate,
    db: AsyncSessionDep,
    space_service: SpaceServiceDep,
    _: CurrentSuperUserDep,
) -> dict[str, Any]:
    """编辑空间（管理员）。"""
    try:
        return await space_service.update_admin(
            db, space_id, values.name,
            int(values.space_level) if values.space_level is not None else None,
        )
    except Exception as e:
        http_exception = handle_exception(e)
        if http_exception:
            raise http_exception
        raise HTTPException(status_code=500, detail="修改空间失败")


@router.delete(
    "/{space_id}",
    summary="删除空间（仅管理员）",
    description="软删除空间，并级联软删除其下所有图片。",
)
async def delete_space(
    space_id: int,
    db: AsyncSessionDep,
    space_service: SpaceServiceDep,
    _: CurrentSuperUserDep,
) -> dict[str, str]:
    """删除空间（管理员）。"""
    try:
        await space_service.delete_admin(db, space_id)
        return {"message": "空间已删除"}
    except Exception as e:
        http_exception = handle_exception(e)
        if http_exception:
            raise http_exception
        raise HTTPException(status_code=500, detail="删除空间失败")


@router.post(
    "/{space_id}/ban",
    response_model=SpaceRead,
    summary="封禁空间（仅管理员）",
    description="封禁后空间内图片不可访问，用户无法上传新图片。",
)
async def ban_space(
    space_id: int,
    db: AsyncSessionDep,
    space_service: SpaceServiceDep,
    _: CurrentSuperUserDep,
) -> dict[str, Any]:
    """封禁空间。"""
    try:
        return await space_service.set_ban(db, space_id, banned=True)
    except Exception as e:
        http_exception = handle_exception(e)
        if http_exception:
            raise http_exception
        raise HTTPException(status_code=500, detail="封禁空间失败")


@router.post(
    "/{space_id}/unban",
    response_model=SpaceRead,
    summary="解封空间（仅管理员）",
)
async def unban_space(
    space_id: int,
    db: AsyncSessionDep,
    space_service: SpaceServiceDep,
    _: CurrentSuperUserDep,
) -> dict[str, Any]:
    """解封空间。"""
    try:
        return await space_service.set_ban(db, space_id, banned=False)
    except Exception as e:
        http_exception = handle_exception(e)
        if http_exception:
            raise http_exception
        raise HTTPException(status_code=500, detail="解封空间失败")
