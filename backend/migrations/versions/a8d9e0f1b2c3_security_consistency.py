"""空间活跃归属唯一约束和扩图任务归属表。

Revision ID: a8d9e0f1b2c3
Revises: f3c4d5e6a7b8
"""

import sqlalchemy as sa
from alembic import op

revision = "a8d9e0f1b2c3"
down_revision = "f3c4d5e6a7b8"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """历史重复空间必须人工确认，不自动删除或合并业务数据。"""
    duplicates = (
        op.get_bind()
        .execute(
            sa.text(
                "SELECT user_id, space_type FROM spaces WHERE is_deleted = false "
                "GROUP BY user_id, space_type HAVING count(*) > 1 LIMIT 1"
            )
        )
        .first()
    )
    if duplicates:
        raise RuntimeError("存在同一用户同类型的多个活跃空间，请人工处理重复空间后重试迁移")
    op.create_index(
        "uq_spaces_active_owner_type",
        "spaces",
        ["user_id", "space_type"],
        unique=True,
        postgresql_where=sa.text("is_deleted = false"),
    )
    op.create_table(
        "outpainting_tasks",
        sa.Column("task_id", sa.String(256), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("user.id"), nullable=False),
        sa.Column("picture_id", sa.Integer(), sa.ForeignKey("pictures.id"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_outpainting_tasks_user_id", "outpainting_tasks", ["user_id"])
    op.create_index("ix_outpainting_tasks_picture_id", "outpainting_tasks", ["picture_id"])


def downgrade() -> None:
    """仅撤回本轮新增约束及任务归属，不改变原有图库数据。"""
    op.drop_table("outpainting_tasks")
    op.drop_index("uq_spaces_active_owner_type", table_name="spaces")
