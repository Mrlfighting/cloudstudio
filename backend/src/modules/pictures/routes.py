"""图片模块 API 路由。"""

from typing import Any

from fastapi import APIRouter, File, Form, Query, UploadFile, status
from fastapi.responses import RedirectResponse
from fastcrud import PaginatedListResponse, paginated_response

from ...infrastructure.auth.http_exceptions import HTTPException
from ...infrastructure.dependencies import AsyncSessionDep, CurrentSuperUserDep, CurrentUserDep
from ..common.utils.error_handler import handle_exception
from .dependencies import PictureServiceDep
from .schemas import PictureListItemRead, PictureRead, PictureStatusUpdate, PictureUpdate

router = APIRouter(tags=["Pictures"])


@router.post(
    "/",
    status_code=status.HTTP_201_CREATED,
    response_model=PictureRead,
    summary="上传图片（登录用户）",
    description="""
           登录用户可上传：multipart 上传图片文件并填写元信息。

           - file：图片文件（JPEG/PNG/WebP/GIF，≤10MB）
           - name：名称
           - introduction：简介（≤200字）
           - category：分类（预置：风景/人物/动物/建筑/美食/科技/插画/其他）
           - tags：标签（JSON 数组字符串，如 ["风景","自然"]）

           系统自动解析宽高、体积、格式、色彩模式并存入数据库。上传后状态为"待审核"，管理员审核通过后所有用户可见。
           """,
    responses={
        201: {"description": "上传成功"},
        401: {"description": "未登录"},
        422: {"description": "参数校验失败"},
    },
    response_description="创建的图片信息",
)
async def upload_picture(
    db: AsyncSessionDep,
    current_user: CurrentUserDep,
    picture_service: PictureServiceDep,
    file: UploadFile = File(...),
    name: str = Form(..., min_length=1, max_length=128),
    introduction: str | None = Form(None, max_length=512),
    category: str = Form(...),
    tags: str = Form("[]"),
) -> dict[str, Any]:
    """上传图片（登录用户，待审核）。"""
    try:
        return await picture_service.upload(
            file=file, name=name, introduction=introduction,
            category=category, tags_str=tags, db=db, current_user=current_user,
        )
    except Exception as e:
        http_exception = handle_exception(e)
        if http_exception:
            raise http_exception
        raise HTTPException(status_code=500, detail="上传图片失败")


@router.get(
    "/",
    response_model=PaginatedListResponse[PictureListItemRead],
    summary="图片列表（已发布）",
    description="""
           登录用户可见：分页展示已审核通过的图片。

           - page / items_per_page：分页
           - category：按分类筛选
           - keyword：按名称/简介/标签搜索
           - sort：time（最新）/ popularity（热度，按下载次数）
           """,
    responses={401: {"description": "未登录"}},
    response_description="分页图片列表",
)
async def list_pictures(
    db: AsyncSessionDep,
    picture_service: PictureServiceDep,
    _: CurrentUserDep,
    page: int = Query(1, ge=1),
    items_per_page: int = Query(10, ge=1, le=100),
    category: str | None = Query(None),
    keyword: str | None = Query(None),
    sort: str = Query("time", pattern="^(time|popularity)$"),
) -> dict[str, Any]:
    """用户端图片列表（已发布）。"""
    try:
        data = await picture_service.list_user(
            db=db, page=page, items_per_page=items_per_page,
            category=category, keyword=keyword, sort=sort,
        )
        return paginated_response(crud_data=data, page=page, items_per_page=items_per_page)
    except Exception as e:
        http_exception = handle_exception(e)
        if http_exception:
            raise http_exception
        raise HTTPException(status_code=500, detail="获取图片列表失败")


@router.get(
    "/manage",
    response_model=PaginatedListResponse[PictureListItemRead],
    summary="图片管理列表（仅管理员）",
    description="""
           仅管理员可用：全状态图片列表（含待审核/已拒绝）。

           额外支持按 status（pending/approved/rejected）过滤。
           """,
    responses={401: {"description": "未登录"}, 403: {"description": "无权限"}},
    response_description="分页图片列表",
)
async def manage_pictures(
    db: AsyncSessionDep,
    picture_service: PictureServiceDep,
    _: CurrentSuperUserDep,
    page: int = Query(1, ge=1),
    items_per_page: int = Query(10, ge=1, le=100),
    category: str | None = Query(None),
    keyword: str | None = Query(None),
    sort: str = Query("time", pattern="^(time|popularity)$"),
    pic_status: str | None = Query(None, alias="status", pattern="^(pending|approved|rejected)$"),
) -> dict[str, Any]:
    """管理端图片列表（全状态）。"""
    try:
        data = await picture_service.list_admin(
            db=db, page=page, items_per_page=items_per_page,
            category=category, keyword=keyword, sort=sort, status=pic_status,
        )
        return paginated_response(crud_data=data, page=page, items_per_page=items_per_page)
    except Exception as e:
        http_exception = handle_exception(e)
        if http_exception:
            raise http_exception
        raise HTTPException(status_code=500, detail="获取图片管理列表失败")


