"""FastAPI 依赖注入"""
import hmac

from fastapi import Depends, Header
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.database import get_db
from app.core.exceptions import AuthError
from app.services.article_service import ArticleService
from app.services.attribution_service import AttributionService
from app.services.config_service import ConfigService
from app.services.data_service import DataService
from app.services.dds_service import DDSService
from app.services.keyword_service import KeywordService
from app.services.knowledge_service import KnowledgeService
from app.services.monitor_service import MonitorService
from app.services.optimization_service import OptimizationService
from app.services.platform_service import PlatformService
from app.services.report_service import ReportService
from app.services.roi_service import ROIService
from app.services.schema_service import SchemaService
from app.services.scoring_service import ScoringService
from app.services.template_service import TemplateService
from app.services.verify_service import VerifyService
from app.services.workflow_service import WorkflowService

settings = get_settings()


async def get_config_service(db: AsyncSession = Depends(get_db)) -> ConfigService:
    return ConfigService(db)


async def get_keyword_service(db: AsyncSession = Depends(get_db)) -> KeywordService:
    return KeywordService(db)


async def get_article_service(db: AsyncSession = Depends(get_db)) -> ArticleService:
    return ArticleService(db)


async def get_optimization_service(db: AsyncSession = Depends(get_db)) -> OptimizationService:
    return OptimizationService(db)


async def get_scoring_service(db: AsyncSession = Depends(get_db)) -> ScoringService:
    return ScoringService(db)


async def get_verify_service(db: AsyncSession = Depends(get_db)) -> VerifyService:
    return VerifyService(db)


async def get_roi_service(db: AsyncSession = Depends(get_db)) -> ROIService:
    from app.services.config_service import ConfigService
    cfg_svc = ConfigService(db)
    cfg = await cfg_svc.get_config()
    return ROIService(
        mention_value=cfg.get("roi_value_per_mention", 50.0),
    )


async def get_knowledge_service(db: AsyncSession = Depends(get_db)) -> KnowledgeService:
    return KnowledgeService(db)


async def get_workflow_service(db: AsyncSession = Depends(get_db)) -> WorkflowService:
    return WorkflowService(db)


async def get_platform_service(db: AsyncSession = Depends(get_db)) -> PlatformService:
    return PlatformService(db)


async def get_schema_service(db: AsyncSession = Depends(get_db)) -> SchemaService:
    return SchemaService(db)


async def get_attribution_service(db: AsyncSession = Depends(get_db)) -> AttributionService:
    return AttributionService(db)


async def get_report_service(db: AsyncSession = Depends(get_db)) -> ReportService:
    from app.services.config_service import ConfigService
    cfg_svc = ConfigService(db)
    cfg = await cfg_svc.get_config()
    return ReportService(db, mention_value=cfg.get("roi_value_per_mention", 50.0))


async def get_monitor_service(db: AsyncSession = Depends(get_db)) -> MonitorService:
    return MonitorService(db)


async def get_dds_service(db: AsyncSession = Depends(get_db)) -> DDSService:
    return DDSService(db)


async def get_data_service(db: AsyncSession = Depends(get_db)) -> DataService:
    return DataService(db)


async def get_template_service(db: AsyncSession = Depends(get_db)) -> TemplateService:
    return TemplateService(db)


def require_api_key(x_api_key: str = Header(default="", alias="X-API-Key")) -> None:
    """API Key 认证依赖（使用常量时间比较防时序攻击）"""
    if not settings.API_KEY:
        return
    if not hmac.compare_digest(x_api_key or "", settings.API_KEY):
        raise AuthError("无效的 API Key")
