"""空间模块：spaces 新增 space_type 列，新建 space_user 成员关联表

Revision ID: b2c3d4e5f6a7
Revises: a3f2c1d4b5e6
Create Date: 2026-08-27 01:20:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b2c3d4e5f6a7'
down_revision: Union[str, Sequence[str], None] = 'a3f2c1d4b5e6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # spaces 新增 space_type：0-私有 1-团队；存量私有空间回填 0
    op.add_column('spaces', sa.Column('space_type', sa.Integer(), nullable=False, server_default='0'))
    op.create_index(op.f('ix_spaces_space_type'), 'spaces', ['space_type'], unique=False)

    # 新建 space_user 成员关联表（团队空间成员与角色，一个成员一个角色）
    op.create_table(
        'space_user',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('space_id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('space_role', sa.String(length=20), nullable=False, server_default='viewer'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['space_id'], ['spaces.id']),
        sa.ForeignKeyConstraint(['user_id'], ['user.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('space_id', 'user_id', name='uk_space_user_space_user'),
    )
    op.create_index(op.f('ix_space_user_space_id'), 'space_user', ['space_id'], unique=False)
    op.create_index(op.f('ix_space_user_user_id'), 'space_user', ['user_id'], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f('ix_space_user_user_id'), table_name='space_user')
    op.drop_index(op.f('ix_space_user_space_id'), table_name='space_user')
    op.drop_table('space_user')
    op.drop_index(op.f('ix_spaces_space_type'), table_name='spaces')
    op.drop_column('spaces', 'space_type')
