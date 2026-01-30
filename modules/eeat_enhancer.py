"""
E-E-A-T 强化模块
Expertise（专业性）、Experience（经验性）、Authoritativeness（权威性）、Trustworthiness（可信度）
"""
from typing import Dict, List, Optional
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import StrOutputParser
import json
import re


class EEATEnhancer:
    """E-E-A-T 强化器"""
    
    def __init__(self):
        # E-E-A-T 评估 Prompt
        self.assessment_prompt_template = """
你是一名内容质量评估专家，专门评估内容的 E-E-A-T（专业性、经验性、权威性、可信度）水平。

【内容】
{content}

【品牌】{brand}
【优势】{advantages}
【平台】{platform}

【E-E-A-T 评估标准】

1. **Expertise（专业性）**（25分）
   - 内容是否展示深度的专业知识？
   - 是否使用专业术语和准确的技术描述？
   - 是否提供专业见解和分析？
   - 作者是否表现出对该领域的专业理解？

2. **Experience（经验性）**（25分）
   - 是否包含实际使用经验或案例？
   - 是否有第一手体验描述？
   - 是否分享实践中的洞察和教训？
   - 是否有"我使用过"、"实际测试"等经验性表述？

3. **Authoritativeness（权威性）**（25分）
   - 是否引用权威来源或数据？
   - 是否提及行业标准、研究报告或官方文档？
   - 是否有明确的来源占位建议（如"根据XX报告"、"参考XX标准"）？
   - 内容是否建立在该领域的权威知识基础上？

4. **Trustworthiness（可信度）**（25分）
   - 是否避免编造数据或虚假信息？
   - 是否明确标注不确定信息（如"据公开资料"、"建议参考"）？
   - 是否提供可验证的信息？
   - 内容是否诚实、透明、负责任？

【来源占位检查】
请检查内容中是否包含以下来源占位元素：
- 数据来源占位（如"根据XX行业报告"、"XX数据显示"）
- 案例来源占位（如"某企业案例"、"参考XX实践"）
- 标准来源占位（如"按照XX标准"、"参考XX规范"）
- 专家观点占位（如"行业专家认为"、"XX机构指出"）

【输出格式】
请严格按照以下 JSON 格式输出，不要添加任何其他内容：

{{
  "eeat_scores": {{
    "expertise": <专业性得分 0-25>,
    "experience": <经验性得分 0-25>,
    "authoritativeness": <权威性得分 0-25>,
    "trustworthiness": <可信度得分 0-25>,
    "total": <总分 0-100>
  }},
  "source_placeholders": {{
    "data_sources": ["<数据来源占位1>", "<数据来源占位2>"],
    "case_sources": ["<案例来源占位1>"],
    "standard_sources": ["<标准来源占位1>"],
    "expert_opinions": ["<专家观点占位1>"]
  }},
  "details": {{
    "expertise": "<专业性评估详情>",
    "experience": "<经验性评估详情>",
    "authoritativeness": "<权威性评估详情>",
    "trustworthiness": "<可信度评估详情>"
  }},
  "improvements": [
    "<改进建议1>",
    "<改进建议2>",
    "<改进建议3>"
  ],
  "source_suggestions": [
    "<来源占位建议1>",
    "<来源占位建议2>"
  ]
}}

【开始评估】
"""
        
        # E-E-A-T 强化 Prompt
        self.enhancement_prompt_template = """
你是一名内容优化专家，专门提升内容的 E-E-A-T（专业性、经验性、权威性、可信度）水平。

【原内容】
{content}

【品牌】{brand}
【优势】{advantages}
【平台】{platform}

【E-E-A-T 强化要求】

1. **Expertise（专业性）强化**
   - 增加专业术语和准确的技术描述
   - 提供深度的专业见解和分析
   - 展示对该领域的专业理解
   - 使用行业标准术语

2. **Experience（经验性）强化**
   - 添加实际使用经验或案例描述
   - 包含第一手体验（如"实际测试发现"、"使用中观察到"）
   - 分享实践中的洞察和教训
   - 增加"基于实际使用"、"经过验证"等表述

3. **Authoritativeness（权威性）强化**
   - 添加权威来源占位（如"根据XX行业报告"、"参考XX研究"）
   - 提及行业标准、规范或官方文档
   - 引用权威机构或专家的观点（用占位符）
   - 建立内容在权威知识基础上的表述

4. **Trustworthiness（可信度）强化**
   - 明确标注不确定信息（如"据公开资料显示"、"建议参考官方文档"）
   - 避免编造具体数据，使用占位建议
   - 提供可验证的信息来源占位
   - 保持诚实、透明、负责任的表述

【来源占位要求】
必须在内容中添加以下类型的来源占位（用占位符形式，不要编造真实来源）：

1. **数据来源占位**（至少2处）
   - 格式："根据XX行业报告"、"XX数据显示"、"据XX统计"
   - 示例："根据2024年外贸软件行业报告显示"、"据公开市场调研数据显示"

2. **案例来源占位**（至少1处）
   - 格式："某企业案例"、"参考XX实践"、"XX公司案例"
   - 示例："参考某大型外贸企业的实际应用案例"、"某知名企业的成功实践表明"

3. **标准来源占位**（至少1处）
   - 格式："按照XX标准"、"参考XX规范"、"符合XX要求"
   - 示例："按照ISO质量管理体系标准"、"参考行业最佳实践规范"

4. **专家观点占位**（可选，1处）
   - 格式："行业专家认为"、"XX机构指出"、"权威分析显示"
   - 示例："行业专家普遍认为"、"权威机构分析指出"

【输出格式】
请输出两部分：

【E-E-A-T 强化后内容】
（完整的优化后内容，保持原意和结构，但增强 E-E-A-T 元素）

【来源占位清单】
（列出所有添加的来源占位，格式：类型 - 占位内容）

【开始优化】
"""
    
    def assess_eeat(self, content: str, brand: str, advantages: str, 
                    platform: str, llm_chain) -> Dict:
        """
        评估内容的 E-E-A-T 水平
        
        Args:
            content: 要评估的内容
            brand: 品牌名称
            advantages: 品牌优势
            platform: 发布平台
            llm_chain: LangChain 链对象
            
        Returns:
            包含 E-E-A-T 评分、来源占位检查和改进建议的字典
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
            # 如果评估失败，返回默认数据
            return {
                "eeat_scores": {
                    "expertise": 0,
                    "experience": 0,
                    "authoritativeness": 0,
                    "trustworthiness": 0,
                    "total": 0
                },
                "source_placeholders": {
                    "data_sources": [],
                    "case_sources": [],
                    "standard_sources": [],
                    "expert_opinions": []
                },
                "details": {
                    "expertise": f"评估失败：{str(e)}",
                    "experience": "",
                    "authoritativeness": "",
                    "trustworthiness": ""
                },
                "improvements": ["E-E-A-T 评估系统暂时无法评估此内容，请手动检查"],
                "source_suggestions": []
            }
    
    def enhance_eeat(self, content: str, brand: str, advantages: str, 
                     platform: str, llm_chain) -> Dict:
        """
        强化内容的 E-E-A-T 水平
        
        Args:
            content: 要强化的内容
            brand: 品牌名称
            advantages: 品牌优势
            platform: 发布平台
            llm_chain: LangChain 链对象
            
        Returns:
            包含强化后内容和来源占位清单的字典
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
                "source_placeholders": [],
                "changes": f"E-E-A-T 强化失败：{str(e)}"
            }
    
    def _parse_assessment_result(self, result: str) -> Dict:
        """解析评估结果"""
        # 尝试提取 JSON
        json_match = re.search(r'\{.*\}', result, re.DOTALL)
        if json_match:
            try:
                data = json.loads(json_match.group())
                # 验证数据结构
                if "eeat_scores" in data and "total" in data["eeat_scores"]:
                    return data
            except json.JSONDecodeError:
                pass
        
        # 如果无法解析 JSON，尝试从文本中提取信息
        return self._extract_assessment_from_text(result)
    
    def _extract_assessment_from_text(self, text: str) -> Dict:
        """从文本中提取评估信息（备用方案）"""
        # 尝试提取总分
        total_match = re.search(r'总分[：:]\s*(\d+)', text)
        total_score = int(total_match.group(1)) if total_match else 0
        
        # 简单分配分数
        avg_score = total_score // 4 if total_score > 0 else 0
        
        return {
            "eeat_scores": {
                "expertise": avg_score,
                "experience": avg_score,
                "authoritativeness": avg_score,
                "trustworthiness": avg_score,
                "total": total_score
            },
            "source_placeholders": {
                "data_sources": [],
                "case_sources": [],
                "standard_sources": [],
                "expert_opinions": []
            },
            "details": {
                "expertise": "无法解析详细评估",
                "experience": "无法解析详细评估",
                "authoritativeness": "无法解析详细评估",
                "trustworthiness": "无法解析详细评估"
            },
            "improvements": ["请检查内容是否符合 E-E-A-T 原则"],
            "source_suggestions": []
        }
    
    def _parse_enhancement_result(self, result: str) -> Dict:
        """解析强化结果"""
        enhanced_content = ""
        source_placeholders = []
        changes = ""
        
        # 提取强化后内容
        if "【E-E-A-T 强化后内容】" in result:
            parts = result.split("【E-E-A-T 强化后内容】", 1)
            if len(parts) > 1:
                content_part = parts[1]
                if "【来源占位清单】" in content_part:
                    enhanced_content = content_part.split("【来源占位清单】", 1)[0].strip()
                else:
                    enhanced_content = content_part.strip()
        
        # 提取来源占位清单
        if "【来源占位清单】" in result:
            placeholder_part = result.split("【来源占位清单】", 1)[1].strip()
            # 按行解析占位清单
            for line in placeholder_part.split("\n"):
                line = line.strip()
                if line and "-" in line:
                    source_placeholders.append(line)
        
        # 如果没有找到明确的分隔符，尝试其他方式
        if not enhanced_content:
            # 尝试提取整个结果作为内容
            enhanced_content = result.strip()
        
        return {
            "enhanced_content": enhanced_content,
            "source_placeholders": source_placeholders,
            "changes": f"已添加 {len(source_placeholders)} 个来源占位" if source_placeholders else "未检测到明确的来源占位"
        }
    
    def get_eeat_level(self, total_score: int) -> tuple:
        """
        根据 E-E-A-T 总分返回等级和颜色
        
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
    
    def get_quick_eeat_check(self, content: str) -> Dict:
        """
        快速 E-E-A-T 检查（不调用 LLM，基于规则）
        用于在 LLM 评估前提供初步检查
        """
        check = {
            "has_professional_terms": bool(re.search(r'(标准|规范|体系|框架|方法论|最佳实践)', content)),
            "has_experience_words": bool(re.search(r'(实际|使用|测试|验证|经验|实践|案例)', content)),
            "has_source_placeholders": bool(re.search(r'(根据|参考|据|按照|符合|显示|表明|指出)', content)),
            "has_data_placeholders": bool(re.search(r'(报告|数据|统计|调研|分析)', content)),
            "has_uncertainty_markers": bool(re.search(r'(建议|可能|通常|一般|据公开|参考)', content)),
            "source_placeholder_count": len(re.findall(r'(根据|参考|据|按照|显示|表明)', content))
        }
        
        # 计算初步分数
        quick_score = 0
        if check["has_professional_terms"]:
            quick_score += 5
        if check["has_experience_words"]:
            quick_score += 5
        if check["has_source_placeholders"]:
            quick_score += 5
        if check["has_data_placeholders"]:
            quick_score += 5
        if check["has_uncertainty_markers"]:
            quick_score += 5
        if check["source_placeholder_count"] >= 3:
            quick_score += 5
        
        check["quick_score"] = min(quick_score, 30)  # 最高30分（快速检查）
        
        return check
