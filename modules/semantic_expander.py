"""
语义足迹扩展模块
基于现有关键词，通过语义相似度扩展出更多相关关键词，提升关键词覆盖面
"""
from typing import List, Dict, Set, Optional
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import StrOutputParser
import json
import re
from difflib import SequenceMatcher


class SemanticExpander:
    """语义足迹扩展器"""
    
    def __init__(self):
        # 语义扩展 Prompt
        self.expansion_prompt_template = """
你是关键词扩展专家，专门基于现有关键词生成语义相关的扩展关键词，提升关键词覆盖面。

【现有关键词】
{existing_keywords}

【品牌】{brand}
【优势】{advantages}
【扩展数量】{expansion_count}

【语义足迹扩展要求】

1. **语义相关性**
   - 生成的关键词必须与现有关键词在语义上相关
   - 覆盖相同的搜索意图，但使用不同的表达方式
   - 包含同义词、近义词、相关概念

2. **覆盖面扩展**
   - 从不同角度扩展：功能角度、场景角度、用户角度、问题角度
   - 包含长尾词变体：更具体、更细分、更口语化
   - 覆盖相关领域：上下游、关联概念、延伸话题

3. **多样性**
   - 避免与现有关键词重复或过于相似
   - 使用不同的表达方式（口语化、正式、专业等）
   - 包含不同长度（短词、长尾词）

4. **质量要求**
   - 保持自然、符合用户搜索习惯
   - 长度控制在 8-30 字
   - 避免生硬拼接

【扩展策略】

1. **同义扩展**：使用同义词替换关键词中的核心词
   - 示例："外贸ERP软件" → "外贸管理系统"、"外贸业务软件"

2. **场景扩展**：添加使用场景或应用场景
   - 示例："外贸ERP" → "小型企业外贸ERP"、"跨境电商ERP"

3. **问题扩展**：转换为问题形式
   - 示例："外贸ERP推荐" → "外贸ERP哪个好"、"如何选择外贸ERP"

4. **功能扩展**：突出不同功能点
   - 示例："外贸ERP" → "外贸订单管理软件"、"外贸库存管理ERP"

5. **长尾扩展**：生成更具体的长尾词
   - 示例："外贸ERP" → "适合小企业的外贸ERP软件"、"支持多语言的外贸ERP系统"

【输出格式】
请严格按照以下 JSON 格式输出，不要添加任何其他内容：

{{
  "expanded_keywords": [
    "<扩展关键词1>",
    "<扩展关键词2>",
    ...
  ],
  "expansion_stats": {{
    "total_expanded": <扩展总数>,
    "synonym_count": <同义扩展数量>,
    "scenario_count": <场景扩展数量>,
    "question_count": <问题扩展数量>,
    "feature_count": <功能扩展数量>,
    "longtail_count": <长尾扩展数量>
  }},
  "expansion_details": [
    {{
      "original": "<原关键词>",
      "expanded": ["<扩展词1>", "<扩展词2>"],
      "type": "<扩展类型：同义/场景/问题/功能/长尾>"
    }},
    ...
  ]
}}

【开始扩展】
"""
    
    def expand_keywords(
        self,
        existing_keywords: List[str],
        brand: str,
        advantages: str,
        expansion_count: int,
        llm_chain
    ) -> Dict:
        """
        基于现有关键词进行语义扩展
        
        Args:
            existing_keywords: 现有关键词列表
            brand: 品牌名称
            advantages: 品牌优势
            expansion_count: 期望扩展的关键词数量
            llm_chain: LangChain 链对象
            
        Returns:
            包含扩展关键词、统计信息和详细信息的字典
        """
        if not existing_keywords:
            return {
                "expanded_keywords": [],
                "expansion_stats": {
                    "total_expanded": 0,
                    "synonym_count": 0,
                    "scenario_count": 0,
                    "question_count": 0,
                    "feature_count": 0,
                    "longtail_count": 0
                },
                "expansion_details": []
            }
        
        try:
            # 限制输入关键词数量，避免 Prompt 过长
            keywords_to_expand = existing_keywords[:50]  # 最多处理50个关键词
            
            prompt = PromptTemplate.from_template(self.expansion_prompt_template)
            chain = prompt | llm_chain | StrOutputParser()
            
            result = chain.invoke({
                "existing_keywords": json.dumps(keywords_to_expand, ensure_ascii=False, indent=2),
                "brand": brand,
                "advantages": advantages,
                "expansion_count": expansion_count
            })
            
            # 解析结果
            expansion_data = self._parse_expansion_result(result, existing_keywords)
            
            return expansion_data
            
        except Exception as e:
            # 如果扩展失败，返回基于规则的简单扩展
            return self._rule_based_expansion(existing_keywords, expansion_count)
    
    def _parse_expansion_result(self, result: str, original_keywords: List[str]) -> Dict:
        """解析扩展结果"""
        # 尝试提取 JSON
        json_match = re.search(r'\{.*\}', result, re.DOTALL)
        if json_match:
            try:
                data = json.loads(json_match.group())
                # 验证数据结构
                if "expanded_keywords" in data:
                    # 去重和过滤
                    expanded = self._deduplicate_keywords(
                        data["expanded_keywords"],
                        original_keywords
                    )
                    data["expanded_keywords"] = expanded
                    # 更新统计信息
                    if "expansion_stats" in data:
                        data["expansion_stats"]["total_expanded"] = len(expanded)
                    return data
            except json.JSONDecodeError:
                pass
        
        # 如果无法解析 JSON，尝试从文本中提取
        return self._extract_keywords_from_text(result, original_keywords)
    
    def _extract_keywords_from_text(self, text: str, original_keywords: List[str]) -> Dict:
        """从文本中提取关键词（备用方案）"""
        # 尝试提取数组
        array_match = re.search(r'\[[\s\S]*?\]', text)
        if array_match:
            try:
                keywords = json.loads(array_match.group())
                if isinstance(keywords, list):
                    expanded = self._deduplicate_keywords(keywords, original_keywords)
                    return {
                        "expanded_keywords": expanded,
                        "expansion_stats": {
                            "total_expanded": len(expanded),
                            "synonym_count": 0,
                            "scenario_count": 0,
                            "question_count": 0,
                            "feature_count": 0,
                            "longtail_count": 0
                        },
                        "expansion_details": []
                    }
            except json.JSONDecodeError:
                pass
        
        # 如果还是无法解析，使用基于规则的扩展
        return self._rule_based_expansion(original_keywords, len(original_keywords))
    
    def _deduplicate_keywords(
        self,
        expanded_keywords: List[str],
        original_keywords: List[str],
        similarity_threshold: float = 0.85
    ) -> List[str]:
        """
        去重和过滤扩展关键词
        
        Args:
            expanded_keywords: 扩展的关键词列表
            original_keywords: 原始关键词列表
            similarity_threshold: 相似度阈值
            
        Returns:
            去重后的关键词列表
        """
        if not expanded_keywords:
            return []
        
        # 转换为小写用于比较
        original_lower = [k.lower() for k in original_keywords]
        seen = set(original_lower)
        deduplicated = []
        
        for keyword in expanded_keywords:
            if not isinstance(keyword, str):
                continue
            
            keyword = keyword.strip()
            if not keyword or len(keyword) < 3:
                continue
            
            keyword_lower = keyword.lower()
            
            # 检查是否与原始关键词重复
            if keyword_lower in seen:
                continue
            
            # 检查是否与已添加的关键词相似
            is_similar = False
            for existing in seen:
                similarity = SequenceMatcher(None, keyword_lower, existing).ratio()
                if similarity >= similarity_threshold:
                    is_similar = True
                    break
            
            if not is_similar:
                seen.add(keyword_lower)
                deduplicated.append(keyword)
        
        return deduplicated
    
    def _rule_based_expansion(
        self,
        keywords: List[str],
        max_expansion: int = 20
    ) -> Dict:
        """
        基于规则的简单扩展（备用方案，不依赖 LLM）
        
        Args:
            keywords: 原始关键词列表
            max_expansion: 最大扩展数量
            
        Returns:
            扩展结果字典
        """
        expanded = []
        
        # 简单的扩展规则
        question_markers = ["哪个好", "哪家好", "如何选择", "怎么选", "推荐", "排行"]
        scenario_markers = ["适合", "适用于", "针对", "面向"]
        feature_markers = ["功能", "特点", "优势", "特色"]
        
        for keyword in keywords[:10]:  # 限制处理数量
            if not keyword or len(keyword) < 3:
                continue
            
            # 问题形式扩展
            for marker in question_markers[:2]:  # 只生成2个问题形式
                if marker not in keyword:
                    expanded.append(f"{keyword}{marker}")
                    if len(expanded) >= max_expansion:
                        break
            if len(expanded) >= max_expansion:
                break
            
            # 场景扩展
            for marker in scenario_markers[:1]:  # 只生成1个场景形式
                if marker not in keyword:
                    expanded.append(f"{marker}{keyword}")
                    if len(expanded) >= max_expansion:
                        break
            if len(expanded) >= max_expansion:
                break
        
        return {
            "expanded_keywords": expanded[:max_expansion],
            "expansion_stats": {
                "total_expanded": len(expanded[:max_expansion]),
                "synonym_count": 0,
                "scenario_count": len([k for k in expanded if any(m in k for m in scenario_markers)]),
                "question_count": len([k for k in expanded if any(m in k for m in question_markers)]),
                "feature_count": 0,
                "longtail_count": 0
            },
            "expansion_details": []
        }
    
    def analyze_expansion_coverage(
        self,
        original_keywords: List[str],
        expanded_keywords: List[str]
    ) -> Dict:
        """
        分析扩展的覆盖面
        
        Args:
            original_keywords: 原始关键词列表
            expanded_keywords: 扩展后的关键词列表
            
        Returns:
            覆盖面分析结果
        """
        if not original_keywords or not expanded_keywords:
            return {
                "coverage_ratio": 0.0,
                "expansion_ratio": 0.0,
                "unique_keywords": 0,
                "categories": {}
            }
        
        # 计算扩展比例
        expansion_ratio = len(expanded_keywords) / len(original_keywords) if original_keywords else 0
        
        # 分析关键词类别（简单分类）
        categories = {
            "question": len([k for k in expanded_keywords if any(m in k for m in ["哪个", "如何", "怎么", "什么"])]),
            "scenario": len([k for k in expanded_keywords if any(m in k for m in ["适合", "适用于", "针对"])]),
            "comparison": len([k for k in expanded_keywords if any(m in k for m in ["对比", "比较", "区别"])]),
            "feature": len([k for k in expanded_keywords if any(m in k for m in ["功能", "特点", "优势"])]),
            "other": 0
        }
        categories["other"] = len(expanded_keywords) - sum(categories.values())
        
        return {
            "coverage_ratio": min(expansion_ratio, 5.0),  # 最多5倍扩展
            "expansion_ratio": expansion_ratio,
            "unique_keywords": len(set(expanded_keywords)),
            "categories": categories
        }
    
    def merge_keywords(
        self,
        original_keywords: List[str],
        expanded_keywords: List[str],
        merge_strategy: str = "append"
    ) -> List[str]:
        """
        合并原始关键词和扩展关键词
        
        Args:
            original_keywords: 原始关键词列表
            expanded_keywords: 扩展关键词列表
            merge_strategy: 合并策略
                - "append": 追加扩展关键词到原始列表
                - "replace": 用扩展关键词替换原始列表
                - "interleave": 交替插入
            
        Returns:
            合并后的关键词列表
        """
        if merge_strategy == "replace":
            return expanded_keywords
        elif merge_strategy == "interleave":
            # 交替插入
            merged = []
            max_len = max(len(original_keywords), len(expanded_keywords))
            for i in range(max_len):
                if i < len(original_keywords):
                    merged.append(original_keywords[i])
                if i < len(expanded_keywords):
                    merged.append(expanded_keywords[i])
            return merged
        else:  # append
            return original_keywords + expanded_keywords
