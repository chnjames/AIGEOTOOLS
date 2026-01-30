"""
话题集群生成模块
基于关键词进行语义聚类，生成话题集群，分析话题关联，提供内容规划建议
"""
from typing import List, Dict, Set, Optional, Tuple
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import StrOutputParser
import json
import re
from collections import defaultdict
from difflib import SequenceMatcher
import math


class TopicCluster:
    """话题集群生成器"""
    
    def __init__(self):
        # 话题聚类 Prompt
        self.clustering_prompt_template = """
你是话题聚类专家，专门将关键词聚类为话题集群，帮助用户系统化规划内容策略。

【关键词列表】
{keywords}

【品牌】{brand}
【优势】{advantages}
【聚类数量】{cluster_count}（建议范围：3-10个话题集群）

【话题聚类要求】

1. **语义相似性**
   - 将语义相似的关键词归为同一话题集群
   - 每个话题集群应该围绕一个核心主题
   - 话题之间应该有明显的区分度

2. **话题命名**
   - 为每个话题集群生成一个简洁、有代表性的名称（2-8字）
   - 话题名称应该能概括该集群的核心主题
   - 使用用户容易理解的语言

3. **话题描述**
   - 为每个话题集群生成一段描述（20-50字）
   - 说明该话题的核心内容和价值

4. **关键词分配**
   - 每个关键词应该只属于一个话题集群
   - 如果关键词可以属于多个话题，选择最相关的一个
   - 确保所有关键词都被分配

5. **话题关联**
   - 识别话题之间的关联关系
   - 标记强关联（直接相关）和弱关联（间接相关）

【输出格式】
请严格按照以下 JSON 格式输出，不要添加任何其他内容：

{{
  "clusters": [
    {{
      "id": 1,
      "name": "<话题名称>",
      "description": "<话题描述>",
      "keywords": ["<关键词1>", "<关键词2>", ...],
      "keyword_count": <关键词数量>,
      "priority": "<优先级：高/中/低>"
    }},
    ...
  ],
  "relationships": [
    {{
      "from": <话题ID>,
      "to": <话题ID>,
      "strength": "<关联强度：强/弱>",
      "type": "<关联类型：功能相关/场景相关/用户相关等>"
    }},
    ...
  ],
  "cluster_stats": {{
    "total_clusters": <话题总数>,
    "total_keywords": <关键词总数>,
    "avg_keywords_per_cluster": <平均每个话题的关键词数量>,
    "max_keywords": <最大话题的关键词数量>,
    "min_keywords": <最小话题的关键词数量>
  }}
}}

【开始聚类】
"""
        
        # 内容规划 Prompt
        self.content_planning_prompt_template = """
你是内容策略专家，基于话题集群生成内容规划建议。

【话题集群】
{clusters}

【品牌】{brand}
【优势】{advantages}

【内容规划要求】

1. **内容盲区分析**
   - 识别哪些话题集群缺少内容
   - 分析话题覆盖的完整性
   - 发现内容空白点

2. **内容优先级**
   - 根据话题的重要性和覆盖度，给出内容创作优先级
   - 优先覆盖高价值、低覆盖的话题

3. **内容建议**
   - 为每个话题集群提供内容创作建议
   - 包括：内容类型、发布平台、关键词策略等

4. **内容矩阵**
   - 建议话题之间的内容关联策略
   - 如何通过内容矩阵提升整体覆盖面

【输出格式】
请严格按照以下 JSON 格式输出，不要添加任何其他内容：

{{
  "content_gaps": [
    {{
      "cluster_id": <话题ID>,
      "cluster_name": "<话题名称>",
      "gap_type": "<盲区类型：完全空白/内容不足/关联缺失>",
      "description": "<盲区描述>",
      "priority": "<优先级：高/中/低>"
    }},
    ...
  ],
  "content_priorities": [
    {{
      "cluster_id": <话题ID>,
      "cluster_name": "<话题名称>",
      "priority": "<优先级：高/中/低>",
      "reason": "<优先级原因>",
      "recommended_content_count": <建议内容数量>
    }},
    ...
  ],
  "content_suggestions": [
    {{
      "cluster_id": <话题ID>,
      "cluster_name": "<话题名称>",
      "content_types": ["<内容类型1>", "<内容类型2>", ...],
      "platforms": ["<平台1>", "<平台2>", ...],
      "keyword_strategy": "<关键词策略>",
      "content_ideas": ["<内容创意1>", "<内容创意2>", ...]
    }},
    ...
  ],
  "content_matrix": {{
    "strategy": "<内容矩阵策略描述>",
    "cross_cluster_opportunities": [
      {{
        "clusters": ["<话题1>", "<话题2>"],
        "opportunity": "<关联机会描述>",
        "content_type": "<建议内容类型>"
      }},
      ...
    ]
  }}
}}

【开始规划】
"""
    
    def cluster_keywords(
        self,
        keywords: List[str],
        brand: str,
        advantages: str,
        cluster_count: int,
        llm_chain
    ) -> Dict:
        """
        将关键词聚类为话题集群
        
        Args:
            keywords: 关键词列表
            brand: 品牌名称
            advantages: 品牌优势
            cluster_count: 期望的话题集群数量（3-10）
            llm_chain: LangChain 链对象
            
        Returns:
            包含话题集群、关联关系和统计信息的字典
        """
        if not keywords:
            return {
                "clusters": [],
                "relationships": [],
                "cluster_stats": {
                    "total_clusters": 0,
                    "total_keywords": 0,
                    "avg_keywords_per_cluster": 0,
                    "max_keywords": 0,
                    "min_keywords": 0
                }
            }
        
        # 限制关键词数量，避免 Prompt 过长
        keywords_to_cluster = keywords[:100]  # 最多处理100个关键词
        
        # 限制聚类数量在合理范围
        cluster_count = max(3, min(10, cluster_count))
        
        try:
            prompt = PromptTemplate.from_template(self.clustering_prompt_template)
            chain = prompt | llm_chain | StrOutputParser()
            
            result = chain.invoke({
                "keywords": json.dumps(keywords_to_cluster, ensure_ascii=False, indent=2),
                "brand": brand,
                "advantages": advantages,
                "cluster_count": cluster_count
            })
            
            # 解析结果
            cluster_data = self._parse_clustering_result(result, keywords_to_cluster)
            
            return cluster_data
            
        except Exception as e:
            # 如果聚类失败，返回基于规则的简单聚类
            return self._rule_based_clustering(keywords_to_cluster, cluster_count)
    
    def _parse_clustering_result(self, result: str, original_keywords: List[str]) -> Dict:
        """解析聚类结果"""
        # 尝试提取 JSON
        json_match = re.search(r'\{.*\}', result, re.DOTALL)
        if json_match:
            try:
                data = json.loads(json_match.group())
                # 验证数据结构
                if "clusters" in data:
                    # 验证和清理数据
                    data = self._validate_cluster_data(data, original_keywords)
                    return data
            except json.JSONDecodeError:
                pass
        
        # 如果无法解析 JSON，使用基于规则的聚类
        return self._rule_based_clustering(original_keywords, min(5, len(original_keywords) // 5))
    
    def _validate_cluster_data(self, data: Dict, original_keywords: List[str]) -> Dict:
        """验证和清理聚类数据"""
        if "clusters" not in data:
            return self._rule_based_clustering(original_keywords, 5)
        
        clusters = data.get("clusters", [])
        validated_clusters = []
        assigned_keywords = set()
        
        # 验证每个集群
        for cluster in clusters:
            if not isinstance(cluster, dict):
                continue
            
            cluster_id = cluster.get("id")
            name = cluster.get("name", "").strip()
            keywords = cluster.get("keywords", [])
            
            if not name or not keywords:
                continue
            
            # 过滤无效关键词
            valid_keywords = []
            for kw in keywords:
                if isinstance(kw, str) and kw.strip() and kw.strip() in original_keywords:
                    kw_clean = kw.strip()
                    if kw_clean not in assigned_keywords:
                        valid_keywords.append(kw_clean)
                        assigned_keywords.add(kw_clean)
            
            if valid_keywords:
                validated_clusters.append({
                    "id": cluster_id if cluster_id else len(validated_clusters) + 1,
                    "name": name,
                    "description": cluster.get("description", ""),
                    "keywords": valid_keywords,
                    "keyword_count": len(valid_keywords),
                    "priority": cluster.get("priority", "中")
                })
        
        # 分配未分配的关键词到最近的集群
        unassigned = [kw for kw in original_keywords if kw not in assigned_keywords]
        if unassigned and validated_clusters:
            for kw in unassigned:
                # 找到最相似的集群
                best_cluster = None
                best_similarity = 0
                for cluster in validated_clusters:
                    # 计算与集群关键词的平均相似度
                    similarities = [
                        SequenceMatcher(None, kw.lower(), ckw.lower()).ratio()
                        for ckw in cluster["keywords"][:5]  # 只比较前5个
                    ]
                    avg_sim = sum(similarities) / len(similarities) if similarities else 0
                    if avg_sim > best_similarity:
                        best_similarity = avg_sim
                        best_cluster = cluster
                
                if best_cluster and best_similarity > 0.3:
                    best_cluster["keywords"].append(kw)
                    best_cluster["keyword_count"] = len(best_cluster["keywords"])
        
        # 更新统计信息
        total_keywords = sum(c["keyword_count"] for c in validated_clusters)
        cluster_counts = [c["keyword_count"] for c in validated_clusters]
        
        data["clusters"] = validated_clusters
        data["cluster_stats"] = {
            "total_clusters": len(validated_clusters),
            "total_keywords": total_keywords,
            "avg_keywords_per_cluster": total_keywords / len(validated_clusters) if validated_clusters else 0,
            "max_keywords": max(cluster_counts) if cluster_counts else 0,
            "min_keywords": min(cluster_counts) if cluster_counts else 0
        }
        
        # 验证关联关系
        if "relationships" in data:
            relationships = []
            cluster_ids = {c["id"] for c in validated_clusters}
            for rel in data["relationships"]:
                if isinstance(rel, dict):
                    from_id = rel.get("from")
                    to_id = rel.get("to")
                    if from_id in cluster_ids and to_id in cluster_ids and from_id != to_id:
                        relationships.append(rel)
            data["relationships"] = relationships
        
        return data
    
    def _rule_based_clustering(
        self,
        keywords: List[str],
        target_clusters: int
    ) -> Dict:
        """
        基于规则的简单聚类（备用方案，不依赖 LLM）
        
        Args:
            keywords: 关键词列表
            target_clusters: 目标集群数量
            
        Returns:
            聚类结果字典
        """
        if not keywords:
            return {
                "clusters": [],
                "relationships": [],
                "cluster_stats": {
                    "total_clusters": 0,
                    "total_keywords": 0,
                    "avg_keywords_per_cluster": 0,
                    "max_keywords": 0,
                    "min_keywords": 0
                }
            }
        
        # 简单的基于关键词相似度的聚类
        clusters = []
        remaining_keywords = keywords.copy()
        
        # 计算关键词之间的相似度矩阵
        similarity_matrix = {}
        for i, kw1 in enumerate(keywords):
            for j, kw2 in enumerate(keywords[i+1:], i+1):
                sim = SequenceMatcher(None, kw1.lower(), kw2.lower()).ratio()
                similarity_matrix[(i, j)] = sim
        
        # 简单的聚类算法：找到相似度高的关键词组
        used_indices = set()
        cluster_id = 1
        
        # 按相似度排序
        sorted_pairs = sorted(similarity_matrix.items(), key=lambda x: x[1], reverse=True)
        
        for (i, j), sim in sorted_pairs:
            if i in used_indices or j in used_indices:
                continue
            
            if sim > 0.5:  # 相似度阈值
                # 创建新集群
                cluster_keywords = [keywords[i], keywords[j]]
                used_indices.add(i)
                used_indices.add(j)
                
                # 尝试添加其他相似的关键词
                for k, kw in enumerate(keywords):
                    if k in used_indices or k == i or k == j:
                        continue
                    
                    # 计算与集群的平均相似度
                    avg_sim = (sim + SequenceMatcher(None, kw.lower(), keywords[i].lower()).ratio() + 
                              SequenceMatcher(None, kw.lower(), keywords[j].lower()).ratio()) / 3
                    
                    if avg_sim > 0.4:
                        cluster_keywords.append(kw)
                        used_indices.add(k)
                
                # 生成集群名称（使用第一个关键词的主要部分）
                cluster_name = self._extract_topic_name(cluster_keywords[0])
                
                clusters.append({
                    "id": cluster_id,
                    "name": cluster_name,
                    "description": f"包含 {len(cluster_keywords)} 个相关关键词",
                    "keywords": cluster_keywords,
                    "keyword_count": len(cluster_keywords),
                    "priority": "中"
                })
                cluster_id += 1
                
                if len(clusters) >= target_clusters:
                    break
        
        # 分配剩余关键词到最近的集群
        for i, kw in enumerate(keywords):
            if i not in used_indices:
                if clusters:
                    # 找到最相似的集群
                    best_cluster = None
                    best_sim = 0
                    for cluster in clusters:
                        avg_sim = sum(
                            SequenceMatcher(None, kw.lower(), ckw.lower()).ratio()
                            for ckw in cluster["keywords"][:3]
                        ) / min(3, len(cluster["keywords"]))
                        if avg_sim > best_sim:
                            best_sim = avg_sim
                            best_cluster = cluster
                    
                    if best_cluster and best_sim > 0.2:
                        best_cluster["keywords"].append(kw)
                        best_cluster["keyword_count"] = len(best_cluster["keywords"])
                    else:
                        # 创建新集群
                        clusters.append({
                            "id": cluster_id,
                            "name": self._extract_topic_name(kw),
                            "description": f"包含 1 个关键词",
                            "keywords": [kw],
                            "keyword_count": 1,
                            "priority": "低"
                        })
                        cluster_id += 1
                else:
                    # 创建第一个集群
                    clusters.append({
                        "id": cluster_id,
                        "name": self._extract_topic_name(kw),
                        "description": f"包含 1 个关键词",
                        "keywords": [kw],
                        "keyword_count": 1,
                        "priority": "中"
                    })
                    cluster_id += 1
        
        # 生成简单的关联关系
        relationships = []
        for i, cluster1 in enumerate(clusters):
            for j, cluster2 in enumerate(clusters[i+1:], i+1):
                # 计算集群之间的相似度
                similarities = [
                    SequenceMatcher(None, kw1.lower(), kw2.lower()).ratio()
                    for kw1 in cluster1["keywords"][:3]
                    for kw2 in cluster2["keywords"][:3]
                ]
                avg_sim = sum(similarities) / len(similarities) if similarities else 0
                
                if avg_sim > 0.3:
                    relationships.append({
                        "from": cluster1["id"],
                        "to": cluster2["id"],
                        "strength": "强" if avg_sim > 0.5 else "弱",
                        "type": "语义相关"
                    })
        
        # 计算统计信息
        total_keywords = sum(c["keyword_count"] for c in clusters)
        cluster_counts = [c["keyword_count"] for c in clusters]
        
        return {
            "clusters": clusters,
            "relationships": relationships,
            "cluster_stats": {
                "total_clusters": len(clusters),
                "total_keywords": total_keywords,
                "avg_keywords_per_cluster": total_keywords / len(clusters) if clusters else 0,
                "max_keywords": max(cluster_counts) if cluster_counts else 0,
                "min_keywords": min(cluster_counts) if cluster_counts else 0
            }
        }
    
    def _extract_topic_name(self, keyword: str) -> str:
        """从关键词中提取话题名称"""
        # 简单的提取逻辑：取关键词的前几个字或核心词
        if len(keyword) <= 6:
            return keyword
        
        # 尝试提取核心词（去除常见修饰词）
        common_modifiers = ["的", "和", "与", "或", "及", "等", "如何", "怎么", "什么", "哪个", "哪家"]
        words = keyword
        for mod in common_modifiers:
            words = words.replace(mod, " ")
        
        words = words.split()
        if words:
            return words[0][:8] if len(words[0]) > 8 else words[0]
        
        return keyword[:8]
    
    def generate_content_planning(
        self,
        clusters: List[Dict],
        brand: str,
        advantages: str,
        llm_chain
    ) -> Dict:
        """
        基于话题集群生成内容规划建议
        
        Args:
            clusters: 话题集群列表
            brand: 品牌名称
            advantages: 品牌优势
            llm_chain: LangChain 链对象
            
        Returns:
            内容规划建议字典
        """
        if not clusters:
            return {
                "content_gaps": [],
                "content_priorities": [],
                "content_suggestions": [],
                "content_matrix": {
                    "strategy": "",
                    "cross_cluster_opportunities": []
                }
            }
        
        try:
            prompt = PromptTemplate.from_template(self.content_planning_prompt_template)
            chain = prompt | llm_chain | StrOutputParser()
            
            result = chain.invoke({
                "clusters": json.dumps(clusters, ensure_ascii=False, indent=2),
                "brand": brand,
                "advantages": advantages
            })
            
            # 解析结果
            planning_data = self._parse_planning_result(result)
            
            return planning_data
            
        except Exception as e:
            # 如果规划失败，返回基于规则的简单规划
            return self._rule_based_planning(clusters)
    
    def _parse_planning_result(self, result: str) -> Dict:
        """解析内容规划结果"""
        json_match = re.search(r'\{.*\}', result, re.DOTALL)
        if json_match:
            try:
                data = json.loads(json_match.group())
                # 验证数据结构
                if "content_gaps" in data or "content_priorities" in data:
                    return data
            except json.JSONDecodeError:
                pass
        
        # 如果无法解析，返回空结果
        return {
            "content_gaps": [],
            "content_priorities": [],
            "content_suggestions": [],
            "content_matrix": {
                "strategy": "",
                "cross_cluster_opportunities": []
            }
        }
    
    def _rule_based_planning(self, clusters: List[Dict]) -> Dict:
        """基于规则的简单内容规划（备用方案）"""
        content_gaps = []
        content_priorities = []
        content_suggestions = []
        
        for cluster in clusters:
            cluster_id = cluster.get("id")
            cluster_name = cluster.get("name", "")
            keyword_count = cluster.get("keyword_count", 0)
            
            # 根据关键词数量判断优先级
            if keyword_count >= 10:
                priority = "高"
            elif keyword_count >= 5:
                priority = "中"
            else:
                priority = "低"
            
            content_priorities.append({
                "cluster_id": cluster_id,
                "cluster_name": cluster_name,
                "priority": priority,
                "reason": f"包含 {keyword_count} 个关键词",
                "recommended_content_count": max(1, keyword_count // 3)
            })
            
            # 生成简单的内容建议
            content_suggestions.append({
                "cluster_id": cluster_id,
                "cluster_name": cluster_name,
                "content_types": ["文章", "指南", "案例"],
                "platforms": ["博客", "知乎", "小红书"],
                "keyword_strategy": f"围绕 {cluster_name} 主题创作内容",
                "content_ideas": [
                    f"{cluster_name} 完整指南",
                    f"{cluster_name} 最佳实践",
                    f"{cluster_name} 案例分析"
                ]
            })
        
        return {
            "content_gaps": content_gaps,
            "content_priorities": content_priorities,
            "content_suggestions": content_suggestions,
            "content_matrix": {
                "strategy": "建议围绕各话题集群系统化创作内容，建立完整的内容矩阵",
                "cross_cluster_opportunities": []
            }
        }
    
    def analyze_cluster_coverage(
        self,
        clusters: List[Dict],
        historical_keywords: List[str]
    ) -> Dict:
        """
        分析话题集群的覆盖情况
        
        Args:
            clusters: 话题集群列表
            historical_keywords: 历史关键词列表（用于分析覆盖度）
            
        Returns:
            覆盖分析结果
        """
        if not clusters:
            return {
                "coverage_ratio": 0.0,
                "cluster_distribution": {},
                "gaps": []
            }
        
        # 统计每个集群的关键词数量
        cluster_distribution = {
            cluster["name"]: cluster["keyword_count"]
            for cluster in clusters
        }
        
        # 计算覆盖比例（如果有历史关键词）
        coverage_ratio = 0.0
        if historical_keywords:
            cluster_keywords = set()
            for cluster in clusters:
                cluster_keywords.update(cluster.get("keywords", []))
            
            covered = len(cluster_keywords & set(historical_keywords))
            coverage_ratio = covered / len(historical_keywords) if historical_keywords else 0.0
        
        # 识别覆盖盲区（关键词数量少的集群）
        gaps = [
            {
                "cluster_name": cluster["name"],
                "keyword_count": cluster["keyword_count"],
                "priority": "高" if cluster["keyword_count"] < 3 else "中"
            }
            for cluster in clusters
            if cluster["keyword_count"] < 5
        ]
        
        return {
            "coverage_ratio": coverage_ratio,
            "cluster_distribution": cluster_distribution,
            "gaps": gaps
        }
    
    def get_visualization_data(
        self,
        clusters: List[Dict],
        relationships: List[Dict]
    ) -> Dict:
        """
        生成可视化数据（用于网络图和树状图）
        
        Args:
            clusters: 话题集群列表
            relationships: 关联关系列表
            
        Returns:
            可视化数据字典
        """
        # 节点数据（话题集群）
        nodes = [
            {
                "id": cluster["id"],
                "name": cluster["name"],
                "size": cluster["keyword_count"],
                "keywords": cluster["keywords"],
                "description": cluster.get("description", "")
            }
            for cluster in clusters
        ]
        
        # 边数据（关联关系）
        edges = [
            {
                "source": rel["from"],
                "target": rel["to"],
                "strength": rel.get("strength", "弱"),
                "type": rel.get("type", "相关")
            }
            for rel in relationships
        ]
        
        return {
            "nodes": nodes,
            "edges": edges
        }
