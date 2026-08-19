"""空间模块：pictures 表新增 space_id 列

Revision ID: 9c4e7b1f6a3d
Revises: 3f8a1c5b9d2e
Create Date: 2026-08-19 18:01:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '9c4e7b1f6a3d'
down_revision: Union[str, Sequence[str], None] = '3f8a1c5b9d2e'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # space_id 为空表示公共图库图片，非空表示属于某私有空间
    op.add_column('pictures', sa.Column('space_id', sa.Integer(), nullable=True))
    op.create_foreign_key(
        'fk_pictures_space_id_spaces', 'pictures', 'spaces', ['space_id'], ['id']
    )
    op.create_index(op.f('ix_pictures_space_id'), 'pictures', ['space_id'], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f('ix_pictures_space_id'), table_name='pictures')
    op.drop_constraint('fk_pictures_space_id_spaces', 'pictures', type_='foreignkey')
    op.drop_column('pictures', 'space_id')
