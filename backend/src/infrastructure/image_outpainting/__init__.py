"""图像画面扩展（扩图）工具包（基础设施层）。

封装阿里云百炼 ``image-out-painting`` 异步扩图 API，对外提供门面、数据模型
与异常，与主业务代码解耦。
"""

from .exceptions import (
    ImageOutpaintingException,
    OutpaintingParseError,
    OutpaintingRequestError,
    OutpaintingTimeoutError,
)
from .facade import (
    ImageOutpaintingFacade,
    create_outpainting_task,
    get_image_outpainting_facade,
    query_outpainting_task,
    set_image_outpainting_facade,
)
from .models import (
    CreateTaskResponse,
    OutpaintingParameters,
    QueryTaskResponse,
    TaskStatus,
)

__all__ = [
    "ImageOutpaintingFacade",
    "ImageOutpaintingException",
    "OutpaintingRequestError",
    "OutpaintingTimeoutError",
    "OutpaintingParseError",
    "OutpaintingParameters",
    "CreateTaskResponse",
    "QueryTaskResponse",
    "TaskStatus",
    "get_image_outpainting_facade",
    "set_image_outpainting_facade",
    "create_outpainting_task",
    "query_outpainting_task",
]
