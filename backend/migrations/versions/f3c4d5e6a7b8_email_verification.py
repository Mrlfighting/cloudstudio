"""邮箱验证与事务邮件：保留既有用户字段，扩展长度和规范化唯一索引。"""

import sqlalchemy as sa
from alembic import op

revision = "f3c4d5e6a7b8"
down_revision = "e2b3c4d5f6a7"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """遇到历史冲突停止，不静默合并账号；事务锁阻止预检后插入冲突。"""
    connection = op.get_bind()
    connection.execute(sa.text('LOCK TABLE "user" IN SHARE ROW EXCLUSIVE MODE'))
    duplicate = connection.execute(
        sa.text("""
        SELECT 1 FROM "user" WHERE email IS NOT NULL
        GROUP BY lower(btrim(email)) HAVING count(*) > 1 LIMIT 1
    """)
    ).first()
    if duplicate:
        raise RuntimeError("存在规范化后重复邮箱，请人工处理后重试迁移；没有修改账号")
    op.alter_column("user", "email", existing_type=sa.String(50), type_=sa.String(254), existing_nullable=True)
    op.create_index("uq_user_email_normalized", "user", [sa.text("lower(btrim(email))")], unique=True)
    op.create_table(
        "email_verification_challenges",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("user.id"), nullable=False),
        sa.Column("email", sa.String(254), nullable=False),
        sa.Column("original_email", sa.String(254)),
        sa.Column("purpose", sa.String(16), nullable=False),
        sa.Column("code_hash", sa.String(64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("attempts", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("consumed_at", sa.DateTime(timezone=True)),
        sa.Column("invalidated_at", sa.DateTime(timezone=True)),
    )
    op.create_index("ix_email_challenge_user_created", "email_verification_challenges", ["user_id", "created_at"])
    op.create_table(
        "email_outbox",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("user.id"), nullable=False),
        sa.Column("kind", sa.String(16), nullable=False),
        sa.Column("recipient", sa.String(254), nullable=False),
        sa.Column("dedupe_key", sa.String(120), nullable=False, unique=True),
        sa.Column("payload", sa.LargeBinary()),
        sa.Column("challenge_id", sa.Uuid(), sa.ForeignKey("email_verification_challenges.id")),
        sa.Column("status", sa.String(16), nullable=False, server_default="pending"),
        sa.Column("attempts", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("next_attempt_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("lease_until", sa.DateTime(timezone=True)),
        sa.Column("lease_token", sa.Uuid()),
        sa.Column("sent_at", sa.DateTime(timezone=True)),
        sa.Column("error_code", sa.String(80)),
    )
    op.create_index("ix_email_outbox_due", "email_outbox", ["status", "next_attempt_at"])


def downgrade() -> None:
    """不能截断升级后合法长邮箱；有长数据时要求先人工备份处理。"""
    connection = op.get_bind()
    connection.execute(sa.text('LOCK TABLE "user" IN SHARE ROW EXCLUSIVE MODE'))
    if connection.execute(sa.text('SELECT 1 FROM "user" WHERE length(email)>50 LIMIT 1')).first():
        raise RuntimeError("存在长度超过50的邮箱，禁止有损降级")
    op.drop_table("email_outbox")
    op.drop_table("email_verification_challenges")
    op.drop_index("uq_user_email_normalized", table_name="user")
    op.alter_column("user", "email", existing_type=sa.String(254), type_=sa.String(50), existing_nullable=True)
