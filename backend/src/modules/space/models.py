"""空间模型：用户私有图库/相册。"""

from sqlalchemy import BigInteger, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from ...infrastructure.database.models import SoftDeleteMixin, TimestampMixin
from ...infrastructure.database.session import Base


class Space(Base, TimestampMixin, SoftDeleteMixin):
    """空间：每个用户一个私有空间，与公共图库隔离。

    - space_level：0普通版 / 1专业版 / 2旗舰版
    - max_size/max_count：当前级别的配额上限
    - total_size/total_count：当前已用量（软配额，允许超过上限，超限软提示）
    - status：active/banned（封禁后不可访问、不可上传）
    """

    __tablename__ = "spaces"

    id: Mapped[int] = mapped_column(
        "id",
        autoincrement=True,
        nullable=False,
        unique=True,
        primary_key=True,
        init=False,
    )

    name: Mapped[str] = mapped_column(String(128), index=True)
    # 所属用户（每个用户仅一个 active 空间，由 service 层本地锁 + 事务保证）
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("user.id"), index=True)

    space_level: Mapped[int] = mapped_column(Integer, default=0, index=True)
    max_size: Mapped[int] = mapped_column(BigInteger, default=0)
    max_count: Mapped[int] = mapped_column(BigInteger, default=0)
    total_size: Mapped[int] = mapped_column(BigInteger, default=0)
    total_count: Mapped[int] = mapped_column(BigInteger, default=0)
    status: Mapped[str] = mapped_column(String(20), default="active", index=True)

    def __repr__(self) -> str:
        return f"{self.name} (level={self.space_level})"
