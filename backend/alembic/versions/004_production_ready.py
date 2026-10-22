"""add audit_logs, platform_templates tables; add is_favorite/tags to keywords, full_response to verify_results

Revision ID: 004_prod_ready
Revises: 003
Create Date: 2026-07-12

"""
from alembic import op
import sqlalchemy as sa


revision = '004_prod_ready'
down_revision = '003'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # audit_logs
    op.create_table(
        'audit_logs',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('action', sa.String(50), nullable=False),
        sa.Column('resource_type', sa.String(50), nullable=False),
        sa.Column('resource_id', sa.String(100), nullable=True),
        sa.Column('detail', sa.Text(), nullable=True),
        sa.Column('result', sa.String(20), nullable=False, server_default='success'),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('operator', sa.String(100), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now()),
    )
    op.create_index('ix_audit_action', 'audit_logs', ['action'])
    op.create_index('ix_audit_resource', 'audit_logs', ['resource_type'])
    op.create_index('ix_audit_created', 'audit_logs', ['created_at'])

    # platform_templates
    op.create_table(
        'platform_templates',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('name', sa.String(100), nullable=False, unique=True),
        sa.Column('style_instruction', sa.Text(), nullable=False),
        sa.Column('filename_suffix', sa.String(50), nullable=False, server_default='.md'),
        sa.Column('group_name', sa.String(50), nullable=False, server_default='其他'),
        sa.Column('is_default', sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column('word_count_default', sa.Integer(), nullable=False, server_default='1500'),
        sa.Column('extra_config', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now()),
    )
    op.create_index('ix_platform_tpl_group', 'platform_templates', ['group_name'])
    op.create_index('ix_platform_tpl_active', 'platform_templates', ['is_active'])

    # add columns to keywords using batch_alter_table for SQLite compatibility
    with op.batch_alter_table('keywords') as batch_op:
        batch_op.add_column(sa.Column('is_favorite', sa.Boolean(), nullable=False, server_default=sa.false()))
        batch_op.add_column(sa.Column('tags', sa.String(500), nullable=True))
    op.create_index('ix_keywords_favorite', 'keywords', ['is_favorite'])

    # add column to verify_results using batch_alter_table for SQLite compatibility
    with op.batch_alter_table('verify_results') as batch_op:
        batch_op.add_column(sa.Column('full_response', sa.Text(), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table('verify_results') as batch_op:
        batch_op.drop_column('full_response')

    op.drop_index('ix_keywords_favorite', table_name='keywords')
    with op.batch_alter_table('keywords') as batch_op:
        batch_op.drop_column('tags')
        batch_op.drop_column('is_favorite')

    op.drop_table('platform_templates')
    op.drop_table('audit_logs')
