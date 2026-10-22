"""Token 估算工具"""


def estimate_tokens(text: str) -> int:
    """
    估算文本的 token 数量。
    中文约 1.5 字符 = 1 token，英文约 4 字符 = 1 token。
    """
    if not text:
        return 0
    chinese_chars = sum(1 for char in text if "\u4e00" <= char <= "\u9fff")
    other_chars = len(text) - chinese_chars
    estimated = int(chinese_chars / 1.5 + other_chars / 4)
    return max(estimated, len(text) // 4)
