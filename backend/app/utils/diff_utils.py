"""简单的文本 Diff 工具 - 基于行级 diff，生成 HTML 高亮输出"""
from __future__ import annotations

import difflib
from typing import Any


def compute_diff(text_a: str, text_b: str, context_lines: int = 2) -> dict[str, Any]:
    """
    计算两个文本的行级 diff，返回统计信息和 HTML。
    返回: {"diff_html": str, "additions": int, "deletions": int}
    """
    lines_a = text_a.splitlines(keepends=True)
    lines_b = text_b.splitlines(keepends=True)

    diff = list(difflib.unified_diff(
        lines_a, lines_b,
        fromfile="版本A", tofile="版本B",
        n=context_lines, lineterm=""
    ))

    additions = 0
    deletions = 0
    html_parts: list[str] = ['<div class="diff-view" style="font-family:monospace;font-size:13px;line-height:1.6;">']

    for line in diff:
        if line.startswith("+++") or line.startswith("---") or line.startswith("@@"):
            html_parts.append(f'<div style="color:#888;background:#f8f8f8;padding:2px 8px;">{_escape_html(line)}</div>')
        elif line.startswith("+"):
            additions += 1
            html_parts.append(f'<div style="background:#e6ffed;color:#22863a;padding:2px 8px;">{_escape_html(line)}</div>')
        elif line.startswith("-"):
            deletions += 1
            html_parts.append(f'<div style="background:#ffeef0;color:#cb2431;padding:2px 8px;">{_escape_html(line)}</div>')
        else:
            html_parts.append(f'<div style="padding:2px 8px;color:#555;">{_escape_html(line)}</div>')

    html_parts.append("</div>")

    return {
        "diff_html": "".join(html_parts),
        "additions": additions,
        "deletions": deletions,
    }


def _escape_html(text: str) -> str:
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )
