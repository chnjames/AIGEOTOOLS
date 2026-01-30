"""
配置优化助手模块
分析品牌名和优势是否 GEO 友好，提供优化建议
"""
from typing import Dict, List, Optional
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import StrOutputParser
import json
import re


class ConfigOptimizer:
    """配置优化器"""
    
    def __init__(self):
        self.optimization_prompt_template = """
你是GEO（生成式引擎优化）专家，专注于帮助品牌在AI模型中被优先、可信地提及。

【当前配置】
- 主品牌名称：{brand}
- 核心优势/卖点：{advantages}
- 竞品列表：{competitors}

【分析要求】
请从以下维度全面评估当前配置，并给出优化建议：

1. **品牌名独特性分析**
   - 是否过于泛化（如"AI助手"、"智能系统"等通用词）？
   - 是否容易被混淆或误认为是其他品牌？
   - 是否具有搜索友好性（用户容易搜索到）？
   - 是否在AI回答中容易被识别和提及？

2. **优势描述分析**
   - 是否具体、可量化（避免"强大"、"优秀"等模糊词）？
   - 是否具有差异化（与竞品有明显区别）？
   - 是否包含E-E-A-T信号（专业性、经验性、权威性、可信度）？
   - 是否便于AI提取和引用？

3. **竞品对比分析**
   - 当前配置在竞品中是否具有明显优势？
   - 哪些方面容易被竞品超越？
   - 如何强化差异化定位？

4. **GEO友好度评估**
   - 品牌名是否容易被AI优先提及？
   - 优势描述是否符合GEO最佳实践？
   - 整体配置是否有助于提升提及率？

【输出格式】
请严格按照以下格式输出，包含所有部分：

【评估总结】
（200-300字，总结当前配置的优势和不足）

【优化建议】
1. 品牌名优化建议：
   - 问题：[指出当前品牌名的问题]
   - 建议：[给出优化建议]
   
2. 优势描述优化建议：
   - 问题：[指出当前优势描述的问题]
   - 建议：[给出优化建议]

3. 差异化强化建议：
   - 竞品对比：[与竞品的对比分析]
   - 差异化策略：[如何强化差异化]

【推荐版本】
请提供3个优化后的配置版本（从保守到激进），严格按照以下格式输出，每个字段单独一行：

版本1（保守优化）：
品牌名：基于当前品牌名进行保守优化，保持核心品牌名不变
优势描述：优化优势描述，使其更具体、可量化，用顿号分隔多个优势点
理由：说明为什么这样优化，50-100字

版本2（平衡优化）：
品牌名：在品牌名中加入行业关键词，提升搜索友好性
优势描述：聚焦核心价值，突出差异化优势，用顿号分隔多个优势点
理由：说明为什么这样优化，50-100字

版本3（激进优化）：
品牌名：完全重构品牌定位，突出核心特性，最大化GEO效果
优势描述：全面展示优势，包含多个维度，用顿号分隔多个优势点
理由：说明为什么这样优化，50-100字

格式要求（非常重要，必须严格遵守）：
1. 必须严格按照上述格式，每个字段单独一行，使用"品牌名："、"优势描述："、"理由："作为字段标识
2. 品牌名必须提供实际内容，不能使用占位符，必须基于当前品牌名"{brand}"进行优化
3. 优势描述必须提供实际内容，不能使用占位符，必须基于当前优势"{advantages}"进行优化
4. 每个版本都必须完整，不能省略任何字段
5. 不要使用方括号[]、不要使用占位符，必须提供针对当前配置的实际优化内容
6. 品牌名和优势描述必须是具体的、可用的内容，不能是说明性文字

【预期效果】
- 提及率提升预期：[预计提升幅度]
- GEO友好度提升：[预计提升幅度]
- 差异化优势：[预计强化效果]

【开始分析】
"""
    
    def optimize_config(self, brand: str, advantages: str, competitors: List[str], llm_chain) -> Dict:
        """
        优化配置
        
        Args:
            brand: 主品牌名称
            advantages: 核心优势/卖点
            competitors: 竞品列表
            llm_chain: LLM调用链
            
        Returns:
            包含优化建议的字典
        """
        competitors_str = "、".join(competitors) if competitors else "无"
        
        prompt = PromptTemplate.from_template(self.optimization_prompt_template)
        chain = prompt | llm_chain | StrOutputParser()
        
        try:
            result = chain.invoke({
                "brand": brand,
                "advantages": advantages,
                "competitors": competitors_str
            })
            
            # 解析结果
            parsed_result = self._parse_optimization_result(result)
            parsed_result["raw_result"] = result
            parsed_result["success"] = True
            
            # 如果推荐版本为空，尝试备用解析方法
            if not parsed_result.get("recommended_versions") or all(
                not v.get("brand") and not v.get("advantages") 
                for v in parsed_result.get("recommended_versions", [])
            ):
                # 尝试更宽松的解析
                parsed_result = self._parse_optimization_result_fallback(result, parsed_result)
            
            return parsed_result
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "raw_result": ""
            }
    
    def _parse_optimization_result(self, result: str) -> Dict:
        """解析优化结果"""
        parsed = {
            "summary": "",
            "suggestions": {
                "brand": {"problem": "", "suggestion": ""},
                "advantages": {"problem": "", "suggestion": ""},
                "differentiation": {"comparison": "", "strategy": ""}
            },
            "recommended_versions": [],
            "expected_effects": {},
            "parse_errors": []  # 记录解析过程中的错误
        }
        
        # 提取评估总结
        if "【评估总结】" in result:
            summary_section = result.split("【评估总结】")[1].split("【")[0].strip()
            parsed["summary"] = summary_section
        
        # 提取优化建议
        if "【优化建议】" in result:
            suggestions_section = result.split("【优化建议】")[1].split("【")[0]
            
            # 品牌名优化建议 - 更健壮的解析
            brand_patterns = ["品牌名优化建议", "1. 品牌名优化建议", "品牌名"]
            for pattern in brand_patterns:
                if pattern in suggestions_section:
                    brand_section = suggestions_section.split(pattern, 1)[1]
                    # 找到下一个建议的开始位置
                    next_patterns = ["2. 优势描述优化建议", "优势描述优化建议", "3. 差异化强化建议"]
                    for next_pattern in next_patterns:
                        if next_pattern in brand_section:
                            brand_section = brand_section.split(next_pattern)[0]
                            break
                    
                    if "问题：" in brand_section or "问题" in brand_section:
                        problem_text = brand_section.split("问题：")[1] if "问题：" in brand_section else brand_section.split("问题")[1]
                        problem_text = problem_text.split("建议：")[0].split("建议")[0].strip()
                        if problem_text:
                            parsed["suggestions"]["brand"]["problem"] = problem_text
                    
                    if "建议：" in brand_section or "建议" in brand_section:
                        suggestion_text = brand_section.split("建议：")[1] if "建议：" in brand_section else brand_section.split("建议", 1)[1]
                        suggestion_text = suggestion_text.split("2.")[0].split("3.")[0].strip()
                        if suggestion_text:
                            parsed["suggestions"]["brand"]["suggestion"] = suggestion_text
                    break
            
            # 优势描述优化建议 - 更健壮的解析
            adv_patterns = ["优势描述优化建议", "2. 优势描述优化建议", "优势描述"]
            for pattern in adv_patterns:
                if pattern in suggestions_section:
                    adv_section = suggestions_section.split(pattern, 1)[1]
                    # 找到下一个建议的开始位置
                    next_patterns = ["3. 差异化强化建议", "差异化强化建议"]
                    for next_pattern in next_patterns:
                        if next_pattern in adv_section:
                            adv_section = adv_section.split(next_pattern)[0]
                            break
                    
                    if "问题：" in adv_section or "问题" in adv_section:
                        problem_text = adv_section.split("问题：")[1] if "问题：" in adv_section else adv_section.split("问题")[1]
                        problem_text = problem_text.split("建议：")[0].split("建议")[0].strip()
                        if problem_text:
                            parsed["suggestions"]["advantages"]["problem"] = problem_text
                    
                    if "建议：" in adv_section or "建议" in adv_section:
                        suggestion_text = adv_section.split("建议：")[1] if "建议：" in adv_section else adv_section.split("建议", 1)[1]
                        suggestion_text = suggestion_text.split("3.")[0].strip()
                        if suggestion_text:
                            parsed["suggestions"]["advantages"]["suggestion"] = suggestion_text
                    break
        
        # 提取推荐版本
        if "【推荐版本】" in result:
            versions_section = result.split("【推荐版本】")[1].split("【")[0]
            
            # 提取3个版本 - 使用更健壮的解析方式
            for i in range(1, 4):
                # 尝试多种匹配模式
                version_patterns = [
                    f"版本{i}（",
                    f"版本{i}：",
                    f"版本{i}",
                    f"版本 {i}",
                    f"Version {i}",
                ]
                
                version_text = None
                for pattern in version_patterns:
                    if pattern in versions_section:
                        # 找到版本开始位置
                        start_idx = versions_section.find(pattern)
                        version_text = versions_section[start_idx + len(pattern):]
                        
                        # 找到下一个版本或结束位置
                        next_patterns = [
                            f"版本{i+1}（" if i < 3 else None,
                            f"版本{i+1}：" if i < 3 else None,
                            f"版本{i+1}" if i < 3 else None,
                            "【预期效果】",
                            "【",
                        ]
                        
                        end_idx = len(version_text)
                        for next_pattern in next_patterns:
                            if next_pattern and next_pattern in version_text:
                                end_idx = min(end_idx, version_text.find(next_pattern))
                        
                        version_text = version_text[:end_idx].strip()
                        break
                
                if not version_text:
                    continue
                
                version_data = {
                    "version_name": f"版本{i}",
                    "brand": "",
                    "advantages": "",
                    "reason": ""
                }
                
                # 提取品牌名 - 支持多种格式，更健壮的解析
                brand_patterns = ["品牌名：", "品牌名", "品牌：", "- 品牌名：", "品牌名"]
                for pattern in brand_patterns:
                    if pattern in version_text:
                        brand_part = version_text.split(pattern, 1)[1]
                        # 提取到换行、下一个字段或下一个版本
                        brand = brand_part.split("\n")[0]
                        # 移除可能的下一个字段标识
                        for next_field in ["优势描述", "理由", "版本", "- 优势描述", "- 理由"]:
                            if next_field in brand:
                                brand = brand.split(next_field)[0]
                        brand = brand.strip()
                        # 移除可能的冒号、破折号等
                        brand = brand.lstrip("：").lstrip(":").lstrip("-").lstrip("—").strip()
                        if brand and len(brand) > 0:
                            version_data["brand"] = brand
                            break
                
                # 提取优势描述 - 支持多种格式，更健壮的解析
                adv_patterns = ["优势描述：", "优势描述", "优势：", "- 优势描述："]
                for pattern in adv_patterns:
                    if pattern in version_text:
                        adv_part = version_text.split(pattern, 1)[1]
                        # 提取到理由或下一个字段
                        advantages = adv_part.split("理由")[0].split("- 理由")[0].split("版本")[0]
                        # 处理多行内容
                        advantages_lines = []
                        for line in advantages.split("\n"):
                            line = line.strip()
                            # 如果遇到下一个字段标识，停止
                            if any(marker in line for marker in ["理由", "版本", "品牌名"]):
                                break
                            if line and not line.startswith("-") and not line.startswith("—"):
                                advantages_lines.append(line)
                        
                        advantages = " ".join(advantages_lines).strip()
                        # 移除可能的冒号、破折号等
                        advantages = advantages.lstrip("：").lstrip(":").lstrip("-").lstrip("—").strip()
                        if advantages and len(advantages) > 0:
                            version_data["advantages"] = advantages
                            break
                
                # 提取理由 - 支持多种格式，更健壮的解析
                reason_patterns = ["理由：", "理由", "- 理由："]
                for pattern in reason_patterns:
                    if pattern in version_text:
                        reason_part = version_text.split(pattern, 1)[1]
                        # 提取到下一个版本或结束
                        reason = reason_part.split("版本")[0]
                        # 处理多行内容
                        reason_lines = []
                        for line in reason.split("\n"):
                            line = line.strip()
                            # 如果遇到下一个版本标识，停止
                            if "版本" in line and any(str(i+1) in line for i in range(1, 4)):
                                break
                            if line and not line.startswith("-") and not line.startswith("—"):
                                reason_lines.append(line)
                        
                        reason = " ".join(reason_lines).strip()
                        # 移除可能的冒号、破折号等
                        reason = reason.lstrip("：").lstrip(":").lstrip("-").lstrip("—").strip()
                        if reason and len(reason) > 0:
                            version_data["reason"] = reason
                            break
                
                # 只有当至少有一个字段有内容时才添加
                if version_data["brand"] or version_data["advantages"]:
                    parsed["recommended_versions"].append(version_data)
                else:
                    # 记录解析失败的版本
                    parsed["parse_errors"].append(f"版本{i}解析失败：未找到品牌名或优势描述")
        
        # 提取预期效果
        if "【预期效果】" in result:
            effects_section = result.split("【预期效果】")[1].strip()
            if "提及率提升预期：" in effects_section:
                parsed["expected_effects"]["mention_rate"] = effects_section.split("提及率提升预期：")[1].split("\n")[0].strip()
            if "GEO友好度提升：" in effects_section:
                parsed["expected_effects"]["geo_friendliness"] = effects_section.split("GEO友好度提升：")[1].split("\n")[0].strip()
        
        return parsed
    
    def _parse_optimization_result_fallback(self, result: str, parsed: Dict) -> Dict:
        """备用解析方法，使用更宽松的规则和正则表达式"""
        # 如果推荐版本部分存在但解析失败，尝试更宽松的解析
        if "【推荐版本】" in result:
            versions_section = result.split("【推荐版本】")[1].split("【")[0]
            
            # 使用正则表达式提取
            import re
            
            # 尝试提取版本1
            version1_match = re.search(r'版本1[^版本]*?品牌名[：:]\s*([^\n]+)', versions_section, re.DOTALL)
            version1_adv_match = re.search(r'版本1[^版本]*?优势描述[：:]\s*([^\n]+)', versions_section, re.DOTALL)
            
            if version1_match or version1_adv_match:
                v1 = {
                    "version_name": "版本1",
                    "brand": version1_match.group(1).strip() if version1_match else "",
                    "advantages": version1_adv_match.group(1).strip() if version1_adv_match else "",
                    "reason": ""
                }
                # 清理品牌名和优势描述
                v1["brand"] = v1["brand"].split("优势描述")[0].split("理由")[0].strip()
                v1["advantages"] = v1["advantages"].split("理由")[0].split("版本")[0].strip()
                if v1["brand"] or v1["advantages"]:
                    if not parsed["recommended_versions"]:
                        parsed["recommended_versions"] = []
                    if len(parsed["recommended_versions"]) < 1:
                        parsed["recommended_versions"].append(v1)
            
            # 尝试提取版本2
            version2_match = re.search(r'版本2[^版本]*?品牌名[：:]\s*([^\n]+)', versions_section, re.DOTALL)
            version2_adv_match = re.search(r'版本2[^版本]*?优势描述[：:]\s*([^\n]+)', versions_section, re.DOTALL)
            
            if version2_match or version2_adv_match:
                v2 = {
                    "version_name": "版本2",
                    "brand": version2_match.group(1).strip() if version2_match else "",
                    "advantages": version2_adv_match.group(1).strip() if version2_adv_match else "",
                    "reason": ""
                }
                # 清理品牌名和优势描述
                v2["brand"] = v2["brand"].split("优势描述")[0].split("理由")[0].strip()
                v2["advantages"] = v2["advantages"].split("理由")[0].split("版本")[0].strip()
                if v2["brand"] or v2["advantages"]:
                    if len(parsed["recommended_versions"]) < 2:
                        parsed["recommended_versions"].append(v2)
            
            # 尝试提取版本3
            version3_match = re.search(r'版本3[^版本]*?品牌名[：:]\s*([^\n]+)', versions_section, re.DOTALL)
            version3_adv_match = re.search(r'版本3[^版本]*?优势描述[：:]\s*([^\n]+)', versions_section, re.DOTALL)
            
            if version3_match or version3_adv_match:
                v3 = {
                    "version_name": "版本3",
                    "brand": version3_match.group(1).strip() if version3_match else "",
                    "advantages": version3_adv_match.group(1).strip() if version3_adv_match else "",
                    "reason": ""
                }
                # 清理品牌名和优势描述
                v3["brand"] = v3["brand"].split("优势描述")[0].split("理由")[0].strip()
                v3["advantages"] = v3["advantages"].split("理由")[0].split("版本")[0].strip()
                if v3["brand"] or v3["advantages"]:
                    if len(parsed["recommended_versions"]) < 3:
                        parsed["recommended_versions"].append(v3)
        
        return parsed
