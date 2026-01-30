"""
内容质量评分系统
自动评估内容是否符合 GEO 原则，提供改进建议
"""
from typing import Dict, List, Optional
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import StrOutputParser
import json
import re


class ContentScorer:
    """内容质量评分器"""
    
    def __init__(self):
        self.scoring_prompt_template = """
你是一名 GEO（生成式引擎优化）内容质量评估专家。请对以下内容进行全面评估，并给出详细的评分和改进建议。

【内容】
{content}

【品牌】{brand}
【优势】{advantages}
【平台】{platform}

【评估维度】
请从以下维度进行评估（每个维度 0-25 分，总分 100 分）：

1. **结构化程度**（25分）
   - 是否有清晰的标题层级？
   - 是否包含清单、列表、FAQ 等结构化元素？
   - 内容层次是否清晰？
   - 是否有结论摘要？

2. **品牌提及质量**（25分）
   - 品牌提及次数是否合适（2-4次）？
   - 品牌提及位置是否靠前（前1/3优先）？
   - 品牌提及是否自然（先通用标准，再品牌适用）？
   - 品牌与内容的关联度如何？

3. **内容权威性**（25分）
   - 是否有数据支撑或案例引用？
   - 是否有评估维度或选择标准？
   - 是否避免编造数据（使用占位建议）？
   - 内容是否专业可信？

4. **可引用性**（25分）
   - 信息密度是否高？
   - 结论是否先行？
   - 是否容易被 AI 提取和引用？
   - 是否符合目标平台的格式要求？

【输出格式】
请严格按照以下 JSON 格式输出，不要添加任何其他内容：

{{
  "scores": {{
    "structure": <结构化得分 0-25>,
    "brand_mention": <品牌提及得分 0-25>,
    "authority": <权威性得分 0-25>,
    "citations": <可引用性得分 0-25>,
    "total": <总分 0-100>
  }},
  "details": {{
    "structure": "<结构化评估详情>",
    "brand_mention": "<品牌提及评估详情>",
    "authority": "<权威性评估详情>",
    "citations": "<可引用性评估详情>"
  }},
  "improvements": [
    "<改进建议1>",
    "<改进建议2>",
    "<改进建议3>"
  ],
  "strengths": [
    "<优点1>",
    "<优点2>"
  ]
}}

【开始评估】
"""
    
    def score_content(self, content: str, brand: str, advantages: str, 
                     platform: str, llm_chain) -> Dict:
        """
        对内容进行质量评分
        
        Args:
            content: 要评分的内容
            brand: 品牌名称
            advantages: 品牌优势
            platform: 发布平台
            llm_chain: LangChain 链对象
            
        Returns:
            包含评分、详情和改进建议的字典
        """
        try:
            prompt = PromptTemplate.from_template(self.scoring_prompt_template)
            chain = prompt | llm_chain | StrOutputParser()
            
            result = chain.invoke({
                "content": content,
                "brand": brand,
                "advantages": advantages,
                "platform": platform
            })
            
            # 尝试解析 JSON
            score_data = self._parse_score_result(result)
            
            return score_data
            
        except Exception as e:
            # 如果评分失败，返回默认评分
            return {
                "scores": {
                    "structure": 0,
                    "brand_mention": 0,
                    "authority": 0,
                    "citations": 0,
                    "total": 0
                },
                "details": {
                    "structure": f"评分失败：{str(e)}",
                    "brand_mention": "",
                    "authority": "",
                    "citations": ""
                },
                "improvements": ["评分系统暂时无法评估此内容，请手动检查"],
                "strengths": []
            }
    
    def _parse_score_result(self, result: str) -> Dict:
        """解析评分结果"""
        # 尝试提取 JSON
        json_match = re.search(r'\{.*\}', result, re.DOTALL)
        if json_match:
            try:
                score_data = json.loads(json_match.group())
                # 验证数据结构
                if "scores" in score_data and "total" in score_data["scores"]:
                    return score_data
            except json.JSONDecodeError:
                pass
        
        # 如果无法解析 JSON，尝试从文本中提取信息
        return self._extract_scores_from_text(result)
    
    def _extract_scores_from_text(self, text: str) -> Dict:
        """从文本中提取评分信息（备用方案）"""
        # 尝试提取总分
        total_match = re.search(r'总分[：:]\s*(\d+)', text)
        total_score = int(total_match.group(1)) if total_match else 0
        
        # 简单分配分数（如果无法精确提取）
        avg_score = total_score // 4 if total_score > 0 else 0
        
        return {
            "scores": {
                "structure": avg_score,
                "brand_mention": avg_score,
                "authority": avg_score,
                "citations": avg_score,
                "total": total_score
            },
            "details": {
                "structure": "无法解析详细评分",
                "brand_mention": "无法解析详细评分",
                "authority": "无法解析详细评分",
                "citations": "无法解析详细评分"
            },
            "improvements": ["请检查内容是否符合 GEO 原则"],
            "strengths": []
        }
    
    def get_score_level(self, total_score: int) -> tuple:
        """
        根据总分返回等级和颜色
        
        Returns:
            (等级名称, 颜色代码)
        """
        if total_score >= 90:
            return ("优秀", "#10B981")  # 绿色
        elif total_score >= 75:
            return ("良好", "#3B82F6")  # 蓝色
        elif total_score >= 60:
            return ("中等", "#F59E0B")  # 橙色
        else:
            return ("需改进", "#EF4444")  # 红色
    
    def get_quick_assessment(self, content: str, brand: str) -> Dict:
        """
        快速评估（不调用 LLM，基于规则）
        用于在 LLM 评分前提供初步评估
        """
        assessment = {
            "has_title": bool(re.search(r'^#+\s+|^标题|^##', content, re.MULTILINE)),
            "has_list": bool(re.search(r'[-*•]\s+|^\d+[\.\)]\s+', content, re.MULTILINE)),
            "has_faq": bool(re.search(r'FAQ|常见问题|Q[：:]|问[：:]', content, re.IGNORECASE)),
            "brand_count": len(re.findall(re.escape(brand), content, re.IGNORECASE)),
            "word_count": len(content)
        }
        
        # 计算初步分数
        quick_score = 0
        if assessment["has_title"]:
            quick_score += 5
        if assessment["has_list"]:
            quick_score += 5
        if assessment["has_faq"]:
            quick_score += 5
        if 2 <= assessment["brand_count"] <= 4:
            quick_score += 10
        elif assessment["brand_count"] > 4:
            quick_score += 5
        
        assessment["quick_score"] = min(quick_score, 30)  # 最高30分（快速评估）
        
        return assessment
