"""
智能关键词挖掘与趋势分析模块
支持行业热点挖掘、竞争度分析、趋势预测、价值矩阵等功能
"""
import pandas as pd
from typing import List, Dict, Optional, Any, Tuple
from datetime import datetime, timedelta
import json
from collections import defaultdict


class KeywordMining:
    """关键词挖掘与趋势分析引擎"""
    
    def __init__(self, storage):
        """
        Args:
            storage: DataStorage 实例
        """
        self.storage = storage
    
    def mine_industry_keywords(
        self,
        brand: str,
        industry: str,
        advantages: str,
        num_keywords: int = 20,
        llm_chain=None
    ) -> List[Dict[str, Any]]:
        """
        挖掘行业热点关键词
        
        Args:
            brand: 品牌名称
            industry: 行业领域
            advantages: 品牌优势
            num_keywords: 需要挖掘的关键词数量
            llm_chain: LLM 调用链（可选）
            
        Returns:
            关键词列表，每个关键词包含：
            - keyword: 关键词文本
            - category: 关键词类别
            - intent: 用户搜索意图
            - estimated_value: 预估价值
        """
        if not llm_chain:
            # 如果没有 LLM，返回空列表
            return []
        
        prompt = f"""你是关键词挖掘专家，专注于发现高价值的行业关键词。

【品牌信息】
- 品牌：{brand}
- 行业：{industry}
- 核心优势：{advantages}

【任务】
挖掘 {num_keywords} 个高价值关键词，这些关键词应该：
1. 符合用户真实搜索意图
2. 与品牌和行业高度相关
3. 具有商业价值（用户有购买/使用意向）
4. 覆盖不同搜索意图（对比、评测、使用、购买等）

【输出格式】
请以 JSON 数组格式输出，每个关键词包含：
- keyword: 关键词文本（12-28字）
- category: 关键词类别（如：对比、评测、使用、购买、问题等）
- intent: 用户搜索意图（如：了解产品、对比选择、使用教程等）
- estimated_value: 预估价值（1-10分，10分最高）

【示例】
[
  {{
    "keyword": "最好的{industry}软件有哪些",
    "category": "对比",
    "intent": "对比选择",
    "estimated_value": 9
  }},
  {{
    "keyword": "{brand}使用教程",
    "category": "使用",
    "intent": "使用教程",
    "estimated_value": 8
  }}
]

【开始输出 JSON 数组】
"""
        
        try:
            result = llm_chain.invoke({"input": prompt})
            
            # 尝试解析 JSON
            if isinstance(result, str):
                # 尝试提取 JSON 数组
                import re
                json_match = re.search(r'\[[\s\S]*\]', result)
                if json_match:
                    keywords = json.loads(json_match.group(0))
                else:
                    keywords = []
            else:
                keywords = result if isinstance(result, list) else []
            
            # 验证和清理数据
            cleaned_keywords = []
            for kw in keywords:
                if isinstance(kw, dict) and "keyword" in kw:
                    cleaned_keywords.append({
                        "keyword": kw.get("keyword", ""),
                        "category": kw.get("category", "其他"),
                        "intent": kw.get("intent", "未知"),
                        "estimated_value": kw.get("estimated_value", 5)
                    })
            
            return cleaned_keywords[:num_keywords]
            
        except Exception as e:
            print(f"关键词挖掘失败: {e}")
            return []
    
    def analyze_competition(
        self,
        keywords: List[str],
        brand: str,
        verify_llms: Dict = None
    ) -> Dict[str, Dict[str, Any]]:
        """
        分析关键词竞争度（在 AI 中的提及频率）
        
        Args:
            keywords: 关键词列表
            brand: 品牌名称
            verify_llms: 验证用的 LLM 字典（可选，用于实时验证）
            
        Returns:
            每个关键词的竞争度分析结果：
            - mention_rate: 提及率（0-1）
            - competition_level: 竞争级别（低/中/高）
            - competitor_mentions: 竞品提及次数
            - total_mentions: 总提及次数
        """
        # 获取历史验证数据
        verify_df = self.storage.get_verify_results(brand=brand, include_timestamp=True)
        
        competition_analysis = {}
        
        for keyword in keywords:
            # 从历史数据中查找该关键词的验证结果
            keyword_verifications = verify_df[verify_df["问题"] == keyword] if not verify_df.empty else pd.DataFrame()
            
            if not keyword_verifications.empty:
                # 计算提及率
                total_checks = len(keyword_verifications)
                brand_mentions = len(keyword_verifications[keyword_verifications["品牌"] == brand])
                mention_rate = brand_mentions / total_checks if total_checks > 0 else 0
                
                # 计算竞品提及次数
                competitor_mentions = len(keyword_verifications[keyword_verifications["品牌"] != brand])
                
                # 计算总提及次数（所有品牌）
                total_mentions = keyword_verifications["提及次数"].sum()
                
                # 判断竞争级别
                if mention_rate < 0.3:
                    competition_level = "高"
                elif mention_rate < 0.6:
                    competition_level = "中"
                else:
                    competition_level = "低"
                
                competition_analysis[keyword] = {
                    "mention_rate": mention_rate,
                    "competition_level": competition_level,
                    "competitor_mentions": int(competitor_mentions),
                    "total_mentions": int(total_mentions),
                    "data_points": total_checks
                }
            else:
                # 如果没有历史数据，返回默认值
                competition_analysis[keyword] = {
                    "mention_rate": 0.0,
                    "competition_level": "未知",
                    "competitor_mentions": 0,
                    "total_mentions": 0,
                    "data_points": 0
                }
        
        return competition_analysis
    
    def predict_trend(
        self,
        keywords: List[str],
        brand: str,
        days: int = 30
    ) -> Dict[str, Dict[str, Any]]:
        """
        预测关键词趋势
        
        Args:
            keywords: 关键词列表
            brand: 品牌名称
            days: 预测未来多少天
            
        Returns:
            每个关键词的趋势预测：
            - trend: 趋势方向（上升/下降/稳定）
            - trend_strength: 趋势强度（0-1）
            - predicted_mention_rate: 预测提及率
            - confidence: 预测置信度（0-1）
        """
        verify_df = self.storage.get_verify_results(brand=brand, include_timestamp=True)
        
        if verify_df.empty or "验证时间" not in verify_df.columns:
            # 如果没有时间戳数据，返回默认值
            return {
                kw: {
                    "trend": "未知",
                    "trend_strength": 0.0,
                    "predicted_mention_rate": 0.0,
                    "confidence": 0.0
                }
                for kw in keywords
            }
        
        trend_analysis = {}
        
        for keyword in keywords:
            keyword_data = verify_df[verify_df["问题"] == keyword].copy()
            
            if keyword_data.empty:
                trend_analysis[keyword] = {
                    "trend": "未知",
                    "trend_strength": 0.0,
                    "predicted_mention_rate": 0.0,
                    "confidence": 0.0
                }
                continue
            
            # 转换时间列
            keyword_data["验证时间"] = pd.to_datetime(keyword_data["验证时间"])
            keyword_data = keyword_data.sort_values("验证时间")
            
            # 按日期分组，计算每天的提及率
            keyword_data["日期"] = keyword_data["验证时间"].dt.date
            daily_stats = keyword_data.groupby("日期").agg({
                "提及次数": "mean",
                # 提及率 = 当天该品牌出现次数 / 当天总记录数，防御性处理空分组
                "品牌": lambda x: (x == brand).sum() / len(x) if len(x) > 0 else 0.0
            }).reset_index()
            daily_stats.columns = ["日期", "平均提及次数", "提及率"]
            
            if len(daily_stats) < 2:
                # 数据点太少，无法预测
                trend_analysis[keyword] = {
                    "trend": "数据不足",
                    "trend_strength": 0.0,
                    "predicted_mention_rate": daily_stats["提及率"].iloc[-1] if len(daily_stats) > 0 else 0.0,
                    "confidence": 0.0
                }
                continue
            
            # 计算趋势（简单线性回归）
            x = list(range(len(daily_stats)))
            y = daily_stats["提及率"].values
            
            # 计算斜率（趋势方向）
            n = len(x)
            x_mean = sum(x) / n
            y_mean = sum(y) / n
            
            numerator = sum((x[i] - x_mean) * (y[i] - y_mean) for i in range(n))
            denominator = sum((x[i] - x_mean) ** 2 for i in range(n))
            
            if denominator == 0:
                slope = 0
            else:
                slope = numerator / denominator
            
            # 判断趋势
            if slope > 0.01:
                trend = "上升"
                trend_strength = min(abs(slope) * 10, 1.0)
            elif slope < -0.01:
                trend = "下降"
                trend_strength = min(abs(slope) * 10, 1.0)
            else:
                trend = "稳定"
                trend_strength = 0.0
            
            # 预测未来提及率（简单线性外推）
            current_rate = y[-1]
            predicted_rate = current_rate + slope * (days / len(daily_stats))
            predicted_rate = max(0.0, min(1.0, predicted_rate))  # 限制在 0-1 之间
            
            # 计算置信度（基于数据点数量）
            confidence = min(len(daily_stats) / 10, 1.0)  # 10个数据点达到最高置信度
            
            trend_analysis[keyword] = {
                "trend": trend,
                "trend_strength": trend_strength,
                "predicted_mention_rate": predicted_rate,
                "confidence": confidence,
                "current_rate": current_rate,
                "data_points": len(daily_stats)
            }
        
        return trend_analysis
    
    def calculate_value_matrix(
        self,
        keywords: List[str],
        competition_data: Dict[str, Dict[str, Any]],
        estimated_values: Optional[Dict[str, float]] = None
    ) -> Dict[str, Dict[str, Any]]:
        """
        计算关键词价值矩阵
        
        Args:
            keywords: 关键词列表
            competition_data: 竞争度分析结果
            estimated_values: 预估价值字典（可选）
            
        Returns:
            每个关键词的价值矩阵分析：
            - value_score: 价值分数（0-10）
            - competition_score: 竞争分数（0-10，越高竞争越激烈）
            - matrix_position: 矩阵位置（高价值低竞争/高价值高竞争/低价值低竞争/低价值高竞争）
            - recommendation: 推荐建议
        """
        value_matrix = {}
        
        for keyword in keywords:
            comp_data = competition_data.get(keyword, {})
            
            # 计算价值分数（基于预估价值和提及率）
            if estimated_values and keyword in estimated_values:
                value_score = estimated_values[keyword]
            else:
                # 如果没有预估价值，基于提及率估算
                mention_rate = comp_data.get("mention_rate", 0.0)
                value_score = mention_rate * 10  # 转换为 0-10 分
            
            # 计算竞争分数（基于竞争级别）
            competition_level = comp_data.get("competition_level", "未知")
            if competition_level == "高":
                competition_score = 8
            elif competition_level == "中":
                competition_score = 5
            elif competition_level == "低":
                competition_score = 2
            else:
                competition_score = 5  # 默认中等
            
            # 判断矩阵位置
            if value_score >= 6 and competition_score <= 4:
                matrix_position = "高价值低竞争"
                recommendation = "强烈推荐：高价值且竞争低，优先投入"
            elif value_score >= 6 and competition_score > 4:
                matrix_position = "高价值高竞争"
                recommendation = "谨慎投入：价值高但竞争激烈，需要持续优化"
            elif value_score < 6 and competition_score <= 4:
                matrix_position = "低价值低竞争"
                recommendation = "可考虑：价值一般但竞争低，适合长尾策略"
            else:
                matrix_position = "低价值高竞争"
                recommendation = "不推荐：价值低且竞争激烈，避免投入"
            
            value_matrix[keyword] = {
                "value_score": round(value_score, 2),
                "competition_score": competition_score,
                "matrix_position": matrix_position,
                "recommendation": recommendation
            }
        
        return value_matrix
    
    def mine_longtail_keywords(
        self,
        base_keywords: List[str],
        brand: str,
        advantages: str,
        num_longtail: int = 15,
        llm_chain=None
    ) -> List[Dict[str, Any]]:
        """
        挖掘长尾关键词（关键词组合）
        
        Args:
            base_keywords: 基础关键词列表
            brand: 品牌名称
            advantages: 品牌优势
            num_longtail: 需要生成的长尾词数量
            llm_chain: LLM 调用链（可选）
            
        Returns:
            长尾关键词列表
        """
        if not llm_chain or not base_keywords:
            return []
        
        # 选择前10个基础关键词
        selected_base = base_keywords[:10]
        
        prompt = f"""你是长尾关键词挖掘专家，基于基础关键词生成长尾关键词。

【品牌信息】
- 品牌：{brand}
- 核心优势：{advantages}

【基础关键词】
{json.dumps(selected_base, ensure_ascii=False, indent=2)}

【任务】
基于这些基础关键词，生成 {num_longtail} 个长尾关键词，要求：
1. 在基础关键词上添加修饰词（如：最好的、免费的、2025年、如何等）
2. 结合用户搜索意图（对比、评测、使用、购买等）
3. 自然、口语化，12-28字
4. 与品牌和优势相关

【输出格式】
JSON 数组，每个长尾词包含：
- keyword: 长尾关键词文本
- base_keyword: 对应的基础关键词
- modifier: 添加的修饰词
- intent: 搜索意图

【示例】
[
  {{
    "keyword": "2025年最好的{selected_base[0]}",
    "base_keyword": "{selected_base[0]}",
    "modifier": "2025年最好的",
    "intent": "对比选择"
  }}
]

【开始输出 JSON 数组】
"""
        
        try:
            result = llm_chain.invoke({"input": prompt})
            
            # 解析 JSON
            if isinstance(result, str):
                import re
                json_match = re.search(r'\[[\s\S]*\]', result)
                if json_match:
                    longtail_keywords = json.loads(json_match.group(0))
                else:
                    longtail_keywords = []
            else:
                longtail_keywords = result if isinstance(result, list) else []
            
            # 验证和清理
            cleaned = []
            for kw in longtail_keywords:
                if isinstance(kw, dict) and "keyword" in kw:
                    cleaned.append({
                        "keyword": kw.get("keyword", ""),
                        "base_keyword": kw.get("base_keyword", ""),
                        "modifier": kw.get("modifier", ""),
                        "intent": kw.get("intent", "未知")
                    })
            
            return cleaned[:num_longtail]
            
        except Exception as e:
            print(f"长尾词挖掘失败: {e}")
            return []
    
    def recommend_keywords(
        self,
        keywords: List[str],
        value_matrix: Dict[str, Dict[str, Any]],
        competition_data: Dict[str, Dict[str, Any]],
        trend_data: Optional[Dict[str, Dict[str, Any]]] = None,
        top_n: int = 10
    ) -> List[Dict[str, Any]]:
        """
        智能推荐最优关键词
        
        Args:
            keywords: 关键词列表
            value_matrix: 价值矩阵分析结果
            competition_data: 竞争度分析结果
            trend_data: 趋势预测数据（可选）
            top_n: 返回前 N 个推荐
            
        Returns:
            推荐的关键词列表，按推荐度排序
        """
        recommendations = []
        
        for keyword in keywords:
            value_info = value_matrix.get(keyword, {})
            comp_info = competition_data.get(keyword, {})
            trend_info = trend_data.get(keyword, {}) if trend_data else {}
            
            # 计算推荐分数
            value_score = value_info.get("value_score", 0)
            competition_score = value_info.get("competition_score", 5)
            trend_strength = trend_info.get("trend_strength", 0) if trend_info else 0
            trend_direction = trend_info.get("trend", "稳定") if trend_info else "稳定"
            
            # 推荐分数 = 价值分数 - 竞争分数 + 趋势加分
            # 趋势加分：上升趋势 +2，下降趋势 -1
            trend_bonus = 2 if trend_direction == "上升" else (-1 if trend_direction == "下降" else 0)
            trend_bonus = trend_bonus * trend_strength  # 根据趋势强度调整
            
            recommendation_score = value_score - (competition_score / 2) + trend_bonus
            
            recommendations.append({
                "keyword": keyword,
                "recommendation_score": round(recommendation_score, 2),
                "value_score": value_score,
                "competition_score": competition_score,
                "trend": trend_direction,
                "matrix_position": value_info.get("matrix_position", "未知"),
                "recommendation": value_info.get("recommendation", "")
            })
        
        # 按推荐分数排序
        recommendations.sort(key=lambda x: x["recommendation_score"], reverse=True)
        
        return recommendations[:top_n]
