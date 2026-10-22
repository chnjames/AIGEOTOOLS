"""层级化自定义异常体系"""
from typing import Any, Optional


class GEOAppException(Exception):
    """应用基础异常"""
    def __init__(
        self,
        code: str = "INTERNAL_ERROR",
        message: str = "服务器内部错误",
        status_code: int = 500,
        details: Optional[dict[str, Any]] = None,
    ):
        self.code = code
        self.message = message
        self.status_code = status_code
        self.details = dict(details) if details else {}
        super().__init__(message)


class ConfigError(GEOAppException):
    """配置相关错误"""
    def __init__(self, message: str = "配置错误", details: Optional[dict[str, Any]] = None):
        super().__init__(code="CONFIG_ERROR", message=message, status_code=400, details=details)


class AuthError(GEOAppException):
    """认证/授权错误"""
    def __init__(self, message: str = "认证失败", details: Optional[dict[str, Any]] = None):
        super().__init__(code="AUTH_ERROR", message=message, status_code=401, details=details)


class NotFoundError(GEOAppException):
    """资源不存在"""
    def __init__(self, message: str = "资源不存在", details: Optional[dict[str, Any]] = None):
        super().__init__(code="NOT_FOUND", message=message, status_code=404, details=details)


class ValidationError(GEOAppException):
    """参数校验错误"""
    def __init__(self, message: str = "参数校验失败", details: Optional[dict[str, Any]] = None):
        super().__init__(code="VALIDATION_ERROR", message=message, status_code=422, details=details)


class LLMError(GEOAppException):
    """LLM 调用错误基类"""
    def __init__(
        self,
        message: str = "LLM 调用失败",
        error_type: str = "unknown",
        provider: str = "",
        model: str = "",
        raw_response: str = "",
        retriable: bool = False,
        details: Optional[dict[str, Any]] = None,
    ):
        d: dict[str, Any] = dict(details) if details else {}
        d.update({
            "error_type": error_type,
            "provider": provider,
            "model": model,
            "raw_response": raw_response[:200],
            "retriable": retriable,
        })
        super().__init__(code=f"LLM_{error_type.upper()}", message=message, status_code=502, details=d)
        self.error_type = error_type
        self.provider = provider
        self.model = model
        self.retriable = retriable


class LLMAuthError(LLMError):
    """API Key 无效或过期 (401/403)"""
    def __init__(self, provider: str = "", raw: str = ""):
        super().__init__(
            message="API Key 无效或已过期，请检查配置",
            error_type="auth_error", provider=provider,
            raw_response=raw, retriable=False,
        )


class LLMBalanceError(LLMError):
    """余额不足"""
    def __init__(self, provider: str = "", raw: str = ""):
        super().__init__(
            message="API 余额不足，请充值后重试",
            error_type="balance_error", provider=provider,
            raw_response=raw, retriable=False,
        )


class LLMTimeoutError(LLMError):
    """请求超时"""
    def __init__(self, provider: str = "", timeout: int = 60, raw: str = ""):
        super().__init__(
            message=f"请求超时（{timeout}秒），请稍后重试",
            error_type="timeout", provider=provider,
            raw_response=raw, retriable=True,
        )


class LLMRateLimitError(LLMError):
    """速率限制 (429)"""
    def __init__(self, provider: str = "", raw: str = ""):
        super().__init__(
            message="请求过于频繁，请等待后重试",
            error_type="rate_limit", provider=provider,
            raw_response=raw, retriable=True,
        )


class LLMModelNotFoundError(LLMError):
    """模型不存在 (404)"""
    def __init__(self, provider: str = "", model: str = "", raw: str = ""):
        super().__init__(
            message=f"模型名称无效（{model}），请检查配置",
            error_type="model_not_found", provider=provider, model=model,
            raw_response=raw, retriable=False,
        )


class LLMNetworkError(LLMError):
    """网络错误"""
    def __init__(self, provider: str = "", raw: str = ""):
        super().__init__(
            message="网络连接失败，请检查网络后重试",
            error_type="network_error", provider=provider,
            raw_response=raw, retriable=True,
        )


class FileError(GEOAppException):
    """文件操作错误"""
    def __init__(self, message: str = "文件操作失败", details: Optional[dict[str, Any]] = None):
        super().__init__(code="FILE_ERROR", message=message, status_code=400, details=details)


class WorkflowError(GEOAppException):
    """工作流执行错误"""
    def __init__(self, message: str = "工作流执行失败", details: Optional[dict[str, Any]] = None):
        super().__init__(code="WORKFLOW_ERROR", message=message, status_code=500, details=details)


class PromptInjectionWarning(GEOAppException):
    """Prompt 注入检测警告（非阻断，HTTP 200 返回）"""
    def __init__(self, message: str = "检测到可疑的注入内容", details: Optional[dict[str, Any]] = None):
        super().__init__(code="PROMPT_INJECTION_WARNING", message=message, status_code=200, details=details)
