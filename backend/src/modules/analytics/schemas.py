"""图库分析响应 schema（纯聚合，不映射 ORM 单行，故无需 from_attributes）。"""

from pydantic import BaseModel


class GalleryOverview(BaseModel):
    """公共图库总量统计。"""

    total_pictures: int
    total_size: int
    total_downloads: int


class TrendPoint(BaseModel):
    """上传量趋势数据点（按日/周/月分桶）。"""

    period: str
    count: int


class StorageTrendPoint(BaseModel):
    """存储容量趋势数据点。"""

    period: str
    total_size: int


class CategoryStat(BaseModel):
    """分类分布项。"""

    category: str
    count: int
    total_size: int
    ratio: float  # 数量占比 0.0-1.0


class TagStat(BaseModel):
    """标签云项。"""

    tag: str
    count: int


class TopUploader(BaseModel):
    """上传者排行项。"""

    user_id: int
    name: str | None
    username: str
    count: int


class SpacesOverview(BaseModel):
    """空间大盘（管理员视角）。"""

    total_spaces: int
    total_capacity: int
    total_used: int
    usage_rate: float  # 0.0-1.0
    avg_pictures_per_space: float


class SpaceRankItem(BaseModel):
    """空间排行项。"""

    space_id: int
    name: str
    user_id: int
    username: str
    space_level: int
    total_count: int
    total_size: int


class MySpaceOverview(BaseModel):
    """个人空间摘要（用户视角）。"""

    space_id: int | None
    picture_count: int
    max_count: int
    count_usage: float  # count/max_count
    total_size: int
    max_size: int
    size_usage: float  # size/max_size


class MyTopPicture(BaseModel):
    """个人热门图片项。"""

    picture_id: int
    name: str
    url: str
    download_count: int
