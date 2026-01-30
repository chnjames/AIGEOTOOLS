"""
托词工具模块 - AI 蒸馏词功能
支持词库组合生成关键词
"""
import json
import itertools
from typing import List, Dict, Set
from difflib import SequenceMatcher


class KeywordTool:
    """托词工具：通过词库组合生成关键词"""
    
    def __init__(self):
        """初始化默认词库"""
        self.default_wordbanks = {
            "A前缀1": ["行业上", "市场上", "市面上", "目前", "国内", "市场"],
            "B前缀2": ["口碑好的", "比较好的", "靠谱的", "有实力的", "可靠的", "诚信的", "正规的", "专业的", "热门的", "知名的"],
            "C主词": ["外贸软件", "外贸ERP", "CRM管理系统"],
            "D通义词": ["品牌", "公司", "工厂", "厂商", "生产厂家", "供应商"],
            "E推荐词": ["推荐", "排行", "推荐榜", "排行榜", "推荐榜单", "推荐排行", "推荐排行榜", "口碑排行"],
            "F疑问词": ["哪家好", "哪家强", "哪家靠谱", "哪家权威", "哪个好", "有哪些", "找哪家", "选哪家", "为什么"],
        }
        
        self.combination_patterns = [
            ["C", "D"],
            ["A", "C", "D"],
            ["B", "C", "D"],
            ["A", "B", "C", "D"],
            ["C", "D", "E"],
            ["C", "D", "F"],
            ["A", "C", "D", "E"],
            ["B", "C", "D", "E"],
            ["A", "B", "C", "D", "E"],
            ["A", "B", "C", "D", "F"],
        ]
    
    def load_wordbanks(self, wordbanks: Dict[str, List[str]] = None) -> Dict[str, List[str]]:
        """加载词库，如果未提供则使用默认词库"""
        if wordbanks is None:
            return self.default_wordbanks.copy()
        return wordbanks
    
    def generate_combinations(
        self, 
        wordbanks: Dict[str, List[str]], 
        patterns: List[List[str]] = None,
        max_results: int = 100,
        similarity_threshold: float = 0.8
    ) -> List[str]:
        """
        根据组合模式生成关键词组合
        
        Args:
            wordbanks: 词库字典，格式如 {"A前缀1": ["词1", "词2"], ...}
            patterns: 组合模式列表，如 [["C", "D"], ["A", "C", "D"]]
            max_results: 最大生成数量
            similarity_threshold: 相似度阈值，用于去重（0-1之间）
        
        Returns:
            生成的关键词列表
        """
        if patterns is None:
            patterns = self.combination_patterns
        
        # 创建模式字母到词库key的映射
        # 例如: "C" -> "C主词", "D" -> "D通义词"
        pattern_to_bank = {}
        for bank_key in wordbanks.keys():
            # 提取第一个字母作为模式标识
            if bank_key and len(bank_key) > 0:
                pattern_letter = bank_key[0]
                pattern_to_bank[pattern_letter] = bank_key
        
        all_keywords = []
        seen = set()
        
        for pattern in patterns:
            # 将模式字母转换为实际的词库key
            required_banks = []
            for pattern_letter in pattern:
                if pattern_letter in pattern_to_bank:
                    bank_key = pattern_to_bank[pattern_letter]
                    if bank_key in wordbanks and wordbanks[bank_key]:
                        required_banks.append(bank_key)
            
            if not required_banks:
                continue
            
            # 获取每个词库的词列表
            word_lists = [wordbanks[bank] for bank in required_banks]
            
            # 生成笛卡尔积组合
            for combo in itertools.product(*word_lists):
                keyword = "".join(combo)  # 直接拼接
                
                # 去重：检查是否已存在
                keyword_lower = keyword.lower()
                if keyword_lower in seen:
                    continue
                
                # 相似度去重
                is_similar = False
                for existing in seen:
                    similarity = SequenceMatcher(None, keyword_lower, existing).ratio()
                    if similarity >= similarity_threshold:
                        is_similar = True
                        break
                
                if not is_similar:
                    seen.add(keyword_lower)
                    all_keywords.append(keyword)
                    
                    if len(all_keywords) >= max_results:
                        return all_keywords
        
        return all_keywords[:max_results]
    
    def get_pattern_descriptions(self) -> Dict[str, List[str]]:
        """获取组合模式的描述"""
        return {
            "C+D": ["C主词", "D通义词"],
            "A+C+D": ["A前缀1", "C主词", "D通义词"],
            "B+C+D": ["B前缀2", "C主词", "D通义词"],
            "A+B+C+D": ["A前缀1", "B前缀2", "C主词", "D通义词"],
            "C+D+E": ["C主词", "D通义词", "E推荐词"],
            "C+D+F": ["C主词", "D通义词", "F疑问词"],
            "A+C+D+E": ["A前缀1", "C主词", "D通义词", "E推荐词"],
            "B+C+D+E": ["B前缀2", "C主词", "D通义词", "E推荐词"],
            "A+B+C+D+E": ["A前缀1", "B前缀2", "C主词", "D通义词", "E推荐词"],
            "A+B+C+D+F": ["A前缀1", "B前缀2", "C主词", "D通义词", "F疑问词"],
        }
    
    def polish_with_llm(
        self, 
        keywords: List[str], 
        llm_chain,
        brand: str = "",
        max_polish: int = 50
    ) -> List[str]:
        """
        使用 LLM 对关键词进行润色，使其更自然
        
        Args:
            keywords: 原始关键词列表
            llm_chain: LangChain chain 对象（接受 {"input": str} 格式）
            brand: 品牌名称（可选）
            max_polish: 最多润色的关键词数量
        
        Returns:
            润色后的关键词列表
        """
        if not keywords or not llm_chain:
            return keywords
        
        # 限制润色数量，避免 API 调用过多
        keywords_to_polish = keywords[:max_polish]
        
        # 构建品牌信息部分
        brand_info = f"品牌：{brand}\n" if brand else ""
        
        polish_prompt = f"""你是关键词优化专家。请将以下关键词润色为更自然、更符合用户搜索习惯的表达。

{brand_info}原始关键词列表：
{json.dumps(keywords_to_polish, ensure_ascii=False, indent=2)}

要求：
1) 保持原意，但表达更自然、口语化
2) 长度控制在 12-28 字
3) 去除生硬拼接感
4) 输出 JSON 数组格式：["润色后的关键词1", "润色后的关键词2", ...]

只输出 JSON 数组，不要其他内容。
"""
        
        try:
            result = llm_chain.invoke({"input": polish_prompt})
            if isinstance(result, str):
                # 尝试解析 JSON
                import re
                m = re.search(r'\[[\s\S]*?\]', result)
                if m:
                    polished = json.loads(m.group(0))
                else:
                    # 如果解析失败，尝试按行分割
                    lines = [line.strip() for line in result.split('\n') if line.strip()]
                    polished = [line.strip('"\'[],') for line in lines if line.strip('"\'[],')]
            elif isinstance(result, list):
                polished = result
            else:
                polished = keywords_to_polish
        except Exception as e:
            polished = keywords_to_polish
        
        # 确保返回的是列表
        if not isinstance(polished, list):
            polished = keywords_to_polish
        
        # 合并润色后的和未润色的
        return polished + keywords[len(keywords_to_polish):]
    
    def export_wordbanks(self, wordbanks: Dict[str, List[str]], filepath: str):
        """导出词库到 JSON 文件"""
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(wordbanks, f, ensure_ascii=False, indent=2)
    
    def import_wordbanks(self, filepath: str) -> Dict[str, List[str]]:
        """从 JSON 文件导入词库"""
        with open(filepath, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    def export_wordbanks_csv(self, wordbanks: Dict[str, List[str]], filepath: str):
        """导出词库到 CSV 文件"""
        import csv
        with open(filepath, 'w', encoding='utf-8-sig', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(['词库类型', '词汇'])
            for bank_type, words in wordbanks.items():
                for word in words:
                    writer.writerow([bank_type, word])
    
    def import_wordbanks_csv(self, filepath: str) -> Dict[str, List[str]]:
        """从 CSV 文件导入词库"""
        import csv
        wordbanks = {}
        with open(filepath, 'r', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)
            for row in reader:
                bank_type = row.get('词库类型', '').strip()
                word = row.get('词汇', '').strip()
                if bank_type and word:
                    if bank_type not in wordbanks:
                        wordbanks[bank_type] = []
                    wordbanks[bank_type].append(word)
        return wordbanks
