"""图像画面扩展（扩图）工具包异常体系。"""


class ImageOutpaintingException(Exception):
    """扩图工具包基类异常。"""


class OutpaintingRequestError(ImageOutpaintingException):
    """百炼扩图接口 HTTP 请求失败（非 2xx / 网络错误 / 业务 code 错误）。"""


class OutpaintingTimeoutError(ImageOutpaintingException):
    """百炼扩图接口请求超时。"""


class OutpaintingParseError(ImageOutpaintingException):
    """百炼扩图接口返回数据解析失败（非 JSON / 缺关键字段）。"""
