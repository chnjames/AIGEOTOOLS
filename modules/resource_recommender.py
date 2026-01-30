"""
GEO 资源推荐模块
提供 GEO 代理、工具、论文等资源推荐，增强工具生态
"""
from typing import List, Dict, Optional
from datetime import datetime


class ResourceRecommender:
    """GEO 资源推荐器"""
    
    def __init__(self):
        # GEO 代理列表
        self.agents = [
            {
                "name": "KrillinAI",
                "description": "专业的 GEO 代理服务，提供高质量的内容生成和优化",
                "url": "https://krillin.ai",
                "category": "代理服务",
                "rating": "⭐⭐⭐⭐⭐",
                "features": ["内容生成", "SEO 优化", "多平台支持"]
            },
            {
                "name": "AutoGPT",
                "description": "自动化 AI 代理，支持 GEO 内容创作",
                "url": "https://autogpt.net",
                "category": "代理服务",
                "rating": "⭐⭐⭐⭐",
                "features": ["自动化", "多任务", "API 集成"]
            },
            {
                "name": "AgentGPT",
                "description": "基于 GPT 的智能代理，支持 GEO 策略执行",
                "url": "https://agentgpt.reworkd.ai",
                "category": "代理服务",
                "rating": "⭐⭐⭐⭐",
                "features": ["策略规划", "任务执行", "结果分析"]
            }
        ]
        
        # 工具推荐
        self.tools = [
            {
                "name": "Google Search Console",
                "description": "监控网站搜索表现，优化 GEO 效果",
                "url": "https://search.google.com/search-console",
                "category": "SEO 工具",
                "rating": "⭐⭐⭐⭐⭐",
                "features": ["搜索分析", "索引监控", "性能报告"]
            },
            {
                "name": "Bing Webmaster Tools",
                "description": "Bing 搜索引擎的网站管理工具",
                "url": "https://www.bing.com/webmasters",
                "category": "SEO 工具",
                "rating": "⭐⭐⭐⭐",
                "features": ["索引提交", "搜索分析", "URL 检查"]
            },
            {
                "name": "Schema.org Validator",
                "description": "验证 JSON-LD Schema 标记",
                "url": "https://validator.schema.org",
                "category": "技术工具",
                "rating": "⭐⭐⭐⭐⭐",
                "features": ["Schema 验证", "结构化数据测试", "错误检测"]
            },
            {
                "name": "Rich Results Test",
                "description": "Google 富媒体结果测试工具",
                "url": "https://search.google.com/test/rich-results",
                "category": "技术工具",
                "rating": "⭐⭐⭐⭐⭐",
                "features": ["富媒体测试", "预览效果", "错误诊断"]
            },
            {
                "name": "PageSpeed Insights",
                "description": "网站性能分析工具，影响 GEO 排名",
                "url": "https://pagespeed.web.dev",
                "category": "性能工具",
                "rating": "⭐⭐⭐⭐⭐",
                "features": ["性能分析", "优化建议", "移动端测试"]
            }
        ]
        
        # 论文/指南链接
        self.papers = [
            {
                "title": "Google E-E-A-T Guidelines",
                "description": "Google 官方 E-E-A-T 指南，GEO 核心原则",
                "url": "https://developers.google.com/search/docs/fundamentals/creating-helpful-content",
                "category": "官方指南",
                "date": "2023",
                "importance": "高"
            },
            {
                "title": "Schema.org Documentation",
                "description": "Schema.org 结构化数据完整文档",
                "url": "https://schema.org",
                "category": "技术文档",
                "date": "持续更新",
                "importance": "高"
            },
            {
                "title": "GEO Strategy Guide",
                "description": "GEO（Generative Engine Optimization）策略指南",
                "url": "https://github.com/mprimi/portable-seed",
                "category": "策略指南",
                "date": "2024",
                "importance": "高"
            },
            {
                "title": "AI Search Optimization",
                "description": "AI 搜索引擎优化最佳实践",
                "url": "https://www.searchenginejournal.com/ai-search-optimization",
                "category": "最佳实践",
                "date": "2024",
                "importance": "中"
            },
            {
                "title": "LLM Prompt Engineering",
                "description": "大语言模型提示工程指南",
                "url": "https://www.promptingguide.ai",
                "category": "技术指南",
                "date": "持续更新",
                "importance": "中"
            }
        ]
        
        # 社区资源
        self.communities = [
            {
                "name": "GEO Reddit Community",
                "description": "GEO 相关讨论和经验分享",
                "url": "https://www.reddit.com/r/SEO",
                "category": "社区论坛",
                "rating": "⭐⭐⭐⭐"
            },
            {
                "name": "AI SEO Discord",
                "description": "AI SEO 和 GEO 技术交流社区",
                "url": "https://discord.gg/ai-seo",
                "category": "社区论坛",
                "rating": "⭐⭐⭐⭐"
            }
        ]
    
    def get_agents(self, category: Optional[str] = None) -> List[Dict]:
        """
        获取 GEO 代理列表
        
        Args:
            category: 分类筛选（可选）
            
        Returns:
            代理列表
        """
        if category:
            return [agent for agent in self.agents if agent.get("category") == category]
        return self.agents
    
    def get_tools(self, category: Optional[str] = None) -> List[Dict]:
        """
        获取工具推荐列表
        
        Args:
            category: 分类筛选（可选）
            
        Returns:
            工具列表
        """
        if category:
            return [tool for tool in self.tools if tool.get("category") == category]
        return self.tools
    
    def get_papers(self, category: Optional[str] = None, importance: Optional[str] = None) -> List[Dict]:
        """
        获取论文/指南列表
        
        Args:
            category: 分类筛选（可选）
            importance: 重要性筛选（可选：高、中、低）
            
        Returns:
            论文/指南列表
        """
        result = self.papers
        if category:
            result = [p for p in result if p.get("category") == category]
        if importance:
            result = [p for p in result if p.get("importance") == importance]
        return result
    
    def get_communities(self) -> List[Dict]:
        """
        获取社区资源列表
        
        Returns:
            社区列表
        """
        return self.communities
    
    def search_resources(self, query: str, resource_type: Optional[str] = None) -> List[Dict]:
        """
        搜索资源（简单文本匹配）
        
        Args:
            query: 搜索关键词
            resource_type: 资源类型（agents, tools, papers, communities）
            
        Returns:
            匹配的资源列表
        """
        query_lower = query.lower()
        results = []
        
        if resource_type is None or resource_type == "agents":
            for agent in self.agents:
                if (query_lower in agent["name"].lower() or 
                    query_lower in agent["description"].lower() or
                    any(query_lower in f.lower() for f in agent.get("features", []))):
                    results.append({**agent, "type": "agent"})
        
        if resource_type is None or resource_type == "tools":
            for tool in self.tools:
                if (query_lower in tool["name"].lower() or 
                    query_lower in tool["description"].lower() or
                    any(query_lower in f.lower() for f in tool.get("features", []))):
                    results.append({**tool, "type": "tool"})
        
        if resource_type is None or resource_type == "papers":
            for paper in self.papers:
                if (query_lower in paper["title"].lower() or 
                    query_lower in paper["description"].lower()):
                    results.append({**paper, "type": "paper"})
        
        if resource_type is None or resource_type == "communities":
            for community in self.communities:
                if (query_lower in community["name"].lower() or 
                    query_lower in community["description"].lower()):
                    results.append({**community, "type": "community"})
        
        return results
    
    def get_categories(self) -> Dict[str, List[str]]:
        """
        获取所有分类
        
        Returns:
            分类字典
        """
        return {
            "agents": list(set(agent["category"] for agent in self.agents)),
            "tools": list(set(tool["category"] for tool in self.tools)),
            "papers": list(set(paper["category"] for paper in self.papers)),
            "communities": list(set(community["category"] for community in self.communities))
        }
    
    def get_resource_summary(self) -> Dict[str, int]:
        """
        获取资源统计摘要
        
        Returns:
            统计字典
        """
        return {
            "agents": len(self.agents),
            "tools": len(self.tools),
            "papers": len(self.papers),
            "communities": len(self.communities),
            "total": len(self.agents) + len(self.tools) + len(self.papers) + len(self.communities)
        }
