"""空间模型：用户私有图库/相册，以及团队空间成员关联表。"""

from sqlalchemy import BigInteger, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from ...infrastructure.database.models import SoftDeleteMixin, TimestampMixin
from ...infrastructure.database.session import Base


class Space(Base, TimestampMixin, SoftDeleteMixin):
    """空间：私有空间或团队空间，均与公共图库隔离。

    - space_type：0私有空间 / 1团队空间
    - space_level：0普通版 / 1专业版 / 2旗舰版
    - max_size/max_count：当前级别的配额上限
    - total_size/total_count：当前已用量（软配额，允许超过上限，超限软提示）
    - status：active/banned（封禁后不可访问、不可上传）
    - user_id：私有空间=所属用户；团队空间=创建者（Owner/管理员）
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
    # 所属用户（私有空间=owner；团队空间=创建者，由 service 层本地锁 + 事务保证每用户各一个）
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("user.id"), index=True)

    space_type: Mapped[int] = mapped_column(Integer, default=0, index=True)  # 0私有 / 1团队
    space_level: Mapped[int] = mapped_column(Integer, default=0, index=True)
    max_size: Mapped[int] = mapped_column(BigInteger, default=0)
    max_count: Mapped[int] = mapped_column(BigInteger, default=0)
    total_size: Mapped[int] = mapped_column(BigInteger, default=0)
    total_count: Mapped[int] = mapped_column(BigInteger, default=0)
    status: Mapped[str] = mapped_column(String(20), default="active", index=True)

    def __repr__(self) -> str:
        return f"{self.name} (type={self.space_type}, level={self.space_level})"


class SpaceUser(Base, TimestampMixin):
    """空间成员关联表：团队空间的成员与角色。

    - 一个成员在一个空间内只有一个角色（(space_id, user_id) 唯一）
    - 成员移除=硬删除（不继承 SoftDeleteMixin），保证唯一约束在重新加入时仍成立
    - space_role：admin / editor / viewer
    """

    __tablename__ = "space_user"
    __table_args__ = (UniqueConstraint("space_id", "user_id", name="uk_space_user_space_user"),)

    id: Mapped[int] = mapped_column(
        "id",
        autoincrement=True,
        nullable=False,
        unique=True,
        primary_key=True,
        init=False,
    )

    space_id: Mapped[int] = mapped_column(Integer, ForeignKey("spaces.id"), index=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("user.id"), index=True)
    space_role: Mapped[str] = mapped_column(String(20), default="viewer")
