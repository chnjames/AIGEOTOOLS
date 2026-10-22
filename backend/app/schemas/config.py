"""应用配置 Schema"""
from typing import Optional
from pydantic import BaseModel, Field


class ProviderKey(BaseModel):
    provider: str
    api_key: str = ""
    is_configured: bool = False


class AppConfigUpdate(BaseModel):
    gen_provider: Optional[str] = Field(default=None, description="生成LLM提供商")
    gen_api_key: Optional[str] = Field(default=None, description="生成LLM API Key")
    gen_base_url: Optional[str] = Field(default=None, description="生成LLM自定义API地址（代理/中转）")
    gen_model: Optional[str] = Field(default=None, description="生成LLM模型名称")
    verify_providers: Optional[list[str]] = Field(default=None, description="验证模型列表")
    verify_keys: Optional[dict[str, str]] = Field(default=None, description="验证模型 API Keys")
    tongyi_wanxiang_api_key: Optional[str] = Field(default=None, description="通义万相 API Key")
    brand: Optional[str] = Field(default=None, description="品牌名称")
    advantages: Optional[str] = Field(default=None, description="核心优势")
    competitors: Optional[str] = Field(default=None, description="竞品品牌(每行一个)")
    temperature: Optional[float] = Field(default=None, ge=0.0, le=1.0, description="温度参数")
    # 新配置项
    use_knowledge_base: Optional[bool] = Field(default=None, description="是否启用知识库增强")
    roi_value_per_mention: Optional[float] = Field(default=None, ge=0, description="单次提及估算价值(元)")
    platform_value_coefficients: Optional[dict[str, float]] = Field(default=None, description="各平台价值系数")
    first_run_completed: Optional[bool] = Field(default=None, description="首次配置向导是否已完成")
    default_verify_mode: Optional[str] = Field(default=None, description="默认验证模式: natural/prompted")


class AppConfigResponse(BaseModel):
    gen_provider: str = "DeepSeek"
    gen_api_key_masked: str = ""
    gen_api_key_configured: bool = False
    gen_base_url: str = ""
    gen_model: str = ""
    verify_providers: list[str] = Field(default_factory=list)
    verify_keys_configured: dict[str, bool] = Field(default_factory=dict)
    tongyi_wanxiang_configured: bool = False
    brand: str = ""
    advantages: str = ""
    competitors: str = ""
    temperature: float = 0.7
    use_knowledge_base: bool = False
    roi_value_per_mention: float = 50.0
    platform_value_coefficients: dict[str, float] = Field(default_factory=dict)
    first_run_completed: bool = False
    default_verify_mode: str = "natural"


class ProviderTestRequest(BaseModel):
    provider: str
    api_key: str
    model: Optional[str] = None
    base_url: Optional[str] = None


class ProviderTestResponse(BaseModel):
    success: bool
    message: str
