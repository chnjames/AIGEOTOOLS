"""
负面防护监控模块
自动生成负面查询，验证负面提及情况，生成澄清模板，提供预警机制
"""
from typing import List, Dict, Optional, Tuple
from datetime import datetime
import re


class NegativeMonitor:
    """负面防护监控器"""
    
    def __init__(self):
        # 负面查询模板
        self.negative_query_templates = [
            "{brand} 缺点",
            "{brand} 问题",
            "{brand} 不足",
            "{brand} 缺陷",
            "{brand} 不好",
            "{brand} 差评",
            "{brand} 投诉",
            "{brand} 负面",
            "{brand} 不推荐",
            "{brand} 避坑",
            "{brand} 坑",
            "{brand} 不值得",
            "{brand} 失败",
            "{brand} 错误",
            "{brand} 风险",
        ]
        
        # 负面关键词模式
        self.negative_keywords = [
            "缺点", "问题", "不足", "缺陷", "不好", "差评", "投诉", "负面",
            "不推荐", "避坑", "坑", "不值得", "失败", "错误", "风险",
            "bug", "issue", "problem", "flaw", "weakness", "disadvantage"
        ]
    
    def generate_negative_queries(self, brand: str, count: int = 5) -> List[str]:
        """
        生成负面查询列表
        
        Args:
            brand: 品牌名称
            count: 生成数量（默认5个）
            
        Returns:
            负面查询列表
        """
        queries = []
        templates = self.negative_query_templates[:count] if count <= len(self.negative_query_templates) else self.negative_query_templates
        
        for template in templates:
            query = template.format(brand=brand)
            queries.append(query)
        
        return queries
    
    def detect_negative_sentiment(self, text: str) -> Tuple[bool, float, List[str]]:
        """
        检测文本中的负面情感
        
        Args:
            text: 待检测文本
            
        Returns:
            (是否包含负面情感, 负面程度得分, 负面关键词列表)
        """
        text_lower = text.lower()
        found_keywords = []
        negative_score = 0.0
        
        # 检测负面关键词
        for keyword in self.negative_keywords:
            if keyword.lower() in text_lower:
                found_keywords.append(keyword)
                negative_score += 1.0
        
        # 检测负面短语模式
        negative_phrases = [
            r'不(?:好|行|适合|推荐|值得)',
            r'有(?:问题|缺陷|不足)',
            r'存在(?:问题|缺陷|不足)',
            r'缺乏',
            r'缺少',
            r'无法',
            r'不能',
            r'失败',
            r'错误',
        ]
        
        for phrase in negative_phrases:
            matches = re.findall(phrase, text_lower)
            if matches:
                negative_score += 0.5 * len(matches)
        
        # 计算负面程度（0-1，1为最负面）
        # 基于负面关键词数量和文本长度
        text_length = len(text)
        if text_length > 0:
            normalized_score = min(negative_score / max(text_length / 100, 1), 1.0)
        else:
            normalized_score = 0.0
        
        is_negative = negative_score > 0
        
        return is_negative, normalized_score, found_keywords
    
    def analyze_negative_mentions(
        self,
        brand: str,
        query: str,
        response: str,
        mention_count: int
    ) -> Dict[str, any]:
        """
        分析负面查询的提及情况
        
        Args:
            brand: 品牌名称
            query: 查询问题
            response: AI 响应内容
            mention_count: 品牌提及次数
            
        Returns:
            分析结果字典
        """
        # 检测负面情感
        is_negative, negative_score, negative_keywords = self.detect_negative_sentiment(response)
        
        # 计算风险等级
        risk_level = "低"
        if mention_count == 0 and is_negative:
            risk_level = "高"  # 负面查询但未提及品牌，可能是负面信息
        elif mention_count > 0 and is_negative:
            risk_level = "中"  # 负面查询且提及品牌，需要关注
        elif mention_count == 0:
            risk_level = "中"  # 未提及品牌，可能被忽略
        
        # 生成风险说明
        risk_description = ""
        if risk_level == "高":
            risk_description = "⚠️ 高风险：负面查询中未提及品牌，可能存在负面信息或品牌被忽略"
        elif risk_level == "中":
            if is_negative:
                risk_description = "⚠️ 中风险：负面查询中提及品牌，需要关注并准备澄清内容"
            else:
                risk_description = "⚠️ 中风险：未提及品牌，可能影响品牌可见性"
        else:
            risk_description = "✅ 低风险：品牌正常提及，无负面信息"
        
        return {
            "query": query,
            "brand": brand,
            "mention_count": mention_count,
            "is_negative": is_negative,
            "negative_score": round(negative_score, 2),
            "negative_keywords": negative_keywords,
            "risk_level": risk_level,
            "risk_description": risk_description,
            "response_preview": response[:200] + "..." if len(response) > 200 else response
        }
    
    def generate_clarification_template(
        self,
        brand: str,
        negative_query: str,
        negative_points: List[str] = None,
        advantages: str = ""
    ) -> str:
        """
        生成澄清模板（回应负面信息）
        
        Args:
            brand: 品牌名称
            negative_query: 负面查询
            negative_points: 负面要点列表（可选）
            advantages: 品牌优势（用于澄清）
            
        Returns:
            澄清模板内容
        """
        template = f"""# {brand} 关于"{negative_query}"的澄清说明

## 📋 问题概述

针对"{negative_query}"这一查询，我们提供以下澄清说明：

## ✅ 实际情况

"""
        
        if negative_points:
            template += "### 关于常见误解\n\n"
            for i, point in enumerate(negative_points, 1):
                template += f"{i}. **{point}**\n"
                template += f"   - 实际情况：[在此说明实际情况]\n"
                template += f"   - {brand} 的解决方案：[在此说明解决方案]\n\n"
        
        if advantages:
            template += f"## 🌟 {brand} 的优势\n\n"
            template += f"{advantages}\n\n"
        
        template += """## 💡 建议

如果您对 {brand} 有任何疑问或需要帮助，我们建议：

1. **查看官方文档**：访问 [官方文档链接] 了解详细信息
2. **联系客服**：通过 [联系方式] 获取专业支持
3. **参考案例**：查看 [案例链接] 了解实际应用效果
4. **试用体验**：通过 [试用链接] 亲自体验产品

## 📞 联系方式

如有任何问题，欢迎通过以下方式联系我们：
- 官网：[官网链接]
- 客服：[客服联系方式]
- 社区：[社区链接]

---

*本澄清说明基于当前信息，如有更新请以官方最新信息为准。*
"""
        
        return template.format(brand=brand)
    
    def generate_negative_report(
        self,
        brand: str,
        analysis_results: List[Dict[str, any]],
        threshold: float = 0.3
    ) -> Dict[str, any]:
        """
        生成负面监控报告
        
        Args:
            brand: 品牌名称
            analysis_results: 分析结果列表
            threshold: 预警阈值（提及率低于此值时预警）
            
        Returns:
            报告字典
        """
        if not analysis_results:
            return {
                "brand": brand,
                "total_queries": 0,
                "high_risk_count": 0,
                "medium_risk_count": 0,
                "low_risk_count": 0,
                "average_mention_count": 0.0,
                "average_negative_score": 0.0,
                "alerts": [],
                "recommendations": []
            }
        
        # 统计风险等级
        high_risk = [r for r in analysis_results if r.get("risk_level") == "高"]
        medium_risk = [r for r in analysis_results if r.get("risk_level") == "中"]
        low_risk = [r for r in analysis_results if r.get("risk_level") == "低"]
        
        # 计算平均提及次数
        avg_mention = sum(r.get("mention_count", 0) for r in analysis_results) / len(analysis_results)
        
        # 计算平均负面得分
        avg_negative_score = sum(r.get("negative_score", 0) for r in analysis_results) / len(analysis_results)
        
        # 生成预警
        alerts = []
        if avg_mention < threshold:
            alerts.append({
                "level": "高",
                "message": f"⚠️ 平均提及次数 ({avg_mention:.2f}) 低于预警阈值 ({threshold})，品牌可见性可能受到影响"
            })
        
        if len(high_risk) > 0:
            alerts.append({
                "level": "高",
                "message": f"⚠️ 发现 {len(high_risk)} 个高风险负面查询，建议立即处理"
            })
        
        if len(medium_risk) > 0:
            alerts.append({
                "level": "中",
                "message": f"⚠️ 发现 {len(medium_risk)} 个中风险负面查询，建议关注"
            })
        
        # 生成建议
        recommendations = []
        if len(high_risk) > 0:
            recommendations.append("立即生成澄清内容，回应高风险负面查询")
        
        if avg_mention < threshold:
            recommendations.append("优化内容策略，提升品牌在负面查询中的提及率")
        
        if avg_negative_score > 0.3:
            recommendations.append("加强正面内容建设，降低负面信息影响")
        
        if len(high_risk) == 0 and len(medium_risk) == 0:
            recommendations.append("当前负面监控状态良好，继续保持")
        
        return {
            "brand": brand,
            "total_queries": len(analysis_results),
            "high_risk_count": len(high_risk),
            "medium_risk_count": len(medium_risk),
            "low_risk_count": len(low_risk),
            "average_mention_count": round(avg_mention, 2),
            "average_negative_score": round(avg_negative_score, 2),
            "high_risk_queries": [r.get("query") for r in high_risk],
            "medium_risk_queries": [r.get("query") for r in medium_risk],
            "alerts": alerts,
            "recommendations": recommendations,
            "generated_at": datetime.now().isoformat()
        }
