"""文本处理工具函数"""
import json
import re
from typing import Any, Optional


def extract_json(text: str) -> Optional[Any]:
    """从 LLM 输出中提取 JSON 对象/数组，支持容错解析"""
    if not text:
        return None

    # 尝试直接解析
    text = text.strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # 尝试提取 ```json ... ``` 代码块
    code_block = re.search(r"```(?:json)?\s*\n([\s\S]*?)\n```", text)
    if code_block:
        try:
            return json.loads(code_block.group(1))
        except json.JSONDecodeError:
            pass

    # 尝试提取最外层 {...} 或 [...]
    for pattern in (r"\{[^{}]*\}", r"\[[^\[\]]*\]"):
        match = re.search(pattern, text, re.DOTALL)
        if match:
            try:
                return json.loads(match.group(0))
            except json.JSONDecodeError:
                continue

    # 尝试贪婪匹配最大的 {}
    brace_start = text.find("{")
    brace_end = text.rfind("}")
    if brace_start != -1 and brace_end > brace_start:
        try:
            return json.loads(text[brace_start : brace_end + 1])
        except json.JSONDecodeError:
            pass

    bracket_start = text.find("[")
    bracket_end = text.rfind("]")
    if bracket_start != -1 and bracket_end > bracket_start:
        try:
            return json.loads(text[bracket_start : bracket_end + 1])
        except json.JSONDecodeError:
            pass

    return None


def mask_api_key(api_key: str, show_chars: int = 4) -> str:
    """掩码 API Key，只显示前后几位"""
    if not api_key or len(api_key) <= show_chars * 2:
        return "***" if api_key else ""
    return api_key[:show_chars] + "***" + api_key[-show_chars:]


def clean_competitors(competitors_text: str, brand: str = "") -> list[str]:
    """清理竞品列表文本，去重、去空、去除自身品牌"""
    seen: set[str] = set()
    result: list[str] = []
    brand_lower = brand.lower().strip()
    for line in competitors_text.split("\n"):
        c = line.strip()
        if not c:
            continue
        cl = c.lower()
        if brand_lower and cl == brand_lower:
            continue
        if cl in seen:
            continue
        seen.add(cl)
        result.append(c)
    return result
