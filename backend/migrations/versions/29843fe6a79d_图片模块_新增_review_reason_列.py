"""图片模块: 新增 review_reason 列

Revision ID: 29843fe6a79d
Revises: c63446b89172
Create Date: 2026-08-14 17:59:35.476020

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '29843fe6a79d'
down_revision: Union[str, Sequence[str], None] = 'c63446b89172'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # 仅新增 review_reason 列（已手动清理 autogenerate 对 id 唯一约束的误检测）
    op.add_column('pictures', sa.Column('review_reason', sa.String(length=512), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('pictures', 'review_reason')
