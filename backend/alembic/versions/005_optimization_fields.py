"""add article_id, keyword, applied columns to optimizations table

Revision ID: 005_opt_fields
Revises: 004_prod_ready
Create Date: 2026-07-25

修复 H1: optimization 模型在阶段四新增了 article_id(FK)、keyword、applied 字段，
但未提供对应的 Alembic 迁移，导致生产环境 `alembic upgrade head` 后
`/optimizations/{opt_id}/apply` 端点读写这些字段会抛 OperationalError。
"""
from alembic import op
import sqlalchemy as sa


revision = '005_opt_fields'
down_revision = '004_prod_ready'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # SQLite 不支持直接 ADD COLUMN with FK，需用 batch_alter_table 重建表
    # 外键约束也必须在 batch 模式内部创建（SQLite 限制）
    with op.batch_alter_table('optimizations') as batch_op:
        batch_op.add_column(sa.Column('article_id', sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column('keyword', sa.String(500), nullable=True))
        batch_op.add_column(
            sa.Column('applied', sa.Boolean(), nullable=False, server_default=sa.false())
        )
        batch_op.create_foreign_key(
            'fk_optimizations_article_id', 'articles',
            ['article_id'], ['id'], ondelete='SET NULL',
        )
        batch_op.create_index('ix_optimizations_article', ['article_id'])


def downgrade() -> None:
    op.drop_index('ix_optimizations_article', table_name='optimizations')
    op.drop_constraint('fk_optimizations_article_id', 'optimizations', type_='foreignkey')
    with op.batch_alter_table('optimizations') as batch_op:
        batch_op.drop_column('applied')
        batch_op.drop_column('keyword')
        batch_op.drop_column('article_id')