@router.get(
    "/my",
    response_model=PaginatedListResponse[PictureListItemRead],
    summary="我的上传（登录用户）",
    description="""
           登录用户查看自己上传的全部图片（含待审核/已通过/已拒绝），展示状态与拒绝理由。
           """,
    responses={401: {"description": "未登录"}},
    response_description="分页图片列表",
)
async def list_my_pictures(
    db: AsyncSessionDep,
    picture_service: PictureServiceDep,
    current_user: CurrentUserDep,
    page: int = Query(1, ge=1),
    items_per_page: int = Query(10, ge=1, le=100),
    category: str | None = Query(None),
    keyword: str | None = Query(None),
    sort: str = Query("time", pattern="^(time|popularity)$"),
    pic_status: str | None = Query(None, alias="status", pattern="^(pending|approved|rejected)$"),
) -> dict[str, Any]:
    """我的上传列表（全状态）。"""
    try:
        data = await picture_service.list_my(
            db=db, user_id=current_user["id"], page=page, items_per_page=items_per_page,
            category=category, keyword=keyword, sort=sort, status=pic_status,
        )
        return paginated_response(crud_data=data, page=page, items_per_page=items_per_page)
    except Exception as e:
        http_exception = handle_exception(e)
        if http_exception:
            raise http_exception
        raise HTTPException(status_code=500, detail="获取我的上传列表失败")


@router.get(
    "/{picture_id}",
    response_model=PictureRead,
    summary="图片详情",
    description="""
           登录用户可见：查看已发布图片的完整信息（含宽高、格式、大小、下载次数等）。

           管理员如需查看任意状态图片，可先通过管理列表定位（详情接口对用户端仅返回已发布）。
           """,
    responses={401: {"description": "未登录"}, 404: {"description": "图片不存在"}},
    response_description="图片完整信息",
)
async def get_picture(
    picture_id: int,
    db: AsyncSessionDep,
    picture_service: PictureServiceDep,
    _: CurrentUserDep,
) -> dict[str, Any]:
    """图片详情（仅已发布）。"""
    try:
        return await picture_service.get(db, picture_id, require_approved=True)
    except Exception as e:
        http_exception = handle_exception(e)
        if http_exception:
            raise http_exception
        raise HTTPException(status_code=500, detail="获取图片详情失败")


@router.get(
    "/{picture_id}/download",
    summary="下载图片",
    description="""
           登录用户可用：下载已发布图片。每次下载记录下载次数并更新热度，随后 302 重定向到图片地址。
           """,
    responses={302: {"description": "重定向到图片地址"}, 404: {"description": "图片不存在或未发布"}},
    response_description="重定向到图片文件地址",
)
async def download_picture(
    picture_id: int,
    db: AsyncSessionDep,
    picture_service: PictureServiceDep,
    _: CurrentUserDep,
) -> RedirectResponse:
    """下载图片：计数 +1 后重定向。"""
    try:
        url = await picture_service.download(db, picture_id)
        return RedirectResponse(url=url, status_code=status.HTTP_302_FOUND)
    except Exception as e:
        http_exception = handle_exception(e)
        if http_exception:
            raise http_exception
        raise HTTPException(status_code=500, detail="下载图片失败")


@router.patch(
    "/{picture_id}",
    summary="编辑图片元信息（仅管理员）",
    description="""
           仅管理员可用：修改图片的名称、简介、标签、分类。不支持覆盖图片文件本身。
           """,
    responses={
        200: {"description": "修改成功"},
        403: {"description": "无权限"},
        404: {"description": "图片不存在"},
    },
    response_description="操作结果",
)
async def update_picture(
    picture_id: int,
    values: PictureUpdate,
    db: AsyncSessionDep,
    picture_service: PictureServiceDep,
    _: CurrentSuperUserDep,
) -> dict[str, str]:
    """编辑图片元信息（仅管理员）。"""
    try:
        await picture_service.update(db, picture_id, values)
        return {"message": "图片信息修改成功"}
    except Exception as e:
        http_exception = handle_exception(e)
        if http_exception:
            raise http_exception
        raise HTTPException(status_code=500, detail="修改图片失败")


@router.patch(
    "/{picture_id}/status",
    summary="审核图片（仅管理员）",
    description="""
           仅管理员可用：审核图片，status 为 approved（通过）或 rejected（拒绝）。
           通过后用户列表可见。
           """,
    responses={
        200: {"description": "审核完成"},
        403: {"description": "无权限"},
        404: {"description": "图片不存在"},
    },
    response_description="操作结果",
)
async def audit_picture(
    picture_id: int,
    values: PictureStatusUpdate,
    db: AsyncSessionDep,
    picture_service: PictureServiceDep,
    _: CurrentSuperUserDep,
) -> dict[str, str]:
    """审核图片（仅管理员）。"""
    try:
        await picture_service.audit(db, picture_id, values)
        action = "通过" if values.status == "approved" else "拒绝"
        return {"message": f"图片审核{action}"}
    except Exception as e:
        http_exception = handle_exception(e)
        if http_exception:
            raise http_exception
        raise HTTPException(status_code=500, detail="审核图片失败")


@router.delete(
    "/{picture_id}",
    summary="删除图片（仅管理员，软删除）",
    description="""
           仅管理员可用：软删除图片（is_deleted=True）。可恢复、保留审计，列表不再展示。
           """,
    responses={
        200: {"description": "删除成功"},
        403: {"description": "无权限"},
        404: {"description": "图片不存在"},
    },
    response_description="操作结果",
)
async def delete_picture(
    picture_id: int,
    db: AsyncSessionDep,
    picture_service: PictureServiceDep,
    _: CurrentSuperUserDep,
) -> dict[str, str]:
    """软删除图片（仅管理员）。"""
    try:
        await picture_service.delete(db, picture_id)
        return {"message": "图片已删除"}
    except Exception as e:
        http_exception = handle_exception(e)
        if http_exception:
            raise http_exception
        raise HTTPException(status_code=500, detail="删除图片失败")
