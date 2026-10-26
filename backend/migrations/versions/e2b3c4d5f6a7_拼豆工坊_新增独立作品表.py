"""拼豆作品及工作源独立存储，不修改现有业务表。"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "e2b3c4d5f6a7"
down_revision = "d1e2f3a4b5c6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """创建作品表；字段和现有用户主键类型一致。"""
    op.create_table(
        "bead_patterns",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("user.id"), nullable=False),
        sa.Column("client_id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(128), nullable=False),
        sa.Column("project_data", postgresql.JSONB(), nullable=False),
        sa.Column("content_hash", sa.String(64), nullable=False),
        sa.Column("revision", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("source_data", sa.LargeBinary()),
        sa.Column("source_mime", sa.String(32)),
        sa.Column("source_width", sa.Integer()),
        sa.Column("source_height", sa.Integer()),
        sa.Column("source_size", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("thumbnail_data", sa.LargeBinary()),
        sa.Column("thumbnail_mime", sa.String(32)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("is_deleted", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("deleted_at", sa.DateTime(timezone=True)),
        sa.UniqueConstraint("user_id", "client_id", name="uq_bead_patterns_user_client"),
    )
    op.create_index("ix_bead_patterns_user_id", "bead_patterns", ["user_id"])
    op.create_index(
        "ix_bead_patterns_user_updated",
        "bead_patterns",
        ["user_id", "updated_at"],
        postgresql_where=sa.text("is_deleted = false"),
    )


def downgrade() -> None:
    """仅移除拼豆作品表，降级会丢失此模块数据。"""
    op.drop_table("bead_patterns")
