"""API v1 总路由"""
from fastapi import APIRouter

from app.api.v1.config import router as config_router
from app.api.v1.keywords import router as keywords_router
from app.api.v1.articles import router as articles_router
from app.api.v1.optimizations import router as optimizations_router
from app.api.v1.scoring import router as scoring_router
from app.api.v1.verification import router as verification_router
from app.api.v1.reports import router as reports_router
from app.api.v1.workflows import router as workflows_router
from app.api.v1.platforms import router as platforms_router
from app.api.v1.knowledge import router as knowledge_router
from app.api.v1.resources import router as resources_router
from app.api.v1.monitor import router as monitor_router
from app.api.v1.dds import router as dds_router
from app.api.v1.schema_tools import router as schema_tools_router
from app.api.v1.attribution import router as attribution_router, report_router
from app.api.v1.data import router as data_router
from app.api.v1.templates import router as templates_router

api_router = APIRouter()

api_router.include_router(config_router)
api_router.include_router(keywords_router)
api_router.include_router(articles_router)
api_router.include_router(optimizations_router)
api_router.include_router(scoring_router)
api_router.include_router(verification_router)
api_router.include_router(reports_router)
api_router.include_router(workflows_router)
api_router.include_router(platforms_router)
api_router.include_router(knowledge_router)
api_router.include_router(resources_router)
api_router.include_router(monitor_router)
api_router.include_router(dds_router)
api_router.include_router(schema_tools_router)
api_router.include_router(attribution_router)
api_router.include_router(report_router)
api_router.include_router(data_router)
api_router.include_router(templates_router)
