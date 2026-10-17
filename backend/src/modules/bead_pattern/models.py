"""拼豆作品独立持久化模型，不关联图库或空间记录。"""

from uuid import UUID

from sqlalchemy import BigInteger, ForeignKey, Index, Integer, LargeBinary, String, UniqueConstraint, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from ...infrastructure.database.models import SoftDeleteMixin, TimestampMixin
from ...infrastructure.database.session import Base


class BeadPattern(Base, TimestampMixin, SoftDeleteMixin):
    """作品和工作源事务保存；大字段延迟加载，列表不读取图片。"""

    __tablename__ = "bead_patterns"
    __table_args__ = (
        UniqueConstraint("user_id", "client_id", name="uq_bead_patterns_user_client"),
        Index("ix_bead_patterns_user_updated", "user_id", "updated_at", postgresql_where=text("is_deleted = false")),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True, init=False)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("user.id"), index=True)
    client_id: Mapped[UUID]
    name: Mapped[str] = mapped_column(String(128))
    project_data: Mapped[dict] = mapped_column(JSONB, deferred=True)
    content_hash: Mapped[str] = mapped_column(String(64))
    revision: Mapped[int] = mapped_column(default=1)
    source_data: Mapped[bytes | None] = mapped_column(LargeBinary, default=None, deferred=True)
    source_mime: Mapped[str | None] = mapped_column(String(32), default=None)
    source_width: Mapped[int | None] = mapped_column(default=None)
    source_height: Mapped[int | None] = mapped_column(default=None)
    source_size: Mapped[int] = mapped_column(default=0)
    thumbnail_data: Mapped[bytes | None] = mapped_column(LargeBinary, default=None, deferred=True)
    thumbnail_mime: Mapped[str | None] = mapped_column(String(32), default=None)
