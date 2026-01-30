"""
ROI 分析与成本优化模块
用于计算 API 调用成本、分析 ROI、提供成本优化建议
"""
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
import pandas as pd
from collections import defaultdict


class ROIAnalyzer:
    """ROI 分析器"""
    
    def __init__(self, usd_to_cny_rate: float = 7.2):
        """
        Args:
            usd_to_cny_rate: USD 到 CNY 的汇率（默认 7.2）
        """
        self.usd_to_cny_rate = usd_to_cny_rate
        
        # 各平台 API 定价（每 1K tokens，USD）
        # 注意：这些是示例价格，实际价格可能不同，需要根据实际情况更新
        self.pricing_config = {
            "DeepSeek": {
                "input": 0.00014,  # $0.14 per 1M tokens
                "output": 0.00028,  # $0.28 per 1M tokens
            },
            "OpenAI (GPT)": {
                "gpt-4": {"input": 0.03, "output": 0.06},
                "gpt-4-turbo": {"input": 0.01, "output": 0.03},
                "gpt-3.5-turbo": {"input": 0.0005, "output": 0.0015},
            },
            "Tongyi (通义千问)": {
                "qwen-plus": {"input": 0.002, "output": 0.008},
                "qwen-turbo": {"input": 0.0008, "output": 0.002},
            },
            "Groq": {
                "input": 0.0,  # 免费
                "output": 0.0,
            },
            "Moonshot (Kimi)": {
                "moonshot-v1-8k": {"input": 0.012, "output": 0.012},
                "moonshot-v1-32k": {"input": 0.024, "output": 0.024},
            },
            "豆包（字节跳动）": {
                "doubao-pro-4k": {"input": 0.0008, "output": 0.002},
                "doubao-lite-4k": {"input": 0.0004, "output": 0.001},
            },
            "文心一言（百度）": {
                "ernie-4.0": {"input": 0.012, "output": 0.012},
                "ernie-3.5": {"input": 0.002, "output": 0.002},
            },
        }
    
    def calculate_cost(
        self,
        provider: str,
        model: str,
        input_tokens: int,
        output_tokens: int
    ) -> Tuple[float, float]:
        """
        计算 API 调用成本
        
        Args:
            provider: 提供商名称
            model: 模型名称
            input_tokens: 输入 token 数量
            output_tokens: 输出 token 数量
            
        Returns:
            (cost_usd, cost_cny) 元组
        """
        cost_usd = 0.0
        
        # 获取定价配置
        pricing = self.pricing_config.get(provider, {})
        
        if not pricing:
            # 如果没有配置，返回 0
            return 0.0, 0.0
        
        # 处理不同的定价结构
        if "input" in pricing and "output" in pricing:
            # 统一定价（如 DeepSeek、Groq）
            input_price = pricing["input"]
            output_price = pricing["output"]
        elif model in pricing:
            # 按模型定价（如 OpenAI）
            model_pricing = pricing[model]
            input_price = model_pricing.get("input", 0.0)
            output_price = model_pricing.get("output", 0.0)
        else:
            # 默认使用第一个模型的定价
            if pricing:
                first_model = list(pricing.keys())[0]
                if isinstance(pricing[first_model], dict):
                    input_price = pricing[first_model].get("input", 0.0)
                    output_price = pricing[first_model].get("output", 0.0)
                else:
                    input_price = pricing.get("input", 0.0)
                    output_price = pricing.get("output", 0.0)
            else:
                input_price = 0.0
                output_price = 0.0
        
        # 计算成本（价格是每 1K tokens）
        cost_usd = (input_tokens / 1000.0 * input_price) + (output_tokens / 1000.0 * output_price)
        cost_cny = cost_usd * self.usd_to_cny_rate
        
        return cost_usd, cost_cny
    
    def analyze_costs(
        self,
        api_calls_df: pd.DataFrame,
        verify_results_df: Optional[pd.DataFrame] = None
    ) -> Dict:
        """
        分析成本数据
        
        Args:
            api_calls_df: API 调用记录 DataFrame
            verify_results_df: 验证结果 DataFrame（可选，用于 ROI 分析）
            
        Returns:
            成本分析结果字典
        """
        if api_calls_df.empty:
            return {
                "total_cost_usd": 0.0,
                "total_cost_cny": 0.0,
                "total_tokens": 0,
                "total_calls": 0,
                "cost_by_operation": {},
                "cost_by_provider": {},
                "cost_by_keyword": {},
                "cost_by_platform": {},
                "daily_costs": [],
                "roi_analysis": {}
            }
        
        # 总成本
        total_cost_usd = api_calls_df["成本(USD)"].sum()
        total_cost_cny = api_calls_df["成本(CNY)"].sum()
        total_tokens = api_calls_df["总Token"].sum()
        total_calls = len(api_calls_df)
        
        # 按操作类型统计
        cost_by_operation = {}
        if "操作类型" in api_calls_df.columns:
            operation_groups = api_calls_df.groupby("操作类型")
            for op_type, group in operation_groups:
                cost_by_operation[op_type] = {
                    "cost_usd": group["成本(USD)"].sum(),
                    "cost_cny": group["成本(CNY)"].sum(),
                    "calls": len(group),
                    "tokens": group["总Token"].sum()
                }
        
        # 按提供商统计
        cost_by_provider = {}
        if "提供商" in api_calls_df.columns:
            provider_groups = api_calls_df.groupby("提供商")
            for provider, group in provider_groups:
                cost_by_provider[provider] = {
                    "cost_usd": group["成本(USD)"].sum(),
                    "cost_cny": group["成本(CNY)"].sum(),
                    "calls": len(group),
                    "tokens": group["总Token"].sum()
                }
        
        # 按关键词统计
        cost_by_keyword = {}
        if "关键词" in api_calls_df.columns:
            keyword_groups = api_calls_df.groupby("关键词")
            for keyword, group in keyword_groups:
                if pd.notna(keyword) and keyword:
                    cost_by_keyword[keyword] = {
                        "cost_usd": group["成本(USD)"].sum(),
                        "cost_cny": group["成本(CNY)"].sum(),
                        "calls": len(group),
                        "tokens": group["总Token"].sum()
                    }
        
        # 按平台统计
        cost_by_platform = {}
        if "平台" in api_calls_df.columns:
            platform_groups = api_calls_df.groupby("平台")
            for platform, group in platform_groups:
                if pd.notna(platform) and platform:
                    cost_by_platform[platform] = {
                        "cost_usd": group["成本(USD)"].sum(),
                        "cost_cny": group["成本(CNY)"].sum(),
                        "calls": len(group),
                        "tokens": group["总Token"].sum()
                    }
        
        # 每日成本趋势
        daily_costs = []
        if "调用时间" in api_calls_df.columns:
            api_calls_df["日期"] = pd.to_datetime(api_calls_df["调用时间"]).dt.date
            daily_groups = api_calls_df.groupby("日期")
            for date, group in daily_groups:
                daily_costs.append({
                    "date": date.isoformat() if isinstance(date, datetime.date) else str(date),
                    "cost_usd": group["成本(USD)"].sum(),
                    "cost_cny": group["成本(CNY)"].sum(),
                    "calls": len(group),
                    "tokens": group["总Token"].sum()
                })
            daily_costs.sort(key=lambda x: x["date"])
        
        # ROI 分析（如果有验证结果）
        roi_analysis = {}
        if verify_results_df is not None and not verify_results_df.empty:
            roi_analysis = self._calculate_roi(api_calls_df, verify_results_df)
        
        return {
            "total_cost_usd": total_cost_usd,
            "total_cost_cny": total_cost_cny,
            "total_tokens": int(total_tokens),
            "total_calls": total_calls,
            "cost_by_operation": cost_by_operation,
            "cost_by_provider": cost_by_provider,
            "cost_by_keyword": cost_by_keyword,
            "cost_by_platform": cost_by_platform,
            "daily_costs": daily_costs,
            "roi_analysis": roi_analysis
        }
    
    def _calculate_roi(
        self,
        api_calls_df: pd.DataFrame,
        verify_results_df: pd.DataFrame
    ) -> Dict:
        """
        计算 ROI（基于验证结果）
        
        Args:
            api_calls_df: API 调用记录
            verify_results_df: 验证结果
            
        Returns:
            ROI 分析结果
        """
        # 计算总成本
        total_cost = api_calls_df["成本(CNY)"].sum()
        
        # 计算提及率提升（简化估算）
        # 这里假设每次提及的价值为某个固定值（需要根据实际情况调整）
        mention_value_per_mention = 10.0  # 每次提及的价值（CNY），可配置
        
        # 统计品牌提及次数
        brand_mentions = verify_results_df[verify_results_df["品牌"] == verify_results_df["品牌"].iloc[0] if len(verify_results_df) > 0 else ""]
        total_mentions = brand_mentions["提及次数"].sum() if "提及次数" in brand_mentions.columns else 0
        
        # 估算价值
        estimated_value = total_mentions * mention_value_per_mention
        
        # 计算 ROI
        roi_ratio = (estimated_value - total_cost) / total_cost * 100 if total_cost > 0 else 0
        roi_value = estimated_value - total_cost
        
        # 按关键词分析 ROI
        keyword_roi = {}
        if "关键词" in api_calls_df.columns and "问题" in verify_results_df.columns:
            # 合并数据
            keyword_costs = api_calls_df.groupby("关键词")["成本(CNY)"].sum()
            keyword_mentions = verify_results_df.groupby("问题")["提及次数"].sum()
            
            for keyword in keyword_costs.index:
                if pd.notna(keyword) and keyword:
                    cost = keyword_costs[keyword]
                    mentions = keyword_mentions.get(keyword, 0)
                    value = mentions * mention_value_per_mention
                    roi = (value - cost) / cost * 100 if cost > 0 else 0
                    
                    keyword_roi[keyword] = {
                        "cost": cost,
                        "mentions": int(mentions),
                        "value": value,
                        "roi": roi
                    }
        
        return {
            "total_cost": total_cost,
            "total_mentions": int(total_mentions),
            "estimated_value": estimated_value,
            "roi_ratio": roi_ratio,
            "roi_value": roi_value,
            "mention_value_per_mention": mention_value_per_mention,
            "keyword_roi": keyword_roi
        }
    
    def get_optimization_suggestions(self, cost_analysis: Dict) -> List[Dict]:
        """
        获取成本优化建议
        
        Args:
            cost_analysis: 成本分析结果
            
        Returns:
            优化建议列表
        """
        suggestions = []
        
        total_cost = cost_analysis.get("total_cost_cny", 0.0)
        cost_by_provider = cost_analysis.get("cost_by_provider", {})
        cost_by_keyword = cost_analysis.get("cost_by_keyword", {})
        cost_by_operation = cost_analysis.get("cost_by_operation", {})
        
        # 检查是否有高成本提供商
        if cost_by_provider:
            sorted_providers = sorted(
                cost_by_provider.items(),
                key=lambda x: x[1]["cost_cny"],
                reverse=True
            )
            top_provider = sorted_providers[0]
            if top_provider[1]["cost_cny"] > total_cost * 0.5:
                suggestions.append({
                    "type": "provider",
                    "priority": "高",
                    "title": f"考虑使用更便宜的提供商替代 {top_provider[0]}",
                    "description": f"{top_provider[0]} 占总成本的 {top_provider[1]['cost_cny']/total_cost*100:.1f}%，考虑使用更经济的替代方案",
                    "savings_estimate": top_provider[1]["cost_cny"] * 0.3  # 估算可节省30%
                })
        
        # 检查是否有低 ROI 关键词
        roi_analysis = cost_analysis.get("roi_analysis", {})
        keyword_roi = roi_analysis.get("keyword_roi", {})
        if keyword_roi:
            low_roi_keywords = [
                (kw, data) for kw, data in keyword_roi.items()
                if data.get("roi", 0) < 0
            ]
            if low_roi_keywords:
                suggestions.append({
                    "type": "keyword",
                    "priority": "中",
                    "title": f"发现 {len(low_roi_keywords)} 个负 ROI 关键词",
                    "description": "这些关键词的成本高于产生的价值，建议暂停或优化",
                    "keywords": [kw for kw, _ in low_roi_keywords[:5]]
                })
        
        # 检查操作类型分布
        if cost_by_operation:
            verify_cost = cost_by_operation.get("验证", {}).get("cost_cny", 0.0)
            generate_cost = cost_by_operation.get("生成", {}).get("cost_cny", 0.0)
            
            if verify_cost > total_cost * 0.7:
                suggestions.append({
                    "type": "operation",
                    "priority": "中",
                    "title": "验证成本占比过高",
                    "description": f"验证操作占总成本的 {verify_cost/total_cost*100:.1f}%，建议减少验证频率或使用更便宜的验证模型",
                    "savings_estimate": verify_cost * 0.2
                })
        
        # 如果没有建议，添加通用建议
        if not suggestions:
            suggestions.append({
                "type": "general",
                "priority": "低",
                "title": "成本控制良好",
                "description": "当前成本结构合理，继续保持"
            })
        
        return suggestions
    
    def estimate_future_cost(
        self,
        api_calls_df: pd.DataFrame,
        days: int = 30
    ) -> Dict:
        """
        估算未来成本
        
        Args:
            api_calls_df: 历史 API 调用记录
            days: 预测天数
            
        Returns:
            未来成本估算
        """
        if api_calls_df.empty:
            return {
                "estimated_daily_cost_cny": 0.0,
                "estimated_total_cost_cny": 0.0,
                "confidence": "低"
            }
        
        # 计算日均成本
        if "调用时间" in api_calls_df.columns:
            api_calls_df["日期"] = pd.to_datetime(api_calls_df["调用时间"]).dt.date
            daily_costs = api_calls_df.groupby("日期")["成本(CNY)"].sum()
            
            if len(daily_costs) > 0:
                avg_daily_cost = daily_costs.mean()
                estimated_total = avg_daily_cost * days
                
                # 计算置信度（基于数据点数量）
                confidence = "高" if len(daily_costs) >= 7 else ("中" if len(daily_costs) >= 3 else "低")
                
                return {
                    "estimated_daily_cost_cny": float(avg_daily_cost),
                    "estimated_total_cost_cny": float(estimated_total),
                    "confidence": confidence,
                    "data_points": len(daily_costs)
                }
        
        # 如果没有日期数据，使用总成本估算
        total_cost = api_calls_df["成本(CNY)"].sum()
        # 假设数据覆盖最近7天
        avg_daily = total_cost / 7.0 if total_cost > 0 else 0.0
        
        return {
            "estimated_daily_cost_cny": avg_daily,
            "estimated_total_cost_cny": avg_daily * days,
            "confidence": "低",
            "data_points": 0
        }
