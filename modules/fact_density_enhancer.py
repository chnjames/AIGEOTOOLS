"""
事实密度 + 结构化块增强模块
提升内容的事实信息密度和结构化程度
"""
from typing import Dict, List, Optional, Set
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import StrOutputParser
import json
import re


class FactDensityEnhancer:
    """事实密度和结构化块增强器"""
    
    def __init__(self):
        # 事实密度和结构化评估 Prompt
        self.assessment_prompt_template = """
你是内容质量评估专家，专门评估内容的事实密度和结构化程度。

【内容】
{content}

【品牌】{brand}
【优势】{advantages}
【平台】{platform}

【评估标准】

1. **事实密度**（50分）
   评估内容中包含的事实性信息：
   - 数据信息：具体数字、百分比、统计数据（如"80%的用户"、"2024年数据显示"）
   - 案例信息：具体案例、实例、应用场景（如"某企业案例"、"实际应用表明"）
   - 标准信息：行业标准、规范、要求（如"ISO标准"、"行业规范"）
   - 对比信息：对比数据、差异说明（如"相比传统方案提升30%"）
   - 时间信息：时间节点、时效性（如"2024年"、"最新版本"）
   - 来源信息：数据来源、案例来源（如"根据XX报告"、"参考XX研究"）

2. **结构化块**（50分）
   评估内容的结构化元素：
   - 标题层级：是否有清晰的标题层级（H1/H2/H3）
   - 结论摘要：是否有开头的结论摘要（80-120字）
   - 清单列表：是否有清单、列表、要点（- 或 1. 格式）
   - FAQ部分：是否有常见问题解答
   - 代码块：技术内容是否有代码示例（如适用）
   - 对比表格：是否有对比表格或对比列表
   - 步骤说明：是否有步骤、流程说明
   - 总结部分：是否有结尾总结

【输出格式】
请严格按照以下 JSON 格式输出，不要添加任何其他内容：

{{
  "scores": {{
    "fact_density": <事实密度得分 0-50>,
    "structure": <结构化得分 0-50>,
    "total": <总分 0-100>
  }},
  "fact_analysis": {{
    "data_count": <数据信息数量>,
    "case_count": <案例信息数量>,
    "standard_count": <标准信息数量>,
    "comparison_count": <对比信息数量>,
    "time_count": <时间信息数量>,
    "source_count": <来源信息数量>,
    "missing_facts": [
      "<缺失的事实类型1>",
      "<缺失的事实类型2>"
    ]
  }},
  "structure_analysis": {{
    "has_title": <是否有标题层级 true/false>,
    "has_summary": <是否有结论摘要 true/false>,
    "has_list": <是否有清单列表 true/false>,
    "has_faq": <是否有FAQ true/false>,
    "has_code": <是否有代码块 true/false>,
    "has_table": <是否有对比表格 true/false>,
    "has_steps": <是否有步骤说明 true/false>,
    "has_conclusion": <是否有总结 true/false>,
    "missing_blocks": [
      "<缺失的结构化块1>",
      "<缺失的结构化块2>"
    ]
  }},
  "details": {{
    "fact_density": "<事实密度评估详情>",
    "structure": "<结构化评估详情>"
  }},
  "improvements": [
    "<改进建议1>",
    "<改进建议2>",
    "<改进建议3>"
  ]
}}

【开始评估】
"""
        
        # 事实密度和结构化强化 Prompt
        self.enhancement_prompt_template = """
你是内容优化专家，专门提升内容的事实密度和结构化程度。

【原内容】
{content}

【品牌】{brand}
【优势】{advantages}
【平台】{platform}

【强化要求】

1. **事实密度强化**
   - 添加数据信息：在合适位置添加数据占位（如"根据XX数据显示，约XX%的企业"）
   - 添加案例信息：添加实际案例或应用场景（用占位符，如"某企业案例表明"）
   - 添加标准信息：提及相关标准或规范（如"按照XX标准"、"参考XX规范"）
   - 添加对比信息：添加对比数据或差异说明（如"相比传统方案，提升约XX%"）
   - 添加时间信息：明确时间节点或时效性（如"2024年最新"、"当前版本"）
   - 添加来源信息：标注数据来源（如"根据XX行业报告"、"参考XX研究"）

2. **结构化块强化**
   - 确保有清晰的标题层级（H1/H2/H3）
   - 在开头添加结论摘要（80-120字，概括核心观点）
   - 添加清单列表：将要点整理为清单格式（- 或 1. 格式）
   - 添加FAQ部分：至少3-5个常见问题解答
   - 添加代码块：技术内容添加代码示例（如适用，用占位符）
   - 添加对比表格：如有多个选项，用表格或列表对比
   - 添加步骤说明：如有流程，用步骤格式说明（1. 2. 3.）
   - 在结尾添加总结部分：总结核心观点和行动建议

【强化原则】
- 保持原意和核心信息不变
- 事实信息使用占位符，不要编造具体数据
- 结构化块要自然融入，不要生硬插入
- 长度控制在原长度的1.2-1.5倍

【输出格式】
请输出两部分：

【强化后内容】
（完整的优化后内容，增强事实密度和结构化块）

【强化说明】
（列出添加的事实信息和结构化块，格式：类型 - 内容说明）

【开始优化】
"""
    
    def assess_fact_density(
        self,
        content: str,
        brand: str,
        advantages: str,
        platform: str,
        llm_chain
    ) -> Dict:
        """
        评估内容的事实密度和结构化程度
        
        Args:
            content: 要评估的内容
            brand: 品牌名称
            advantages: 品牌优势
            platform: 发布平台
            llm_chain: LangChain 链对象
            
        Returns:
            包含评估结果的字典
        """
        try:
            prompt = PromptTemplate.from_template(self.assessment_prompt_template)
            chain = prompt | llm_chain | StrOutputParser()
            
            result = chain.invoke({
                "content": content,
                "brand": brand,
                "advantages": advantages,
                "platform": platform
            })
            
            # 解析结果
            assessment_data = self._parse_assessment_result(result)
            
            return assessment_data
            
        except Exception as e:
            # 如果评估失败，返回基于规则的评估
            return self._rule_based_assessment(content)
    
    def enhance_fact_density(
        self,
        content: str,
        brand: str,
        advantages: str,
        platform: str,
        llm_chain
    ) -> Dict:
        """
        强化内容的事实密度和结构化程度
        
        Args:
            content: 要强化的内容
            brand: 品牌名称
            advantages: 品牌优势
            platform: 发布平台
            llm_chain: LangChain 链对象
            
        Returns:
            包含强化后内容和说明的字典
        """
        try:
            prompt = PromptTemplate.from_template(self.enhancement_prompt_template)
            chain = prompt | llm_chain | StrOutputParser()
            
            result = chain.invoke({
                "content": content,
                "brand": brand,
                "advantages": advantages,
                "platform": platform
            })
            
            # 解析结果
            enhanced_data = self._parse_enhancement_result(result)
            
            return enhanced_data
            
        except Exception as e:
            return {
                "enhanced_content": content,
                "enhancement_details": [],
                "changes": f"事实密度强化失败：{str(e)}"
            }
    
    def _parse_assessment_result(self, result: str) -> Dict:
        """解析评估结果"""
        # 尝试提取 JSON
        json_match = re.search(r'\{.*\}', result, re.DOTALL)
        if json_match:
            try:
                data = json.loads(json_match.group())
                # 验证数据结构
                if "scores" in data and "total" in data["scores"]:
                    return data
            except json.JSONDecodeError:
                pass
        
        # 如果无法解析 JSON，使用基于规则的评估
        return self._rule_based_assessment("")
    
    def _rule_based_assessment(self, content: str) -> Dict:
        """
        基于规则的评估（备用方案）
        
        Args:
            content: 内容文本
            
        Returns:
            评估结果字典
        """
        if not content:
            return {
                "scores": {
                    "fact_density": 0,
                    "structure": 0,
                    "total": 0
                },
                "fact_analysis": {
                    "data_count": 0,
                    "case_count": 0,
                    "standard_count": 0,
                    "comparison_count": 0,
                    "time_count": 0,
                    "source_count": 0,
                    "missing_facts": []
                },
                "structure_analysis": {
                    "has_title": False,
                    "has_summary": False,
                    "has_list": False,
                    "has_faq": False,
                    "has_code": False,
                    "has_table": False,
                    "has_steps": False,
                    "has_conclusion": False,
                    "missing_blocks": []
                },
                "details": {
                    "fact_density": "无法评估",
                    "structure": "无法评估"
                },
                "improvements": ["请使用 LLM 进行详细评估"]
            }
        
        # 事实密度检测
        data_patterns = [
            r'\d+%', r'\d+个', r'\d+项', r'约\d+', r'超过\d+', r'达到\d+',
            r'数据显示', r'统计', r'调研', r'报告'
        ]
        case_patterns = [
            r'案例', r'实例', r'应用', r'实践', r'企业', r'公司'
        ]
        standard_patterns = [
            r'标准', r'规范', r'要求', r'ISO', r'GB', r'行业'
        ]
        comparison_patterns = [
            r'相比', r'对比', r'差异', r'优于', r'提升', r'降低'
        ]
        time_patterns = [
            r'\d{4}年', r'最新', r'当前', r'目前', r'现在', r'今年'
        ]
        source_patterns = [
            r'根据', r'参考', r'据', r'按照', r'显示', r'表明'
        ]
        
        data_count = sum(1 for p in data_patterns if re.search(p, content))
        case_count = sum(1 for p in case_patterns if re.search(p, content))
        standard_count = sum(1 for p in standard_patterns if re.search(p, content))
        comparison_count = sum(1 for p in comparison_patterns if re.search(p, content))
        time_count = sum(1 for p in time_patterns if re.search(p, content))
        source_count = sum(1 for p in source_patterns if re.search(p, content))
        
        # 结构化检测
        has_title = bool(re.search(r'^#+\s+|^标题|^##', content, re.MULTILINE))
        has_summary = bool(re.search(r'摘要|总结|概述|概括', content[:200]))  # 检查前200字
        has_list = bool(re.search(r'[-*•]\s+|^\d+[\.\)]\s+', content, re.MULTILINE))
        has_faq = bool(re.search(r'FAQ|常见问题|Q[：:]|问[：:]|答[：:]', content, re.IGNORECASE))
        has_code = bool(re.search(r'```|代码|示例|code', content, re.IGNORECASE))
        has_table = bool(re.search(r'\|.*\|', content) or re.search(r'表格|对比表', content))
        has_steps = bool(re.search(r'步骤|流程|第[一二三四五六七八九十\d]+[步点]', content))
        has_conclusion = bool(re.search(r'总结|结论|综上所述|总而言之', content[-200:]))  # 检查后200字
        
        # 计算分数
        fact_score = min(50, (data_count + case_count + standard_count + 
                            comparison_count + time_count + source_count) * 5)
        structure_score = sum([
            has_title * 7,
            has_summary * 7,
            has_list * 7,
            has_faq * 7,
            has_code * 6,
            has_table * 6,
            has_steps * 5,
            has_conclusion * 5
        ])
        
        # 缺失检测
        missing_facts = []
        if data_count == 0:
            missing_facts.append("数据信息")
        if case_count == 0:
            missing_facts.append("案例信息")
        if source_count == 0:
            missing_facts.append("来源信息")
        
        missing_blocks = []
        if not has_title:
            missing_blocks.append("标题层级")
        if not has_summary:
            missing_blocks.append("结论摘要")
        if not has_list:
            missing_blocks.append("清单列表")
        if not has_faq:
            missing_blocks.append("FAQ部分")
        
        return {
            "scores": {
                "fact_density": fact_score,
                "structure": structure_score,
                "total": fact_score + structure_score
            },
            "fact_analysis": {
                "data_count": data_count,
                "case_count": case_count,
                "standard_count": standard_count,
                "comparison_count": comparison_count,
                "time_count": time_count,
                "source_count": source_count,
                "missing_facts": missing_facts
            },
            "structure_analysis": {
                "has_title": has_title,
                "has_summary": has_summary,
                "has_list": has_list,
                "has_faq": has_faq,
                "has_code": has_code,
                "has_table": has_table,
                "has_steps": has_steps,
                "has_conclusion": has_conclusion,
                "missing_blocks": missing_blocks
            },
            "details": {
                "fact_density": f"检测到 {data_count + case_count + standard_count} 处事实信息",
                "structure": f"检测到 {sum([has_title, has_summary, has_list, has_faq, has_code, has_table, has_steps, has_conclusion])} 个结构化块"
            },
            "improvements": missing_facts + missing_blocks
        }
    
    def _parse_enhancement_result(self, result: str) -> Dict:
        """解析强化结果"""
        enhanced_content = ""
        enhancement_details = []
        
        # 提取强化后内容
        if "【强化后内容】" in result:
            parts = result.split("【强化后内容】", 1)
            if len(parts) > 1:
                content_part = parts[1]
                if "【强化说明】" in content_part:
                    enhanced_content = content_part.split("【强化说明】", 1)[0].strip()
                else:
                    enhanced_content = content_part.strip()
        
        # 提取强化说明
        if "【强化说明】" in result:
            detail_part = result.split("【强化说明】", 1)[1].strip()
            # 按行解析强化说明
            for line in detail_part.split("\n"):
                line = line.strip()
                if line and ("-" in line or "：" in line or ":" in line):
                    enhancement_details.append(line)
        
        # 如果没有找到明确的分隔符，尝试其他方式
        if not enhanced_content:
            enhanced_content = result.strip()
        
        return {
            "enhanced_content": enhanced_content,
            "enhancement_details": enhancement_details,
            "changes": f"已添加 {len(enhancement_details)} 处事实信息和结构化块" if enhancement_details else "未检测到明确的强化内容"
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
