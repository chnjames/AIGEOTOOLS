"""add monitor, dds_scores, optimization_actions, marketing_reports tables

Revision ID: 002
Revises: 001
Create Date: 2026-07-12

"""
from alembic import op
import sqlalchemy as sa

revision = '002'
down_revision = '001'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # monitor_tasks
    op.create_table(
        'monitor_tasks',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('name', sa.String(200), nullable=False),
        sa.Column('queries', sa.Text(), nullable=False),
        sa.Column('platforms', sa.String(500), server_default='deepseek'),
        sa.Column('schedule_type', sa.String(20), server_default='daily'),
        sa.Column('schedule_time', sa.String(10), server_default='09:00'),
        sa.Column('is_active', sa.Boolean(), server_default='1'),
        sa.Column('brand', sa.String(200), server_default=''),
        sa.Column('competitors', sa.Text(), server_default=''),
        sa.Column('alert_threshold', sa.Float(), server_default='0.5'),
        sa.Column('last_run_at', sa.DateTime(), nullable=True),
        sa.Column('next_run_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
    )

    # monitor_results
    op.create_table(
        'monitor_results',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('task_id', sa.Integer(), sa.ForeignKey('monitor_tasks.id'), nullable=False, index=True),
        sa.Column('query', sa.String(500), nullable=False),
        sa.Column('platform', sa.String(100), nullable=False),
        sa.Column('is_mentioned', sa.Boolean(), server_default='0'),
        sa.Column('mention_position', sa.String(50), server_default=''),
        sa.Column('mention_count', sa.Integer(), server_default='0'),
        sa.Column('sentiment', sa.String(20), server_default='neutral'),
        sa.Column('content_snippet', sa.Text(), server_default=''),
        sa.Column('competitor_mentions', sa.Text(), server_default=''),
        sa.Column('is_alert', sa.Boolean(), server_default='0'),
        sa.Column('run_batch', sa.String(50), nullable=False, index=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
    )

    # alerts
    op.create_table(
        'alerts',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('alert_type', sa.String(50), nullable=False),
        sa.Column('level', sa.String(20), server_default='warning'),
        sa.Column('title', sa.String(300), nullable=False),
        sa.Column('message', sa.Text(), server_default=''),
        sa.Column('task_id', sa.Integer(), sa.ForeignKey('monitor_tasks.id'), nullable=True),
        sa.Column('result_id', sa.Integer(), sa.ForeignKey('monitor_results.id'), nullable=True),
        sa.Column('is_read', sa.Boolean(), server_default='0'),
        sa.Column('metadata_json', sa.Text(), server_default='{}'),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
    )

    # dds_scores
    op.create_table(
        'dds_scores',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('article_id', sa.Integer(), sa.ForeignKey('articles.id'), nullable=True, index=True),
        sa.Column('brand', sa.String(200), server_default=''),
        sa.Column('semantic_depth', sa.Float(), server_default='0'),
        sa.Column('data_support', sa.Float(), server_default='0'),
        sa.Column('authoritative_source', sa.Float(), server_default='0'),
        sa.Column('total_score', sa.Float(), server_default='0'),
        sa.Column('depth_details', sa.Text(), server_default='{}'),
        sa.Column('data_details', sa.Text(), server_default='{}'),
        sa.Column('source_details', sa.Text(), server_default='{}'),
        sa.Column('improvements', sa.Text(), server_default='[]'),
        sa.Column('strengths', sa.Text(), server_default='[]'),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
    )

    # optimization_actions
    op.create_table(
        'optimization_actions',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('action_type', sa.String(100), nullable=False),
        sa.Column('description', sa.String(500), server_default=''),
        sa.Column('brand', sa.String(200), server_default='', index=True),
        sa.Column('article_id', sa.Integer(), sa.ForeignKey('articles.id'), nullable=True),
        sa.Column('keyword', sa.String(500), server_default=''),
        sa.Column('platform', sa.String(100), server_default=''),
        sa.Column('score_before', sa.Float(), nullable=True),
        sa.Column('score_after', sa.Float(), nullable=True),
        sa.Column('mention_rate_at_action', sa.Float(), nullable=True),
        sa.Column('metadata_json', sa.Text(), server_default='{}'),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
    )

    # marketing_reports
    op.create_table(
        'marketing_reports',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('title', sa.String(300), nullable=False),
        sa.Column('report_type', sa.String(50), server_default='weekly'),
        sa.Column('brand', sa.String(200), server_default='', index=True),
        sa.Column('date_from', sa.DateTime(), nullable=True),
        sa.Column('date_to', sa.DateTime(), nullable=True),
        sa.Column('summary', sa.Text(), server_default=''),
        sa.Column('kpi_data', sa.Text(), server_default='{}'),
        sa.Column('mention_trend', sa.Text(), server_default='[]'),
        sa.Column('cost_data', sa.Text(), server_default='{}'),
        sa.Column('optimization_effect', sa.Text(), server_default='[]'),
        sa.Column('competitor_analysis', sa.Text(), server_default='{}'),
        sa.Column('recommendations', sa.Text(), server_default='[]'),
        sa.Column('markdown_content', sa.Text(), server_default=''),
        sa.Column('share_token', sa.String(100), server_default='', unique=True, index=True),
        sa.Column('is_published', sa.Boolean(), server_default='0'),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
    )


def downgrade() -> None:
    op.drop_table('marketing_reports')
    op.drop_table('optimization_actions')
    op.drop_table('dds_scores')
    op.drop_table('alerts')
    op.drop_table('monitor_results')
    op.drop_table('monitor_tasks')
