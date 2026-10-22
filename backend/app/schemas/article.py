"""文章相关 Schema"""
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


class ArticleResponse(BaseModel):
    id: int
    keyword: Optional[str] = None
    platform: Optional[str] = None
    content: Optional[str] = None
    filename: Optional[str] = None
    brand: Optional[str] = None
    publish_status: str = "draft"
    publish_urls: Optional[str] = None
    multimodal: Optional[str] = None
    created_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class ArticleCreate(BaseModel):
    keyword: str = ""
    platform: str
    content: str
    filename: str = ""
    brand: str = ""


class ArticleUpdate(BaseModel):
    content: Optional[str] = None
    filename: Optional[str] = None
    publish_status: Optional[str] = None
    publish_urls: Optional[str] = None
    note: Optional[str] = None


class ArticleGenerateRequest(BaseModel):
    keyword: str = Field(..., description="目标关键词")
    platform: str = Field(..., description="目标平台")
    brand: str = ""
    advantages: str = ""
    knowledge_context: Optional[str] = None
    use_knowledge: bool = False
    style: str = "professional"
    word_count: int = Field(default=1500, ge=200, le=5000)
    temperature: float = 0.7
    provider: Optional[str] = None
    api_key: Optional[str] = None
    model: Optional[str] = None


class BatchGenerateRequest(BaseModel):
    keywords: list[str] = Field(default_factory=list, description="关键词列表；当提供 keyword_platforms 时可为空")
    platforms: list[str] = Field(default_factory=list, description="目标平台列表（统一应用于所有 keywords）；当提供 keyword_platforms 时可为空")
    brand: str = ""
    advantages: str = ""
    knowledge_context: Optional[str] = None
    use_knowledge: bool = False
    keyword_platforms: Optional[dict[str, list[str]]] = Field(
        default=None,
        description="混合批量映射：关键词 -> 目标平台列表，为每个关键词指定不同平台",
    )
    style: str = "professional"
    word_count: int = Field(default=1500, ge=200, le=5000)
    temperature: float = 0.7
    provider: Optional[str] = None
    api_key: Optional[str] = None
    model: Optional[str] = None


class MultimodalRequest(BaseModel):
    article_id: int
    generate_image_desc: bool = True
    generate_video_script: bool = False
    temperature: float = 0.7
    provider: Optional[str] = None
    api_key: Optional[str] = None
    model: Optional[str] = None


class ArticleVersionResponse(BaseModel):
    id: int
    article_id: int
    version_number: int
    source: Optional[str] = None
    note: Optional[str] = None
    content: Optional[str] = None
    dds_score: Optional[float] = None
    created_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class ArticleSearchItem(BaseModel):
    """文章搜索结果项（用于 selector/autocomplete）"""
    id: int
    keyword: Optional[str] = None
    platform: Optional[str] = None
    brand: Optional[str] = None
    filename: Optional[str] = None

    model_config = {"from_attributes": True}


class OriginalContentResponse(BaseModel):
    """原始版本内容响应"""
    article_id: int
    original_content: Optional[str] = None


class DiffResponse(BaseModel):
    diff_html: str
    additions: int
    deletions: int
    version_a: int
    version_b: int
