"""空间模块：新建 spaces 表

Revision ID: 3f8a1c5b9d2e
Revises: 29843fe6a79d
Create Date: 2026-08-19 18:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '3f8a1c5b9d2e'
down_revision: Union[str, Sequence[str], None] = '29843fe6a79d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table('spaces',
    sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
    sa.Column('name', sa.String(length=128), nullable=False),
    sa.Column('user_id', sa.Integer(), nullable=False),
    sa.Column('space_level', sa.Integer(), nullable=False),
    sa.Column('max_size', sa.BigInteger(), nullable=False),
    sa.Column('max_count', sa.BigInteger(), nullable=False),
    sa.Column('total_size', sa.BigInteger(), nullable=False),
    sa.Column('total_count', sa.BigInteger(), nullable=False),
    sa.Column('status', sa.String(length=20), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('deleted_at', sa.TIMESTAMP(timezone=True), nullable=True),
    sa.Column('is_deleted', sa.Boolean(), nullable=False),
    sa.ForeignKeyConstraint(['user_id'], ['user.id'], ),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('id')
    )
    op.create_index(op.f('ix_spaces_name'), 'spaces', ['name'], unique=False)
    op.create_index(op.f('ix_spaces_space_level'), 'spaces', ['space_level'], unique=False)
    op.create_index(op.f('ix_spaces_status'), 'spaces', ['status'], unique=False)
    op.create_index(op.f('ix_spaces_user_id'), 'spaces', ['user_id'], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f('ix_spaces_user_id'), table_name='spaces')
    op.drop_index(op.f('ix_spaces_status'), table_name='spaces')
    op.drop_index(op.f('ix_spaces_space_level'), table_name='spaces')
    op.drop_index(op.f('ix_spaces_name'), table_name='spaces')
    op.drop_table('spaces')
