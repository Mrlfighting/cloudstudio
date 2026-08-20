"""以图搜图工具包异常体系。"""


class ImageSearchException(Exception):
    """以图搜图工具包基类异常。"""


class EngineRequestError(ImageSearchException):
    """搜索源 HTTP 请求失败（非 2xx / 网络错误）。"""


class EngineTimeoutError(ImageSearchException):
    """搜索源请求超时。"""


class EngineParseError(ImageSearchException):
    """搜索源返回数据解析失败（非 JSON / 缺关键字段）。"""
