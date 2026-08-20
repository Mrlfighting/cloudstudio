"""以图搜图工具包数据模型（pydantic）。

字段统一用 snake_case（与项目 schemas 约定一致）；若将来暴露 HTTP 端点需
camelCase（如 thumbnailUrl），加 ``alias_generator=to_camel`` 即可，无需改内部逻辑。
"""

from pydantic import BaseModel, Field


class SearchResult(BaseModel):
    """单条相似图片结果。"""

    thumbnail_url: str  # 缩略图地址（对应需求 thumbnailUrl）
    source_url: str  # 来源页面地址（对应 sourceUrl）
    source_name: str  # 来源名称（对应 sourceName）
    title: str | None = None  # 图片标题（对应 title，可选）
    score: float | None = None  # 相关性评分（对应 score，可选）


class SourceSearchResult(BaseModel):
    """单个搜索源的结果组（按源分组返回）。"""

    source_name: str
    results: list[SearchResult] = Field(default_factory=list)
    error: str | None = None  # 该源失败原因（有值则 results 为空）
    skipped: bool = False  # True = 未配置/被禁用，被跳过


class ImageSearchResponse(BaseModel):
    """以图搜图聚合响应（按源分组）。"""

    query_url: str  # 查询的图片 URL
    sources: list[SourceSearchResult] = Field(default_factory=list)
