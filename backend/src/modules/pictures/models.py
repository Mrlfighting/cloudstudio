
from sqlalchemy import BigInteger, Float, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import JSON
from sqlalchemy.orm import Mapped, mapped_column

from ...infrastructure.database.models import SoftDeleteMixin, TimestampMixin
from ...infrastructure.database.session import Base


class Picture(Base, TimestampMixin, SoftDeleteMixin):
    """图片模型：公共图库。

    管理员上传图片到腾讯云 COS，本表保存 URL 与元信息（含自动解析的基础信息）。
    审核流程：上传为 pending，管理员审核为 approved 后用户可见。
    """

    __tablename__ = "pictures"

    id: Mapped[int] = mapped_column(
        "id",
        autoincrement=True,
        nullable=False,
        unique=True,
        primary_key=True,
        init=False,
    )

    url: Mapped[str] = mapped_column(String(512))
    name: Mapped[str] = mapped_column(String(128), index=True)
    introduction: Mapped[str | None] = mapped_column(String(512), index=True)
    category: Mapped[str | None] = mapped_column(String(64), index=True)

    # 自动解析的图片基础信息
    pic_size: Mapped[int | None] = mapped_column(BigInteger)
    pic_width: Mapped[int | None] = mapped_column(Integer)
    pic_height: Mapped[int | None] = mapped_column(Integer)
    pic_scale: Mapped[float | None] = mapped_column(Float)
    pic_format: Mapped[str | None] = mapped_column(String(32))
    color_mode: Mapped[str | None] = mapped_column(String(32))

    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("user.id"), index=True)

    # 审核状态（pending/approved/rejected）与下载热度
    # tags 为 JSON 列，PostgreSQL 的 json 类型不支持 btree 索引（搜索用 cast(tags as text) ILIKE）
    tags: Mapped[list[str]] = mapped_column(JSON, default_factory=list)
    status: Mapped[str] = mapped_column(String(20), default="pending", index=True)
    # 审核理由（拒绝时必填，通过时清空）
    review_reason: Mapped[str | None] = mapped_column(String(512), default=None)
    download_count: Mapped[int] = mapped_column(Integer, default=0)

    def __repr__(self) -> str:
        return f"{self.name} ({self.category})"
