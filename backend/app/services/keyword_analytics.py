"""关键词质量分析 - 基于规则的意图分类和质量指标，不调用 LLM"""
from __future__ import annotations

import re
from typing import Any

# 行业预设词库
INDUSTRY_PRESETS: dict[str, dict[str, Any]] = {
    "SaaS": {
        "seed_keywords": [
            "企业SaaS推荐", "SaaS软件哪家好", "SaaS平台对比",
            "云端SaaS解决方案", "中小企业SaaS工具",
        ],
        "brand_words": ["最好用", "推荐", "对比", "评测", "排行"],
        "description": "SaaS/企业软件行业预设",
    },
    "电商": {
        "seed_keywords": [
            "电商平台推荐", "网购哪个平台好", "电商运营工具",
            "跨境电商平台", "私域电商解决方案",
        ],
        "brand_words": ["推荐", "哪个好", "靠谱", "性价比", "正品"],
        "description": "电商/零售行业预设",
    },
    "教育": {
        "seed_keywords": [
            "在线教育平台推荐", "学习软件哪个好", "教育机构排行",
            "AI教育工具", "职业培训平台",
        ],
        "brand_words": ["推荐", "哪个好", "效果好", "靠谱", "多少钱"],
        "description": "教育/培训行业预设",
    },
    "医疗健康": {
        "seed_keywords": [
            "在线问诊平台推荐", "健康管理APP", "医疗服务哪家好",
            "互联网医院排行", "AI医疗诊断",
        ],
        "brand_words": ["推荐", "哪个好", "正规", "专业", "安全"],
        "description": "医疗健康行业预设",
    },
    "金融": {
        "seed_keywords": [
            "理财平台推荐", "金融APP哪个好", "支付解决方案",
            "企业金融服务", "智能投顾平台",
        ],
        "brand_words": ["推荐", "安全", "正规", "靠谱", "收益高"],
        "description": "金融/理财行业预设",
    },
    "制造业": {
        "seed_keywords": [
            "智能制造解决方案", "工业软件推荐", "MES系统哪家好",
            "工厂数字化转型", "工业互联网平台",
        ],
        "brand_words": ["推荐", "哪家好", "方案", "供应商", "排名"],
        "description": "制造业/工业行业预设",
    },
}


def classify_intent(keyword: str) -> str:
    """分类关键词意图"""
    if re.search(r"哪家好|哪个好|推荐|最好|排行|对比|比较", keyword):
        return "对比评测类"
    if re.search(r"怎么|如何|方法|教程|步骤|攻略", keyword):
        return "教程方法类"
    if re.search(r"是什么|为什么|什么是|区别|原理", keyword):
        return "知识科普类"
    if re.search(r"多少钱|价格|费用|报价|划算", keyword):
        return "价格咨询类"
    if re.search(r"评价|好用吗|怎么样|靠谱吗|值得买", keyword):
        return "评价决策类"
    if re.search(r"下载|安装|注册|使用|官网", keyword):
        return "导航使用类"
    return "综合信息类"


def analyze_keywords_quality(keywords: list[str]) -> dict[str, Any]:
    """分析关键词列表的质量指标"""
    if not keywords:
        return {
            "total": 0,
            "intent_distribution": {},
            "brand_keyword_ratio": 0.0,
            "question_ratio": 0.0,
            "avg_length": 0,
            "long_tail_ratio": 0.0,
            "suggestions": ["没有关键词可分析"],
        }

    intent_counts: dict[str, int] = {}
    question_count = 0
    brand_term_count = 0
    long_tail_count = 0
    total_len = 0

    question_markers = ["吗", "呢", "什么", "怎么", "如何", "为什么", "哪", "几", "多少"]
    brand_terms = ["推荐", "哪家好", "哪个好", "最好", "靠谱", "对比", "排行", "品牌"]

    for kw in keywords:
        intent = classify_intent(kw)
        intent_counts[intent] = intent_counts.get(intent, 0) + 1
        total_len += len(kw)
        if any(m in kw for m in question_markers):
            question_count += 1
        if len(kw) >= 15:
            long_tail_count += 1
        if any(t in kw for t in brand_terms):
            brand_term_count += 1

    total = len(keywords)
    intent_distribution = {k: round(v / total * 100, 1) for k, v in intent_counts.items()}

    suggestions = []
    if intent_distribution.get("对比评测类", 0) < 20:
        suggestions.append("对比评测类关键词较少，建议增加「XX哪家好」「XX推荐」类高转化词")
    if intent_distribution.get("教程方法类", 0) < 15:
        suggestions.append("教程方法类关键词不足，用户搜索习惯偏向问答")
    if long_tail_count / total < 0.5:
        suggestions.append("长尾关键词比例偏低，建议增加15字以上的具体问题词")
    if not suggestions:
        suggestions.append("关键词分布健康，结构良好")

    return {
        "total": total,
        "intent_distribution": intent_distribution,
        "brand_keyword_ratio": round(brand_term_count / total * 100, 1),
        "question_ratio": round(question_count / total * 100, 1),
        "avg_length": round(total_len / total, 1),
        "long_tail_ratio": round(long_tail_count / total * 100, 1),
        "suggestions": suggestions,
    }


def get_industry_presets() -> list[dict[str, Any]]:
    return [
        {"key": k, "name": k, "description": v["description"], "seed_keywords": v["seed_keywords"]}
        for k, v in INDUSTRY_PRESETS.items()
    ]
