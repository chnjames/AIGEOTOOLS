# -*- coding: utf-8 -*-
"""
Prompt Injection 检测工具

用于在用户输入（品牌名称、品牌优势、竞品名称等）注入 LLM 提示词之前，
检测潜在的提示词注入攻击。本模块提供非阻塞式警告检测和阻塞式长度校验。

检测模式：
- 忽略指令注入：试图让模型忽略之前/以上的指令
- 角色注入：试图重新设定模型角色（如扮演无限制黑客等）
- 系统提示泄露：试图获取系统提示词内容
- 指令重置：试图让模型忘记原有指令
- 新指令注入：试图注入新的指令覆盖原有行为
- 特殊标记注入：使用 LLM 特殊控制标记（如 [INST]、<s> 等）
- 隐藏内容指令：要求模型对用户隐瞒特定内容
- 重复注入模式：重复出现注入关键词的启发式检测
- DAN 越狱模式：Do Anything Now 类越狱提示
"""

import re
from typing import Optional


# ============================================================
# 各字段长度限制常量（用于阻塞式校验）
# ============================================================

BRAND_NAME_MAX: int = 100        # 品牌名称最大长度
BRAND_ADVANTAGES_MAX: int = 2000 # 品牌优势描述最大长度
COMPETITORS_MAX: int = 500       # 竞品名称最大长度
KEYWORD_MAX: int = 200           # 关键词最大长度
QUERY_MAX: int = 1000            # 查询文本最大长度


# ============================================================
# 注入检测正则规则
# 每条规则格式：(编译后的正则对象, 对应的警告描述)
# ============================================================

# 注意：所有正则均使用 re.IGNORECASE 实现大小写不敏感匹配

_INJECTION_PATTERNS: list[tuple[re.Pattern, str]] = [
    # --- 1. 忽略指令注入 ---
    # 检测：ignore above / ignore previous / 以上指令 / 忽略以上 / 忽略之前
    (
        re.compile(
            r"(?:ignore\s+(?:above|previous|all\s+previous|all\s+above|the\s+above|the\s+previous)"
            r"|忽略以上|忽略之前|以上指令|忽略上述|无视以上|无视之前|ignore\s+all\s+instructions?)",
            re.IGNORECASE,
        ),
        "忽略指令注入：检测到试图让模型忽略已有指令的内容",
    ),

    # --- 2. 角色注入 ---
    # 检测：you are now / 你现在是 / 你是一个 + 角色关键词（hacker / 无限制 / 没有道德 等）
    # 使用更精确的正则：角色设定短语后紧跟（0-30个字符内）出现角色关键词
    (
        re.compile(
            r"(?:"
            r"you\s+are\s+now|你现在是|你是一个|你是一?个|从现在起你是|从现在开始你是|扮演一?个|act\s+as\s+(?:a|an)|pretend\s+to\s+be"
            r")"
            r".{0,40}?"
            r"(?:"
            r"hacker|黑客|无限制|没有限制|不受限制|没有道德|无道德|不需要遵守"
            r"|without\s+(?:any\s+)?restrictions?|no\s+restrictions?|unrestricted"
            r"|unfiltered|no\s+filter|bypass|绕过(?:限制|审核|过滤)?"
            r"|illegal|违法的|anything\s+goes"
            r")",
            re.IGNORECASE | re.DOTALL,
        ),
        "角色注入：检测到试图将模型重置为恶意角色的内容",
    ),

    # --- 3. 系统提示词泄露 ---
    # 检测：system prompt / 系统提示词 / system: （后接指令试图提取提示词）
    (
        re.compile(
            r"(?:"
            r"system\s*prompt|系统提示词|系统指令|system\s*message"
            r"|system\s*:\s*|repeat\s+(?:the\s+)?(?:system|above|previous)\s+(?:prompt|message|instructions?)"
            r"|print\s+(?:your\s+)?(?:system\s+)?prompt|泄露(?:你的|系统)?(?:提示词|指令)"
            r"|输出(?:你的|系统)(?:提示词|指令)|告诉(?:我|我们)(?:你的|系统)(?:提示词|指令)"
            r")",
            re.IGNORECASE,
        ),
        "系统提示泄露：检测到试图获取或泄露系统提示词的内容",
    ),

    # --- 4. 指令重置 ---
    # 检测：forget your instructions / 忘记你的指令 / disregard
    (
        re.compile(
            r"(?:"
            r"forget\s+(?:your\s+)?(?:instructions?|rules|programming)"
            r"|忘记你的指令|忘记指令|忘掉指令|重置指令"
            r"|disregard(?:\s+(?:all|previous|above|your))?(?:\s+instructions?)?"
            r"|ignore\s+(?:your\s+)?(?:instructions?|rules|programming)"
            r")",
            re.IGNORECASE,
        ),
        "指令重置：检测到试图让模型忘记或重置原始指令的内容",
    ),

    # --- 5. 新指令注入 ---
    # 检测：new instructions / 新指令（试图覆盖原行为）
    (
        re.compile(
            r"(?:"
            r"new\s+instructions?|以下是新指令|这是新指令|新的指令"
            r"|from\s+now\s+on\s+you\s+will|从现在开始你(?:将|要|必须)"
            r")",
            re.IGNORECASE,
        ),
        "新指令注入：检测到试图注入新指令覆盖原有行为的内容",
    ),

    # --- 6. LLM 特殊标记注入 ---
    # 检测：[INST]、<s>、</s>、<<SYS>>、<|im_start|>、<|im_end|> 等
    (
        re.compile(
            r"(?:"
            r"\[INST\]|\[/INST\]|<s>|</s>|<\|im_start\|>|<\|im_end\|>"
            r"|<<SYS>>|<</SYS>>|<\|system\|>|<\|user\|>|<\|assistant\|>"
            r"|<\|endoftext\|>|<\|end\|>|\[\/?SYSTEM\]"
            r")",
            re.IGNORECASE,
        ),
        "特殊标记注入：检测到 LLM 特殊控制标记，可能用于劫持模型输出格式",
    ),

    # --- 7. 隐藏内容指令 ---
    # 检测：do not mention / 不要提及 / 不要告诉 / 保密 / 隐瞒
    (
        re.compile(
            r"(?:"
            r"do\s+not\s+mention|don'?t\s+mention|不要提及|不要提到|别说"
            r"|do\s+not\s+tell|don'?t\s+tell|不要告诉|不要说|不准说"
            r"|keep\s+(?:it\s+)?(?:secret|confidential)|保密|隐瞒|不要让.*知道"
            r"|never\s+mention|hide\s+(?:the\s+)?fact|conceal"
            r")",
            re.IGNORECASE,
        ),
        "隐藏内容指令：检测到要求模型向用户隐瞒内容的指令",
    ),

    # --- 8. DAN（Do Anything Now）越狱模式 ---
    (
        re.compile(
            r"(?:"
            r"\bDAN\b|DAN模式|DAN\s*模式|do\s+anything\s+now"
            r"|jailbreak|越狱(?:模式)?|越獄"
            r"|developer\s+mode|开发者模式|dev\s+mode"
            r"|unlimited\s+mode|无限制模式|anti[-_]?filter"
            r")",
            re.IGNORECASE,
        ),
        "DAN越狱模式：检测到 Do Anything Now (DAN) 或越狱类提示",
    ),
]


# 用于重复注入检测的关键词列表
_REPEAT_KEYWORDS: list[str] = ["忽略", "forget", "ignore", "disregard", "无视", "忘记"]
_REPEAT_THRESHOLD: int = 3  # 出现次数阈值


def detect_injection(text: str) -> list[str]:
    """
    检测文本中是否存在潜在的 Prompt Injection 攻击模式。

    对输入文本逐条匹配已知注入特征正则，并对重复注入关键词进行启发式检测。
    返回所有匹配到的警告描述列表；若文本干净则返回空列表。

    Args:
        text: 待检测的用户输入文本。

    Returns:
        list[str]: 检测到的注入模式描述列表，无注入时返回空列表。
    """
    warnings: list[str] = []

    if not text or not isinstance(text, str):
        return warnings

    lower_text = text.lower()

    # 逐条匹配正则规则
    for pattern, description in _INJECTION_PATTERNS:
        if pattern.search(text):
            warnings.append(description)

    # --- 重复注入关键词启发式检测 ---
    # 统计所有注入关键词在文本中出现的总次数，超过阈值则发出警告
    total_occurrences = 0
    for keyword in _REPEAT_KEYWORDS:
        # 中文关键词直接计数；英文单词使用单词边界避免误匹配
        if re.match(r"^[a-zA-Z]+$", keyword):
            total_occurrences += len(
                re.findall(r"\b" + re.escape(keyword) + r"\b", lower_text)
            )
        else:
            total_occurrences += text.count(keyword) + lower_text.count(keyword.lower())

    # 去重：如果已经被正则规则捕获了相同类别的警告，避免重复添加
    already_has_ignore_warning = any("忽略" in w or "重置" in w for w in warnings)
    if total_occurrences >= _REPEAT_THRESHOLD and not already_has_ignore_warning:
        warnings.append(
            f"重复注入模式：注入相关关键词（忽略/forget/ignore等）累计出现 "
            f"{total_occurrences} 次，疑似重复注入攻击"
        )

    return warnings


def check_input_safety(text: str, field_name: str = "输入") -> dict:
    """
    对用户输入进行安全性检查，返回包含安全状态和警告信息的字典。

    本检查为非阻塞式：即使检测到注入警告，safe 字段仍为 True，
    警告信息通过 warnings 字段返回，调用方可以记录日志后继续处理。
    长度校验不在本函数中进行（应使用 validate_input_length 单独处理）。

    Args:
        text: 待检查的用户输入文本。
        field_name: 字段名称，用于在警告信息中标注来源，默认为"输入"。

    Returns:
        dict: 格式如下：
        {
            "safe": bool,          # 非阻塞模式下始终为 True（警告不阻断处理）
            "warnings": list[str], # 检测到的注入警告列表
            "field_name": str,     # 传入的字段名
            "length": int          # 输入文本的字符长度
        }
    """
    if text is None:
        text = ""

    length = len(text)
    warnings = detect_injection(text)

    # 在每条警告前加上字段名前缀以便定位来源
    prefixed_warnings = [f"[{field_name}] {w}" for w in warnings]

    return {
        "safe": True,  # 非阻塞：警告不阻止处理流程
        "warnings": prefixed_warnings,
        "field_name": field_name,
        "length": length,
    }


def validate_input_length(
    text: str, field_name: str, max_length: int
) -> Optional[str]:
    """
    校验输入文本长度是否超过最大限制。

    本函数为阻塞式校验：超过长度限制时返回错误信息字符串，
    调用方应当阻止该输入继续处理。

    Args:
        text: 待校验的输入文本。
        field_name: 字段名称（中文），用于拼接错误提示。
        max_length: 允许的最大字符数。

    Returns:
        Optional[str]: 若超过长度限制返回错误提示字符串，否则返回 None。
    """
    if text is None:
        return None

    length = len(text)
    if length > max_length:
        return (
            f"{field_name}长度超过限制：当前 {length} 个字符，"
            f"最多允许 {max_length} 个字符"
        )
    return None
