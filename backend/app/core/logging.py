"""结构化日志配置 - 支持 JSON 格式和敏感信息过滤"""
import json
import logging
import os
import re
import sys


# 需要脱敏的键名模式
_SENSITIVE_KEYS = re.compile(
    r"(api[_-]?key|api[_-]?secret|access[_-]?token|refresh[_-]?token|"
    r"password|passwd|pwd|secret|authorization|bearer|credential)",
    re.IGNORECASE,
)

# 脱敏后的显示值
_MASKED_VALUE = "***REDACTED***"


class SensitiveDataFilter(logging.Filter):
    """过滤日志中的敏感信息（api_key、token、password 等）"""

    def filter(self, record: logging.LogRecord) -> bool:
        msg = record.getMessage()
        # 对已格式化的消息做脱敏（key=value / key: value 模式）
        record.msg = _redact_string(msg)
        # 关键：清除 args，避免 getMessage() 再次执行 msg % args 导致格式化错误
        # （此时 record.msg 已是最终字符串，不再需要 args 参与格式化）
        record.args = None
        return True


def _redact_string(s: str) -> str:
    """对字符串中的敏感键值对做脱敏"""
    # 匹配 key=value 或 key: value 模式
    def _replace(match):
        key = match.group(1)
        sep = match.group(2)
        return f"{key}{sep}{_MASKED_VALUE}"

    pattern = re.compile(
        r'(["\']?(?:api[_-]?key|api[_-]?secret|access[_-]?token|refresh[_-]?token|'
        r'password|passwd|pwd|secret|authorization|bearer|credential)["\']?\s*[:=]\s*)'
        r'["\']?[^"\',\}\]\s]+["\']?',
        re.IGNORECASE,
    )
    return pattern.sub(lambda m: m.group(1) + _MASKED_VALUE, s)


class JsonFormatter(logging.Formatter):
    """JSON 结构化日志格式"""

    def format(self, record: logging.LogRecord) -> str:
        log_entry = {
            "timestamp": self.formatTime(record, "%Y-%m-%dT%H:%M:%S.%fZ"),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        if record.exc_info and record.exc_info[1]:
            log_entry["exception"] = self.formatException(record.exc_info)
        if hasattr(record, "request_id"):
            log_entry["request_id"] = record.request_id
        return json.dumps(log_entry, ensure_ascii=False)


class TextFormatter(logging.Formatter):
    """可读的文本日志格式"""

    def format(self, record: logging.LogRecord) -> str:
        timestamp = self.formatTime(record, "%Y-%m-%d %H:%M:%S")
        level = record.levelname.ljust(7)
        module = record.name.ljust(25)
        msg = record.getMessage()
        return f"{timestamp} | {level} | {module} | {msg}"


def setup_logging(level: int | None = None) -> None:
    """配置全局日志"""
    if level is None:
        level_name = os.environ.get("LOG_LEVEL", "INFO").upper()
        level = getattr(logging, level_name, logging.INFO)

    use_json = os.environ.get("LOG_JSON", "false").lower() in ("true", "1", "yes")

    handler = logging.StreamHandler(sys.stdout)
    if use_json:
        handler.setFormatter(JsonFormatter())
    else:
        handler.setFormatter(TextFormatter())

    # 添加敏感信息过滤器
    handler.addFilter(SensitiveDataFilter())

    root_logger = logging.getLogger()
    root_logger.setLevel(level)
    root_logger.handlers.clear()
    root_logger.addHandler(handler)

    # 降低第三方库日志噪音
    for noisy in ("httpx", "httpcore", "langchain", "alembic", "chromadb"):
        logging.getLogger(noisy).setLevel(logging.WARNING)


def get_logger(name: str) -> logging.Logger:
    """获取模块级 logger"""
    return logging.getLogger(name)
