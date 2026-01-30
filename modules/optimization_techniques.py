"""
高级优化技巧选择器模块
支持多种优化技巧，动态调整 Prompt 生成策略
"""
from typing import List, Dict, Optional
from enum import Enum


class OptimizationTechnique(Enum):
    """优化技巧类型"""
    EVIDENCE_DRIVEN = "evidence_driven"  # 证据驱动
    CONVERSATIONAL = "conversational"  # 对话式设计
    STORYTELLING = "storytelling"  # 故事化叙述
    COMPARATIVE = "comparative"  # 对比式结构
    STEP_BY_STEP = "step_by_step"  # 步骤式指南
    DATA_RICH = "data_rich"  # 数据丰富
    CASE_STUDY = "case_study"  # 案例研究
    FAQ_FOCUSED = "faq_focused"  # FAQ 聚焦


class OptimizationTechniqueManager:
    """优化技巧管理器"""
    
    def __init__(self):
        # 定义所有优化技巧及其描述
        self.techniques = {
            OptimizationTechnique.EVIDENCE_DRIVEN.value: {
                "name": "证据驱动",
                "description": "添加数据、案例、来源等证据支撑，提升内容可信度",
                "icon": "📊",
                "prompt_addition": """
【证据驱动优化要求】
- 添加具体数据：在合适位置添加数据占位（如"根据XX数据显示，约XX%的用户"）
- 添加案例支撑：至少包含2-3个实际案例或应用场景（用占位符）
- 添加来源引用：标注数据来源、案例来源（如"根据XX行业报告"、"参考XX研究"）
- 添加对比数据：提供对比信息（如"相比传统方案，提升约XX%"）
- 确保每个主要观点都有证据支撑
"""
            },
            OptimizationTechnique.CONVERSATIONAL.value: {
                "name": "对话式设计",
                "description": "采用问答式、互动式结构，提升内容可读性和参与度",
                "icon": "💬",
                "prompt_addition": """
【对话式设计优化要求】
- 开头使用问题引入：用用户常见问题开头（如"你是否遇到过..."、"想知道如何..."）
- 采用问答结构：将内容组织为问答形式，至少包含5-8个问答对
- 使用第二人称：多用"你"、"您"，增强互动感
- 添加互动引导：在合适位置添加互动语句（如"试试看"、"不妨考虑"）
- 结尾设置问题：以开放性问题或思考题结尾，引导用户思考
"""
            },
            OptimizationTechnique.STORYTELLING.value: {
                "name": "故事化叙述",
                "description": "使用案例故事、用户故事，让内容更生动、更易记忆",
                "icon": "📖",
                "prompt_addition": """
【故事化叙述优化要求】
- 开头故事引入：用真实或典型的用户故事开头（用占位符，如"某企业案例"）
- 故事化案例：将案例包装成故事形式，包含背景、挑战、解决方案、结果
- 用户视角：从用户角度叙述，增强代入感
- 情感共鸣：在故事中加入情感元素（如"困扰"、"惊喜"、"成功"）
- 故事结构：使用经典故事结构（起承转合），让内容更有吸引力
"""
            },
            OptimizationTechnique.COMPARATIVE.value: {
                "name": "对比式结构",
                "description": "通过优势对比、功能对比，突出品牌优势",
                "icon": "⚖️",
                "prompt_addition": """
【对比式结构优化要求】
- 多维度对比：从功能、性能、价格、服务等多个维度对比
- 对比表格：使用表格或列表形式清晰展示对比（至少5个对比点）
- 优势突出：在对比中自然突出品牌优势，但保持客观
- 适用场景对比：说明不同方案的适用场景
- 选择建议：基于对比结果，提供选择建议和理由
"""
            },
            OptimizationTechnique.STEP_BY_STEP.value: {
                "name": "步骤式指南",
                "description": "提供清晰的操作步骤、使用教程，提升实用性",
                "icon": "📝",
                "prompt_addition": """
【步骤式指南优化要求】
- 清晰步骤：将内容组织为清晰的步骤（1. 2. 3. 格式）
- 每步说明：每个步骤都有详细说明和注意事项
- 操作示例：提供具体操作示例或代码示例（如适用，用占位符）
- 常见问题：在每个关键步骤后添加"常见问题"或"注意事项"
- 结果验证：说明如何验证每个步骤的结果
- 总结步骤：在结尾总结关键步骤，便于回顾
"""
            },
            OptimizationTechnique.DATA_RICH.value: {
                "name": "数据丰富",
                "description": "大量使用数据、统计、图表，提升内容权威性",
                "icon": "📈",
                "prompt_addition": """
【数据丰富优化要求】
- 数据密度：每100字至少包含1-2个数据点（百分比、数量、增长率等）
- 数据多样性：包含不同类型的数据（市场数据、用户数据、性能数据等）
- 数据可视化建议：在合适位置建议使用图表（如"可用柱状图展示"）
- 数据来源：每个数据都标注来源占位（如"根据XX报告"）
- 数据时效性：标注数据的时间节点（如"2024年数据显示"）
- 数据对比：使用数据对比突出差异和优势
"""
            },
            OptimizationTechnique.CASE_STUDY.value: {
                "name": "案例研究",
                "description": "深入分析案例，展示实际应用效果",
                "icon": "🔬",
                "prompt_addition": """
【案例研究优化要求】
- 完整案例结构：包含背景、挑战、解决方案、实施过程、结果、经验总结
- 案例细节：提供足够的细节（用占位符），让案例真实可信
- 量化结果：案例结果要量化（如"提升XX%"、"节省XX时间"）
- 多案例对比：如可能，提供2-3个不同类型的案例
- 案例启示：从案例中提取可复用的经验和启示
- 适用性分析：说明案例的适用场景和局限性
"""
            },
            OptimizationTechnique.FAQ_FOCUSED.value: {
                "name": "FAQ 聚焦",
                "description": "以常见问题为核心，提供全面解答",
                "icon": "❓",
                "prompt_addition": """
【FAQ 聚焦优化要求】
- 问题收集：至少包含8-12个常见问题，覆盖用户主要关注点
- 问题分类：将问题按主题分类（如"功能类"、"使用类"、"对比类"）
- 详细解答：每个问题提供详细、全面的解答（至少100-200字）
- 问题关联：在解答中关联其他相关问题，形成知识网络
- 问题优先级：按重要性排序，重要问题放在前面
- 问题更新：在结尾提示"如有其他问题，可参考..."，引导进一步了解
"""
            }
        }
    
    def get_technique_info(self, technique_id: str) -> Optional[Dict]:
        """获取技巧信息"""
        return self.techniques.get(technique_id)
    
    def list_techniques(self) -> List[Dict]:
        """列出所有技巧"""
        return [
            {
                "id": tech_id,
                **info
            }
            for tech_id, info in self.techniques.items()
        ]
    
    def get_technique_names(self) -> List[str]:
        """获取所有技巧名称列表（用于 UI 显示）"""
        return [info["name"] for info in self.techniques.values()]
    
    def get_technique_ids_by_names(self, names: List[str]) -> List[str]:
        """根据名称列表获取技巧 ID 列表"""
        name_to_id = {info["name"]: tech_id for tech_id, info in self.techniques.items()}
        result = []
        for name in names:
            # 处理可能包含图标的情况（如 "📊 证据驱动"）
            clean_name = name.split(" ", 1)[-1] if " " in name else name
            if clean_name in name_to_id:
                result.append(name_to_id[clean_name])
        return result
    
    def enhance_prompt(self, base_prompt: str, technique_ids: List[str]) -> str:
        """
        根据选择的技巧增强 Prompt
        
        Args:
            base_prompt: 基础 Prompt 模板
            technique_ids: 选择的技巧 ID 列表
            
        Returns:
            增强后的 Prompt
        """
        if not technique_ids:
            return base_prompt
        
        # 收集所有技巧的 Prompt 增强内容
        enhancements = []
        for tech_id in technique_ids:
            tech_info = self.get_technique_info(tech_id)
            if tech_info and tech_info.get("prompt_addition"):
                enhancements.append(tech_info["prompt_addition"])
        
        if not enhancements:
            return base_prompt
        
        # 将增强内容添加到基础 Prompt
        enhanced_prompt = base_prompt
        
        # 在【开始】或【开始优化】之前插入增强内容
        if "【开始优化】" in enhanced_prompt:
            enhanced_prompt = enhanced_prompt.replace(
                "【开始优化】",
                "\n".join(enhancements) + "\n\n【开始优化】"
            )
        elif "【开始】" in enhanced_prompt:
            enhanced_prompt = enhanced_prompt.replace(
                "【开始】",
                "\n".join(enhancements) + "\n\n【开始】"
            )
        else:
            # 如果没有找到标记，直接追加到末尾
            enhanced_prompt = enhanced_prompt + "\n" + "\n".join(enhancements)
        
        return enhanced_prompt
    
    def get_technique_description(self, technique_id: str) -> str:
        """获取技巧描述"""
        tech_info = self.get_technique_info(technique_id)
        if tech_info:
            return f"{tech_info.get('icon', '')} {tech_info.get('name', '')}：{tech_info.get('description', '')}"
        return ""
    
    def get_combined_description(self, technique_ids: List[str]) -> str:
        """获取组合技巧的描述"""
        if not technique_ids:
            return "未选择优化技巧"
        
        descriptions = []
        for tech_id in technique_ids:
            tech_info = self.get_technique_info(tech_id)
            if tech_info:
                descriptions.append(f"{tech_info.get('icon', '')} {tech_info.get('name', '')}")
        
        return " + ".join(descriptions) if descriptions else "未选择优化技巧"
