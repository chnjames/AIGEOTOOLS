"""add sentiment, positive/negative mentions, verification mode, diagnosis, recommended_brands to verify_results, add article_versions table

Revision ID: 003
Revises: 002
Create Date: 2026-07-12

"""
from alembic import op
import sqlalchemy as sa


revision = '003'
down_revision = '002'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # add columns to verify_results using batch_alter_table for SQLite compatibility
    with op.batch_alter_table('verify_results') as batch_op:
        batch_op.add_column(sa.Column('sentiment', sa.String(20), nullable=True))
        batch_op.add_column(sa.Column('positive_mentions', sa.Integer(), server_default='0'))
        batch_op.add_column(sa.Column('negative_mentions', sa.Integer(), server_default='0'))
        batch_op.add_column(sa.Column('verification_mode', sa.String(20), server_default='prompted'))
        batch_op.add_column(sa.Column('diagnosis', sa.Text(), nullable=True))
        batch_op.add_column(sa.Column('recommended_brands', sa.Text(), nullable=True))

    # article_versions
    op.create_table(
        'article_versions',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('article_id', sa.Integer(), sa.ForeignKey('articles.id'), nullable=False, index=True),
        sa.Column('version_number', sa.Integer(), nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('source', sa.String(50), nullable=True),
        sa.Column('note', sa.Text(), nullable=True),
        sa.Column('dds_score', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
    )


def downgrade() -> None:
    op.drop_table('article_versions')

    with op.batch_alter_table('verify_results') as batch_op:
        batch_op.drop_column('recommended_brands')
        batch_op.drop_column('diagnosis')
        batch_op.drop_column('verification_mode')
        batch_op.drop_column('negative_mentions')
        batch_op.drop_column('positive_mentions')
        batch_op.drop_column('sentiment')
