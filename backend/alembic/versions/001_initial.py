"""initial schema

Revision ID: 001
Revises:
Create Date: 2026-07-12
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "keywords",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("keyword", sa.Text(), nullable=False),
        sa.Column("brand", sa.String(200), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_keywords_brand", "keywords", ["brand"])

    op.create_table(
        "articles",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("keyword", sa.Text(), nullable=True),
        sa.Column("platform", sa.String(100), nullable=True),
        sa.Column("content", sa.Text(), nullable=True),
        sa.Column("filename", sa.String(500), nullable=True),
        sa.Column("brand", sa.String(200), nullable=True),
        sa.Column("publish_status", sa.String(50), nullable=False, server_default="draft"),
        sa.Column("publish_urls", sa.Text(), nullable=True),
        sa.Column("multimodal", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_articles_brand", "articles", ["brand"])
    op.create_index("ix_articles_platform", "articles", ["platform"])

    op.create_table(
        "optimizations",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("original_content", sa.Text(), nullable=True),
        sa.Column("optimized_content", sa.Text(), nullable=True),
        sa.Column("changes", sa.Text(), nullable=True),
        sa.Column("platform", sa.String(100), nullable=True),
        sa.Column("brand", sa.String(200), nullable=True),
        sa.Column("optimization_type", sa.String(50), nullable=True),
        sa.Column("score_result", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_optimizations_brand", "optimizations", ["brand"])
    op.create_index("ix_optimizations_type", "optimizations", ["optimization_type"])

    op.create_table(
        "verify_results",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("query", sa.Text(), nullable=True),
        sa.Column("brand", sa.String(200), nullable=True),
        sa.Column("verify_model", sa.String(200), nullable=True),
        sa.Column("mention_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("mention_position", sa.String(50), nullable=True),
        sa.Column("content_snippet", sa.Text(), nullable=True),
        sa.Column("is_mentioned", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_verify_brand", "verify_results", ["brand"])
    op.create_index("ix_verify_model", "verify_results", ["verify_model"])

    op.create_table(
        "api_calls",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("operation_type", sa.String(100), nullable=False),
        sa.Column("provider", sa.String(100), nullable=True),
        sa.Column("model", sa.String(200), nullable=True),
        sa.Column("input_tokens", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("output_tokens", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("total_tokens", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("cost_usd", sa.Float(), nullable=False, server_default="0"),
        sa.Column("cost_cny", sa.Float(), nullable=False, server_default="0"),
        sa.Column("keyword", sa.Text(), nullable=True),
        sa.Column("platform", sa.String(100), nullable=True),
        sa.Column("brand", sa.String(200), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_api_calls_brand", "api_calls", ["brand"])
    op.create_index("ix_api_calls_operation", "api_calls", ["operation_type"])
    op.create_index("ix_api_calls_provider", "api_calls", ["provider"])

    op.create_table(
        "workflows",
        sa.Column("id", sa.String(100), primary_key=True),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("steps", sa.Text(), nullable=False),
        sa.Column("schedule", sa.String(200), nullable=True),
        sa.Column("conditions", sa.Text(), nullable=True),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("brand", sa.String(200), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "workflow_templates",
        sa.Column("id", sa.String(100), primary_key=True),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("steps", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "workflow_executions",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("workflow_id", sa.String(100), sa.ForeignKey("workflows.id", ondelete="CASCADE"), nullable=False),
        sa.Column("status", sa.String(50), nullable=False),
        sa.Column("result", sa.Text(), nullable=True),
        sa.Column("progress", sa.Float(), nullable=False, server_default="0"),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("logs", sa.Text(), nullable=True),
    )
    op.create_index("ix_we_workflow_id", "workflow_executions", ["workflow_id"])
    op.create_index("ix_we_status", "workflow_executions", ["status"])

    op.create_table(
        "platform_accounts",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("platform", sa.String(100), nullable=False),
        sa.Column("account_type", sa.String(50), nullable=False),
        sa.Column("account_name", sa.String(200), nullable=True),
        sa.Column("api_key", sa.Text(), nullable=True),
        sa.Column("api_secret", sa.Text(), nullable=True),
        sa.Column("access_token", sa.Text(), nullable=True),
        sa.Column("refresh_token", sa.Text(), nullable=True),
        sa.Column("token_expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("config_json", sa.Text(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("brand", sa.String(200), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("platform", "brand", "account_name", name="uq_platform_brand_account"),
    )
    op.create_index("ix_pa_brand", "platform_accounts", ["brand"])
    op.create_index("ix_pa_platform", "platform_accounts", ["platform"])

    op.create_table(
        "publish_records",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("article_id", sa.Integer(), sa.ForeignKey("articles.id", ondelete="SET NULL"), nullable=True),
        sa.Column("platform", sa.String(100), nullable=False),
        sa.Column("publish_method", sa.String(50), nullable=False),
        sa.Column("publish_status", sa.String(50), nullable=False),
        sa.Column("publish_url", sa.Text(), nullable=True),
        sa.Column("publish_id", sa.String(500), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("retry_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_pr_article", "publish_records", ["article_id"])
    op.create_index("ix_pr_platform", "publish_records", ["platform"])

    op.create_table(
        "knowledge_docs",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("filename", sa.String(500), nullable=False),
        sa.Column("file_path", sa.Text(), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("content_hash", sa.String(64), nullable=True),
        sa.Column("file_type", sa.String(50), nullable=True),
        sa.Column("brand", sa.String(200), nullable=True),
        sa.Column("chunk_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_kd_brand", "knowledge_docs", ["brand"])

    op.create_table(
        "app_config",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("config_json", sa.Text(), nullable=False, server_default="{}"),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # 插入默认配置行
    op.execute("INSERT INTO app_config (id, config_json) VALUES (1, '{}')")


def downgrade() -> None:
    op.drop_table("app_config")
    op.drop_table("knowledge_docs")
    op.drop_table("publish_records")
    op.drop_table("platform_accounts")
    op.drop_table("workflow_executions")
    op.drop_table("workflow_templates")
    op.drop_table("workflows")
    op.drop_table("api_calls")
    op.drop_table("verify_results")
    op.drop_table("optimizations")
    op.drop_table("articles")
    op.drop_table("keywords")
