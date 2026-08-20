"""图片模块：pictures 表新增 primary_color（主色调）列

Revision ID: a3f2c1d4b5e6
Revises: 9c4e7b1f6a3d
Create Date: 2026-08-21 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a3f2c1d4b5e6'
down_revision: Union[str, Sequence[str], None] = '9c4e7b1f6a3d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # 主色调 0xRRGGBB 的整数值；NULL 表示未提取（如公共图库图片）
    op.add_column('pictures', sa.Column('primary_color', sa.Integer(), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('pictures', 'primary_color')
