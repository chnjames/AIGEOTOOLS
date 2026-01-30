"""
内容质量指标分析模块
计算 Trust Density、Citation Share、Authority Score、Engagement Potential 等指标
"""
import re
from typing import Dict, List, Optional, Tuple
from collections import Counter


class ContentMetricsAnalyzer:
    """内容质量指标分析器"""
    
    def __init__(self):
        # 信任信号模式（来源占位、数据、案例等）
        self.trust_signal_patterns = [
            # 来源占位模式
            r'根据[^，。；：\n]{2,30}(?:报告|研究|数据|统计|调查|分析|标准|规范|文档|指南)',
            r'参考[^，。；：\n]{2,30}(?:报告|研究|数据|统计|调查|分析|标准|规范|文档|指南)',
            r'来自[^，。；：\n]{2,30}(?:报告|研究|数据|统计|调查|分析)',
            r'据[^，。；：\n]{2,30}(?:显示|表明|统计|调查|分析)',
            r'[^，。；：\n]{2,20}(?:报告|研究|数据|统计|调查)显示',
            r'[^，。；：\n]{2,20}(?:报告|研究|数据|统计|调查)表明',
            # 数据点模式
            r'\d+%',  # 百分比
            r'\d+\.\d+%',  # 小数百分比
            r'约\d+%',  # 约XX%
            r'超过\d+%',  # 超过XX%
            r'达到\d+%',  # 达到XX%
            r'\d+倍',  # XX倍
            r'\d+个',  # XX个
            r'\d+项',  # XX项
            r'\d+次',  # XX次
            r'\d+年',  # XX年（时间数据）
            r'\d+月',  # XX月
            # 案例模式
            r'案例[：:][^，。；\n]{5,100}',
            r'例如[^，。；\n]{5,100}',
            r'以[^，。；\n]{2,30}为例',
            r'某[^，。；\n]{2,20}(?:企业|公司|用户|项目|团队)',
            r'实际[^，。；\n]{2,30}(?:测试|应用|使用|经验)',
            r'使用[^，。；\n]{2,30}(?:发现|表明|显示)',
        ]
        
        # 结构化元素模式
        self.structure_patterns = [
            r'^#{1,6}\s+.+',  # Markdown 标题
            r'^\d+[\.、]\s+.+',  # 编号列表
            r'^[-*+]\s+.+',  # 无序列表
            r'^\s*[-*+]\s+.+',  # 缩进列表
            r'```[\s\S]*?```',  # 代码块
            r'`[^`]+`',  # 行内代码
            r'^\s*[Qq][：:].*',  # FAQ 问题
            r'^\s*[Aa][：:].*',  # FAQ 答案
            r'\|.*\|',  # 表格
            r'^>.*',  # 引用块
        ]
    
    def count_trust_signals(self, content: str) -> int:
        """
        统计信任信号数量
        
        Args:
            content: 内容文本
            
        Returns:
            信任信号数量
        """
        # 去重：如果同一个位置匹配多个模式，只算一次
        # 简化处理：使用集合去重匹配位置附近的一小段文本
        unique_matches = set()
        for pattern in self.trust_signal_patterns:
            for match in re.finditer(pattern, content, re.MULTILINE | re.IGNORECASE):
                pos_key = content[max(0, match.start() - 10): match.end() + 10]
                unique_matches.add(pos_key)
        
        return len(unique_matches)
    
    def count_citations(self, content: str) -> int:
        """
        统计来源占位数量（Citation）
        
        Args:
            content: 内容文本
            
        Returns:
            来源占位数量
        """
        citation_patterns = [
            r'根据[^，。；：\n]{2,30}(?:报告|研究|数据|统计|调查|分析|标准|规范|文档|指南)',
            r'参考[^，。；：\n]{2,30}(?:报告|研究|数据|统计|调查|分析|标准|规范|文档|指南)',
            r'来自[^，。；：\n]{2,30}(?:报告|研究|数据|统计|调查|分析)',
            r'据[^，。；：\n]{2,30}(?:显示|表明|统计|调查|分析)',
            r'[^，。；：\n]{2,20}(?:报告|研究|数据|统计|调查)(?:显示|表明)',
        ]
        
        citations = set()
        for pattern in citation_patterns:
            for match in re.finditer(pattern, content, re.MULTILINE | re.IGNORECASE):
                # 使用匹配位置作为唯一标识
                pos_key = (match.start(), match.end())
                citations.add(pos_key)
        
        return len(citations)
    
    def count_brand_mentions(self, content: str, brand: str) -> int:
        """
        统计品牌提及次数
        
        Args:
            content: 内容文本
            brand: 品牌名称
            
        Returns:
            品牌提及次数
        """
        if not brand:
            return 0
        
        # 使用单词边界匹配，避免部分匹配
        pattern = r'\b' + re.escape(brand) + r'\b'
        matches = re.findall(pattern, content, re.IGNORECASE)
        return len(matches)
    
    def count_structure_elements(self, content: str) -> Dict[str, int]:
        """
        统计结构化元素数量
        
        Args:
            content: 内容文本
            
        Returns:
            结构化元素统计字典
        """
        lines = content.split('\n')
        structure_count = {
            'headings': 0,  # 标题
            'lists': 0,  # 列表
            'code_blocks': 0,  # 代码块
            'faq_pairs': 0,  # FAQ 对
            'tables': 0,  # 表格
            'quotes': 0,  # 引用
        }
        
        # 统计标题
        for line in lines:
            if re.match(r'^#{1,6}\s+.+', line):
                structure_count['headings'] += 1
            elif re.match(r'^\d+[\.、]\s+.+', line) or re.match(r'^[-*+]\s+.+', line):
                structure_count['lists'] += 1
            elif re.match(r'^\s*[Qq][：:].*', line):
                structure_count['faq_pairs'] += 1
            elif re.match(r'^\s*\|.*\|', line):
                structure_count['tables'] += 1
            elif re.match(r'^>.*', line):
                structure_count['quotes'] += 1
        
        # 统计代码块
        code_blocks = re.findall(r'```[\s\S]*?```', content)
        structure_count['code_blocks'] = len(code_blocks)
        
        return structure_count
    
    def calculate_trust_density(self, content: str) -> float:
        """
        计算 Trust Density（每100字信任信号数）
        
        Args:
            content: 内容文本
            
        Returns:
            Trust Density 值
        """
        if not content:
            return 0.0
        
        # 计算实际文本长度（去除空白字符）
        text_length = len(re.sub(r'\s+', '', content))
        if text_length == 0:
            return 0.0
        
        trust_signals = self.count_trust_signals(content)
        # 每100字信任信号数
        trust_density = (trust_signals / text_length) * 100
        
        return round(trust_density, 2)
    
    def calculate_citation_share(self, content: str, brand: str) -> float:
        """
        计算 Citation Share（品牌引用比例）
        
        Args:
            content: 内容文本
            brand: 品牌名称
            
        Returns:
            Citation Share 值（0-100）
        """
        if not content or not brand:
            return 0.0
        
        brand_mentions = self.count_brand_mentions(content, brand)
        
        # 统计所有可能的提及（品牌、竞品、通用术语等）
        # 简化处理：统计所有可能的品牌/产品提及
        # 使用常见品牌提及模式
        all_mentions_pattern = r'\b[A-Z][a-zA-Z0-9]{2,20}\b'  # 大写开头的单词（可能是品牌）
        all_mentions = len(re.findall(all_mentions_pattern, content))
        
        # 如果总提及数太少，使用品牌提及次数作为分母
        if all_mentions < brand_mentions * 2:
            all_mentions = brand_mentions * 2
        
        if all_mentions == 0:
            return 0.0
        
        citation_share = (brand_mentions / all_mentions) * 100
        return round(min(citation_share, 100.0), 2)
    
    def calculate_authority_score(self, content: str) -> float:
        """
        计算 Authority Score（权威性得分，0-100）
        
        基于来源占位数量、数据密度等
        
        Args:
            content: 内容文本
            
        Returns:
            Authority Score 值（0-100）
        """
        if not content:
            return 0.0
        
        citations = self.count_citations(content)
        trust_signals = self.count_trust_signals(content)
        text_length = len(re.sub(r'\s+', '', content))
        
        if text_length == 0:
            return 0.0
        
        # 计算各项得分
        # 来源占位得分（最多30分）
        citation_score = min(citations * 5, 30)
        
        # 信任信号密度得分（最多40分）
        trust_density = (trust_signals / text_length) * 1000  # 每1000字信任信号数
        trust_score = min(trust_density * 4, 40)
        
        # 数据点得分（最多30分）
        data_points = len(re.findall(r'\d+%', content)) + len(re.findall(r'\d+\.\d+%', content))
        data_score = min(data_points * 2, 30)
        
        authority_score = citation_score + trust_score + data_score
        return round(min(authority_score, 100.0), 2)
    
    def calculate_engagement_potential(self, content: str) -> float:
        """
        计算 Engagement Potential（参与度潜力，0-100）
        
        基于结构化程度、互动元素等
        
        Args:
            content: 内容文本
            
        Returns:
            Engagement Potential 值（0-100）
        """
        if not content:
            return 0.0
        
        structure = self.count_structure_elements(content)
        text_length = len(re.sub(r'\s+', '', content))
        
        if text_length == 0:
            return 0.0
        
        # 计算各项得分
        # 标题得分（最多20分）
        heading_score = min(structure['headings'] * 2, 20)
        
        # 列表得分（最多25分）
        list_score = min(structure['lists'] * 1.5, 25)
        
        # FAQ 得分（最多25分）
        faq_score = min(structure['faq_pairs'] * 3, 25)
        
        # 代码块得分（最多15分）
        code_score = min(structure['code_blocks'] * 5, 15)
        
        # 表格得分（最多10分）
        table_score = min(structure['tables'] * 2, 10)
        
        # 引用得分（最多5分）
        quote_score = min(structure['quotes'] * 1, 5)
        
        engagement_score = heading_score + list_score + faq_score + code_score + table_score + quote_score
        return round(min(engagement_score, 100.0), 2)
    
    def analyze_content(self, content: str, brand: str) -> Dict[str, any]:
        """
        综合分析内容，返回所有指标
        
        Args:
            content: 内容文本
            brand: 品牌名称
            
        Returns:
            包含所有指标的字典
        """
        if not content:
            return {
                'trust_density': 0.0,
                'citation_share': 0.0,
                'authority_score': 0.0,
                'engagement_potential': 0.0,
                'trust_signals': 0,
                'citations': 0,
                'brand_mentions': 0,
                'structure_elements': {},
                'text_length': 0,
            }
        
        text_length = len(re.sub(r'\s+', '', content))
        trust_signals = self.count_trust_signals(content)
        citations = self.count_citations(content)
        brand_mentions = self.count_brand_mentions(content, brand)
        structure = self.count_structure_elements(content)
        
        return {
            'trust_density': self.calculate_trust_density(content),
            'citation_share': self.calculate_citation_share(content, brand),
            'authority_score': self.calculate_authority_score(content),
            'engagement_potential': self.calculate_engagement_potential(content),
            'trust_signals': trust_signals,
            'citations': citations,
            'brand_mentions': brand_mentions,
            'structure_elements': structure,
            'text_length': text_length,
        }
    
    def analyze_batch(self, contents: List[Dict[str, str]], brand: str) -> List[Dict[str, any]]:
        """
        批量分析内容
        
        Args:
            contents: 内容列表，每个元素包含 'content' 字段
            brand: 品牌名称
            
        Returns:
            分析结果列表
        """
        results = []
        for item in contents:
            content = item.get('content', '')
            metrics = self.analyze_content(content, brand)
            # 保留原始数据
            metrics['keyword'] = item.get('keyword', '')
            metrics['platform'] = item.get('platform', '')
            results.append(metrics)
        
        return results
    
    def get_metrics_summary(self, results: List[Dict[str, any]]) -> Dict[str, any]:
        """
        获取指标汇总统计
        
        Args:
            results: 分析结果列表
            
        Returns:
            汇总统计字典
        """
        if not results:
            return {
                'avg_trust_density': 0.0,
                'avg_citation_share': 0.0,
                'avg_authority_score': 0.0,
                'avg_engagement_potential': 0.0,
                'total_trust_signals': 0,
                'total_citations': 0,
                'total_brand_mentions': 0,
                'count': 0,
            }
        
        return {
            'avg_trust_density': round(sum(r.get('trust_density', 0) for r in results) / len(results), 2),
            'avg_citation_share': round(sum(r.get('citation_share', 0) for r in results) / len(results), 2),
            'avg_authority_score': round(sum(r.get('authority_score', 0) for r in results) / len(results), 2),
            'avg_engagement_potential': round(sum(r.get('engagement_potential', 0) for r in results) / len(results), 2),
            'total_trust_signals': sum(r.get('trust_signals', 0) for r in results),
            'total_citations': sum(r.get('citations', 0) for r in results),
            'total_brand_mentions': sum(r.get('brand_mentions', 0) for r in results),
            'count': len(results),
        }
