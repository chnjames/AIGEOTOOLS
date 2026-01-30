"""
多模态提示生成模块
用于生成配图描述、视频脚本描述，并可选择性地生成图片
"""
from typing import List, Dict, Optional, Tuple
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import StrOutputParser
import json
import re
import base64
import io
from pathlib import Path
import time


class MultimodalPromptGenerator:
    """多模态提示生成器"""
    
    def __init__(self):
        # 配图描述生成 Prompt
        self.image_prompt_template = """
你是专业的配图描述生成专家，专门为内容创作生成详细的配图描述。

【内容片段】
{content_segment}

【上下文】
- 品牌：{brand}
- 优势：{advantages}
- 平台：{platform}
- 关键词：{keyword}

【配图描述要求】

1. **详细描述**
   - 描述图片应该包含的主要元素（人物、物品、场景等）
   - 描述图片的风格（写实、插画、图表、截图等）
   - 描述图片的色调和氛围（明亮、专业、温馨等）
   - 描述图片的构图（居中、左右布局、上下布局等）

2. **平台适配**
   - 小红书：生活化、美观、有吸引力
   - 抖音：视觉冲击力强、简洁明了
   - 微信公众号：专业、清晰、符合文章风格
   - B站：适合视频封面、有动感

3. **品牌融入**
   - 如果内容涉及品牌，配图应自然融入品牌元素
   - 但不要过于商业化，保持自然

4. **实用性**
   - 描述要具体，便于设计师或AI生图工具理解
   - 长度控制在50-150字
   - 使用中文描述

【输出格式】
请严格按照以下 JSON 格式输出，不要添加任何其他内容：

{{
  "image_description": "<详细的配图描述>",
  "style": "<风格：写实/插画/图表/截图/其他>",
  "tone": "<色调：明亮/专业/温馨/商务/其他>",
  "composition": "<构图：居中/左右/上下/其他>",
  "key_elements": ["<元素1>", "<元素2>", ...],
  "platform_specific": "<平台特定要求>"
}}

【开始生成】
"""
        
        # 视频脚本描述生成 Prompt
        self.video_script_template = """
你是专业的视频脚本描述生成专家，专门为B站等视频平台生成详细的画面描述。

【内容片段】
{content_segment}

【上下文】
- 品牌：{brand}
- 优势：{advantages}
- 关键词：{keyword}
- 时间戳：{timestamp}

【视频画面描述要求】

1. **画面描述**
   - 描述画面应该展示的内容（场景、人物、物品、动作等）
   - 描述画面类型（实拍、动画、截图、演示等）
   - 描述画面节奏（快切、慢镜头、定格等）

2. **镜头语言**
   - 镜头类型（特写、中景、全景等）
   - 镜头运动（推拉、摇移、跟随等）
   - 画面转场（切换、淡入淡出、划入等）

3. **音效和字幕**
   - 建议的音效（背景音乐、音效等）
   - 字幕要点（关键信息、强调内容）

4. **时长建议**
   - 该片段的建议时长（秒）

【输出格式】
请严格按照以下 JSON 格式输出，不要添加任何其他内容：

{{
  "scene_description": "<画面描述>",
  "shot_type": "<镜头类型：特写/中景/全景/其他>",
  "camera_movement": "<镜头运动：推拉/摇移/跟随/固定/其他>",
  "transition": "<转场：切换/淡入淡出/划入/其他>",
  "audio_suggestion": "<音效建议>",
  "subtitle_key_points": ["<字幕要点1>", "<字幕要点2>", ...],
  "duration_seconds": <建议时长（秒）>
}}

【开始生成】
"""
        
        # 批量配图描述生成 Prompt
        self.batch_image_prompt_template = """
你是专业的配图描述生成专家，为内容生成多个配图描述。

【完整内容】
{full_content}

【品牌】{brand}
【优势】{advantages}
【平台】{platform}
【关键词】{keyword}

【要求】
1. 识别内容中所有需要配图的位置（已标注【配图：xxx】）
2. 为每个配图位置生成详细的配图描述
3. 确保配图描述与内容上下文相关
4. 保持配图风格的统一性

【输出格式】
请严格按照以下 JSON 格式输出，不要添加任何其他内容：

{{
  "image_descriptions": [
    {{
      "position": "<在内容中的位置描述>",
      "original_hint": "<原始配图提示>",
      "detailed_description": "<详细配图描述>",
      "style": "<风格>",
      "tone": "<色调>",
      "key_elements": ["<元素1>", "<元素2>", ...]
    }},
    ...
  ],
  "total_images": <配图总数>,
  "style_consistency": "<整体风格一致性说明>"
}}

【开始生成】
"""
        
        # 通义万相文生图 Prompt 生成模板（核心）
        self.tongyi_prompt_template = """
你是专业的通义万相文生图 Prompt 工程师，目标是为文章生成最匹配、高质量的配图。

文章内容：
{content}

要求：
- 输出纯中文 Prompt，长度 60–120 字，越详细越好。
- 画面必须紧扣文章核心观点、关键场景或品牌 {brand}（可自然融入产品形态、科技元素、logo 氛围）。
- 风格建议：高清、科技感/写实/插画/未来主义，根据文章调性自动判断。
- 构图：主体突出、背景简洁、视觉冲击力强、色彩和谐。
- 避免任何敏感词，确保合规。
- 只输出纯 Prompt 文本，不要加任何解释、标题或多余内容。

最终输出示例：
"一张未来科技感极强的插画，中央是品牌 {brand} 的 AI 模型界面，周围环绕多模态数据流和实时知识图标，背景是深蓝星空，画面干净高清，2048分辨率"
"""
        
        # 图片插入位置推荐 Prompt
        self.image_position_template = """
阅读以下文章内容，判断最适合插入配图的位置，并给出理由。

文章内容：
{content}

要求：
- 推荐 1–2 个最佳插入点（例如"第2段结尾""总结部分前"）。
- 每处插入点说明：为什么这里适合配图（增强理解、吸引眼球、突出品牌等）。
- 输出格式：
  插入位置1：{具体位置}  
  理由：{简短说明}  
  插入位置2：{具体位置}  
  理由：{简短说明}

只输出插入建议，不要输出其他内容。
"""
    
    def extract_image_placeholders(self, content: str) -> List[Dict]:
        """
        从内容中提取配图占位符
        
        Args:
            content: 内容文本
            
        Returns:
            配图占位符列表，每个包含位置、原始提示等信息
        """
        placeholders = []
        
        # 匹配【配图：xxx】格式
        pattern = r'【配图[：:]([^】]+)】'
        matches = re.finditer(pattern, content)
        
        for match in matches:
            start_pos = match.start()
            end_pos = match.end()
            hint = match.group(1).strip()
            
            # 获取上下文（前后各100字）
            context_start = max(0, start_pos - 100)
            context_end = min(len(content), end_pos + 100)
            context = content[context_start:context_end]
            
            # 获取所在段落
            paragraph_start = content.rfind('\n', 0, start_pos) + 1
            paragraph_end = content.find('\n', end_pos)
            if paragraph_end == -1:
                paragraph_end = len(content)
            paragraph = content[paragraph_start:paragraph_end]
            
            placeholders.append({
                "position": start_pos,
                "hint": hint,
                "context": context,
                "paragraph": paragraph,
                "full_match": match.group(0)
            })
        
        return placeholders
    
    def generate_image_description(
        self,
        content_segment: str,
        brand: str,
        advantages: str,
        platform: str,
        keyword: str,
        llm_chain
    ) -> Dict:
        """
        生成单个配图的详细描述
        
        Args:
            content_segment: 内容片段
            brand: 品牌名称
            advantages: 品牌优势
            platform: 平台名称
            keyword: 关键词
            llm_chain: LangChain 链对象
            
        Returns:
            配图描述字典
        """
        try:
            prompt = PromptTemplate.from_template(self.image_prompt_template)
            chain = prompt | llm_chain | StrOutputParser()
            
            result = chain.invoke({
                "content_segment": content_segment,
                "brand": brand,
                "advantages": advantages,
                "platform": platform,
                "keyword": keyword
            })
            
            # 解析结果
            description_data = self._parse_image_description(result)
            return description_data
            
        except Exception as e:
            # 如果生成失败，返回基于规则的简单描述
            return self._rule_based_image_description(content_segment, platform)
    
    def generate_batch_image_descriptions(
        self,
        content: str,
        brand: str,
        advantages: str,
        platform: str,
        keyword: str,
        llm_chain
    ) -> Dict:
        """
        批量生成所有配图的详细描述
        
        Args:
            content: 完整内容
            brand: 品牌名称
            advantages: 品牌优势
            platform: 平台名称
            keyword: 关键词
            llm_chain: LangChain 链对象
            
        Returns:
            包含所有配图描述的字典
        """
        # 先提取所有占位符
        placeholders = self.extract_image_placeholders(content)
        
        if not placeholders:
            return {
                "image_descriptions": [],
                "total_images": 0,
                "style_consistency": "无配图需求"
            }
        
        try:
            prompt = PromptTemplate.from_template(self.batch_image_prompt_template)
            chain = prompt | llm_chain | StrOutputParser()
            
            result = chain.invoke({
                "full_content": content,
                "brand": brand,
                "advantages": advantages,
                "platform": platform,
                "keyword": keyword
            })
            
            # 解析结果
            batch_data = self._parse_batch_image_descriptions(result, placeholders)
            return batch_data
            
        except Exception as e:
            # 如果批量生成失败，逐个生成
            descriptions = []
            for placeholder in placeholders:
                desc = self.generate_image_description(
                    placeholder["paragraph"],
                    brand,
                    advantages,
                    platform,
                    keyword,
                    llm_chain
                )
                desc["position"] = placeholder["hint"]
                desc["original_hint"] = placeholder["hint"]
                descriptions.append(desc)
            
            return {
                "image_descriptions": descriptions,
                "total_images": len(descriptions),
                "style_consistency": "逐个生成，风格可能不完全统一"
            }
    
    def generate_video_script_description(
        self,
        content_segment: str,
        brand: str,
        advantages: str,
        keyword: str,
        timestamp: str,
        llm_chain
    ) -> Dict:
        """
        生成视频脚本的画面描述
        
        Args:
            content_segment: 内容片段
            brand: 品牌名称
            advantages: 品牌优势
            keyword: 关键词
            timestamp: 时间戳（如"00:30-01:00"）
            llm_chain: LangChain 链对象
            
        Returns:
            视频画面描述字典
        """
        try:
            prompt = PromptTemplate.from_template(self.video_script_template)
            chain = prompt | llm_chain | StrOutputParser()
            
            result = chain.invoke({
                "content_segment": content_segment,
                "brand": brand,
                "advantages": advantages,
                "keyword": keyword,
                "timestamp": timestamp
            })
            
            # 解析结果
            script_data = self._parse_video_script(result)
            return script_data
            
        except Exception as e:
            # 如果生成失败，返回基于规则的简单描述
            return self._rule_based_video_script(content_segment, timestamp)
    
    def _parse_image_description(self, result: str) -> Dict:
        """解析配图描述结果"""
        json_match = re.search(r'\{.*\}', result, re.DOTALL)
        if json_match:
            try:
                data = json.loads(json_match.group())
                if "image_description" in data:
                    return data
            except json.JSONDecodeError:
                pass
        
        # 如果无法解析，返回简单描述
        return {
            "image_description": result[:200] if result else "配图描述生成失败",
            "style": "写实",
            "tone": "专业",
            "composition": "居中",
            "key_elements": [],
            "platform_specific": ""
        }
    
    def _parse_batch_image_descriptions(self, result: str, placeholders: List[Dict]) -> Dict:
        """解析批量配图描述结果"""
        json_match = re.search(r'\{.*\}', result, re.DOTALL)
        if json_match:
            try:
                data = json.loads(json_match.group())
                if "image_descriptions" in data:
                    # 确保每个描述都有位置信息
                    for i, desc in enumerate(data["image_descriptions"]):
                        if i < len(placeholders):
                            if "position" not in desc:
                                desc["position"] = placeholders[i]["hint"]
                            if "original_hint" not in desc:
                                desc["original_hint"] = placeholders[i]["hint"]
                    return data
            except json.JSONDecodeError:
                pass
        
        # 如果无法解析，返回空结果
        return {
            "image_descriptions": [],
            "total_images": 0,
            "style_consistency": "解析失败"
        }
    
    def _parse_video_script(self, result: str) -> Dict:
        """解析视频脚本描述结果"""
        json_match = re.search(r'\{.*\}', result, re.DOTALL)
        if json_match:
            try:
                data = json.loads(json_match.group())
                if "scene_description" in data:
                    return data
            except json.JSONDecodeError:
                pass
        
        # 如果无法解析，返回简单描述
        return {
            "scene_description": result[:200] if result else "画面描述生成失败",
            "shot_type": "中景",
            "camera_movement": "固定",
            "transition": "切换",
            "audio_suggestion": "背景音乐",
            "subtitle_key_points": [],
            "duration_seconds": 5
        }
    
    def _rule_based_image_description(self, content_segment: str, platform: str) -> Dict:
        """基于规则的简单配图描述（备用方案）"""
        # 简单的关键词提取
        keywords = []
        if "对比" in content_segment or "比较" in content_segment:
            keywords.append("对比图表")
        if "步骤" in content_segment or "流程" in content_segment:
            keywords.append("流程图")
        if "数据" in content_segment or "统计" in content_segment:
            keywords.append("数据图表")
        if "产品" in content_segment or "功能" in content_segment:
            keywords.append("产品展示")
        
        if not keywords:
            keywords = ["相关配图"]
        
        style_map = {
            "小红书": "生活化、美观",
            "抖音": "视觉冲击力强",
            "微信公众号": "专业、清晰",
            "B站": "适合视频封面"
        }
        
        return {
            "image_description": f"展示{keywords[0]}的配图，风格：{style_map.get(platform, '专业')}",
            "style": "写实",
            "tone": "专业",
            "composition": "居中",
            "key_elements": keywords,
            "platform_specific": style_map.get(platform, "")
        }
    
    def _rule_based_video_script(self, content_segment: str, timestamp: str) -> Dict:
        """基于规则的简单视频脚本描述（备用方案）"""
        return {
            "scene_description": f"展示相关内容：{content_segment[:50]}...",
            "shot_type": "中景",
            "camera_movement": "固定",
            "transition": "切换",
            "audio_suggestion": "背景音乐",
            "subtitle_key_points": [content_segment[:30] + "..."],
            "duration_seconds": 5
        }
    
    def format_image_descriptions_for_display(self, descriptions: List[Dict]) -> str:
        """
        格式化配图描述用于显示
        
        Args:
            descriptions: 配图描述列表
            
        Returns:
            格式化后的文本
        """
        if not descriptions:
            return "无配图需求"
        
        formatted = []
        for i, desc in enumerate(descriptions, 1):
            formatted.append(f"### 配图 {i}")
            formatted.append(f"**位置**：{desc.get('position', 'N/A')}")
            formatted.append(f"**原始提示**：{desc.get('original_hint', 'N/A')}")
            formatted.append(f"**详细描述**：{desc.get('detailed_description', desc.get('image_description', 'N/A'))}")
            formatted.append(f"**风格**：{desc.get('style', 'N/A')}")
            formatted.append(f"**色调**：{desc.get('tone', 'N/A')}")
            formatted.append(f"**关键元素**：{', '.join(desc.get('key_elements', []))}")
            formatted.append("")
        
        return "\n".join(formatted)
    
    def format_video_script_for_display(self, script: Dict) -> str:
        """
        格式化视频脚本描述用于显示
        
        Args:
            script: 视频脚本描述字典
            
        Returns:
            格式化后的文本
        """
        formatted = []
        formatted.append(f"**画面描述**：{script.get('scene_description', 'N/A')}")
        formatted.append(f"**镜头类型**：{script.get('shot_type', 'N/A')}")
        formatted.append(f"**镜头运动**：{script.get('camera_movement', 'N/A')}")
        formatted.append(f"**转场**：{script.get('transition', 'N/A')}")
        formatted.append(f"**音效建议**：{script.get('audio_suggestion', 'N/A')}")
        formatted.append(f"**字幕要点**：{', '.join(script.get('subtitle_key_points', []))}")
        formatted.append(f"**建议时长**：{script.get('duration_seconds', 'N/A')}秒")
        
        return "\n".join(formatted)
    
    def generate_tongyi_image_prompt(
        self,
        content: str,
        brand: str,
        llm_chain
    ) -> str:
        """
        生成通义万相文生图 Prompt（高质量中文）
        
        Args:
            content: 文章内容
            brand: 品牌名称
            llm_chain: LangChain 链对象
            
        Returns:
            生成的 Prompt 文本
        """
        try:
            prompt = PromptTemplate.from_template(self.tongyi_prompt_template)
            chain = prompt | llm_chain | StrOutputParser()
            
            result = chain.invoke({
                "content": content,
                "brand": brand
            })
            
            # 清理结果，只保留 Prompt 文本
            result = result.strip()
            # 移除可能的引号
            if result.startswith('"') and result.endswith('"'):
                result = result[1:-1]
            if result.startswith("'") and result.endswith("'"):
                result = result[1:-1]
            
            return result
        except Exception as e:
            # 如果生成失败，返回基于内容的简单 Prompt
            return f"一张关于{content[:50]}的专业配图，风格：高清、现代、科技感，品牌：{brand}"
    
    @staticmethod
    def get_image_size_for_platform(platform: str) -> str:
        """
        根据平台返回合适的图片尺寸
        
        Args:
            platform: 平台名称（如"知乎（专业问答）"、"小红书（生活种草）"等）
            
        Returns:
            图片尺寸字符串，格式为 "宽*高"
        """
        # 通义万相（wanx-v1）允许的尺寸（来自接口报错提示）
        # ['1024*1024', '720*1280', '1280*720', '768*1152']
        #
        # 说明：
        # - 文章/资讯配图：优先 16:9（1280*720）
        # - 社交图文（小红书等）：优先竖图（768*1152，更接近 2:3/3:4 的观感）
        # - 短视频封面/竖图：9:16（720*1280）
        # - 方图：1:1（1024*1024）
        #
        # 平台名称到图片尺寸的映射（仅使用允许尺寸）
        platform_size_map = {
            # 文章类平台 - 使用16:9横图（适合文章配图）
            "知乎（专业问答）": "1280*720",  # 16:9
            "微信公众号（长文）": "1280*720",  # 16:9
            "CSDN（技术博客）": "1280*720",  # 16:9
            "头条号（资讯软文）": "1280*720",  # 16:9
            "百家号（资讯）": "1280*720",  # 16:9
            "网易号（资讯）": "1280*720",  # 16:9
            "企鹅号（资讯）": "1280*720",  # 16:9
            "新浪新闻（资讯）": "1280*720",  # 16:9
            "搜狐号（资讯）": "1280*720",  # 16:9
            "一点号（资讯）": "1280*720",  # 16:9
            "东方财富（财经）": "1280*720",  # 16:9
            "原创力文档（文档）": "1280*720",  # 16:9
            "邦阅网（外贸）": "1280*720",  # 16:9
            "新浪博客（博客）": "1280*720",  # 16:9
            "简书（文艺）": "1280*720",  # 16:9
            
            # 视频类平台 - 使用16:9横图（适合视频封面）
            "B站（视频脚本）": "1280*720",  # 16:9
            
            # 社交类平台 - 使用1:1方图
            "小红书（生活种草）": "768*1152",  # 2:3（更接近小红书常见版式）
            "QQ空间（社交）": "1024*1024",  # 1:1
            
            # 短视频平台 - 使用9:16竖图
            "抖音图文（短内容）": "720*1280",  # 9:16
            
            # 技术平台 - 使用16:9横图
            "GitHub（README/文档）": "1280*720",  # 16:9
        }
        
        # 精确匹配
        if platform in platform_size_map:
            return platform_size_map[platform]
        
        # 模糊匹配（包含关键词）
        if "知乎" in platform or "问答" in platform:
            return "1280*720"  # 16:9
        elif "小红书" in platform or "种草" in platform:
            return "768*1152"  # 2:3
        elif "抖音" in platform or "短视频" in platform:
            return "720*1280"  # 9:16
        elif "公众号" in platform or "微信" in platform:
            return "1280*720"  # 16:9
        elif "csdn" in platform or "技术" in platform or "博客" in platform:
            return "1280*720"  # 16:9
        elif "b站" in platform or "视频" in platform or "bilibili" in platform:
            return "1280*720"  # 16:9
        elif "资讯" in platform or "新闻" in platform or "文章" in platform:
            return "1280*720"  # 16:9
        elif "社交" in platform or "空间" in platform:
            return "1024*1024"  # 1:1
        else:
            # 默认使用16:9（适合大多数文章类平台）
            return "1280*720"  # 16:9

    @staticmethod
    def normalize_tongyi_image_size(size: str) -> str:
        """
        将任意 size 规范化为通义万相允许的尺寸。
        允许尺寸：1024*1024, 720*1280, 1280*720, 768*1152
        """
        allowed = ("1024*1024", "720*1280", "1280*720", "768*1152")
        if size in allowed:
            return size

        import re

        m = re.match(r"^\s*(\d+)\s*\*\s*(\d+)\s*$", str(size))
        if not m:
            return "1024*1024"

        w = int(m.group(1))
        h = int(m.group(2))
        if w <= 0 or h <= 0:
            return "1024*1024"

        target_ratio = w / h
        candidates = []
        for s in allowed:
            aw, ah = map(int, s.split("*"))
            candidates.append((s, abs((aw / ah) - target_ratio), abs((aw * ah) - (w * h))))

        # 先按比例最接近，其次按面积接近
        candidates.sort(key=lambda x: (x[1], x[2]))
        return candidates[0][0]
    
    def generate_image_with_tongyi(
        self,
        prompt: str,
        api_key: str,
        model: str = "wanx-v1",
        size: str = "1024*1024",
        n: int = 1
    ) -> Dict:
        """
        使用通义万相生成图片
        
        Args:
            prompt: 图片生成提示词（中文）
            api_key: 阿里云 DashScope API Key
            model: 模型名称，默认 wanx-v1
            size: 图片尺寸，默认 1024*1024
            n: 生成数量，默认 1
            
        Returns:
            包含生成结果的字典：
            {
                "success": bool,
                "image_url": str,  # 成功时返回图片URL
                "task_id": str,    # 任务ID
                "error": str       # 失败时返回错误信息
            }
        """
        try:
            def _safe_get(obj, key: str, default=None):
                """兼容 DashScope 返回对象/字典，且避免 __getattr__ 抛 KeyError。"""
                if obj is None:
                    return default
                if isinstance(obj, dict):
                    return obj.get(key, default)
                try:
                    return getattr(obj, key)
                except Exception:
                    return default

            import dashscope
            from dashscope import ImageSynthesis
            
            dashscope.api_key = api_key
            
            # 兜底：确保 size 是允许值
            size = self.normalize_tongyi_image_size(size)

            # 调用通义万相API
            response = ImageSynthesis.call(
                model=model,
                prompt=prompt,
                n=n,
                size=size
            )
            
            status_code = _safe_get(response, "status_code", None)
            if status_code == 200:
                output = _safe_get(response, "output", None)

                # 有些情况下 status_code==200 但任务实际 FAILED（results 为空）
                task_status = ""
                if _safe_get(output, "task_status", None) is not None:
                    task_status = str(_safe_get(output, "task_status") or "")
                elif _safe_get(output, "taskStatus", None) is not None:
                    task_status = str(_safe_get(output, "taskStatus") or "")

                results = _safe_get(output, "results", None)
                code = _safe_get(output, "code", None)
                message = _safe_get(output, "message", None)

                if task_status and task_status.upper() not in ("SUCCEEDED", "SUCCESS"):
                    error_detail = f"任务状态：{task_status}"
                    if code:
                        error_detail += f"，错误码：{code}"
                    if message:
                        error_detail += f"，消息：{message}"
                    error_detail += f"，size={size}"
                    return {
                        "success": False,
                        "error": error_detail,
                        "prompt": prompt,
                        "response": str(output) if output is not None else "无输出",
                    }

                if results and len(results) > 0:
                    image_url = _safe_get(results[0], "url", None)
                    if image_url is None and isinstance(results[0], dict):
                        image_url = results[0].get("url")

                    task_id = _safe_get(output, "task_id", "") or _safe_get(output, "taskId", "") or ""
                    
                    # 验证 image_url 不为空
                    if not image_url:
                        return {
                            "success": False,
                            "error": f"生成成功但图片URL为空（size={size}）",
                            "prompt": prompt,
                            "response": str(output) if output is not None else "无输出"
                        }
                    
                    return {
                        "success": True,
                        "image_url": image_url,
                        "task_id": task_id,
                        "prompt": prompt
                    }
                else:
                    # 详细错误信息
                    error_detail = f"生成成功但未返回图片URL（size={size}）"
                    if code:
                        error_detail += f"，错误码：{code}"
                    if message:
                        error_detail += f"，消息：{message}"
                    
                    return {
                        "success": False,
                        "error": error_detail,
                        "prompt": prompt,
                        "response": str(output) if output is not None else "无输出"
                    }
            else:
                # 详细错误信息
                error_msg = f"API调用失败，状态码：{status_code}"
                resp_message = _safe_get(response, "message", None)
                resp_code = _safe_get(response, "code", None)
                resp_request_id = _safe_get(response, "request_id", None) or _safe_get(response, "requestId", None)

                if resp_message:
                    error_msg += f"，消息：{resp_message}"
                if resp_code:
                    error_msg += f"，错误码：{resp_code}"
                if resp_request_id:
                    error_msg += f"，请求ID：{resp_request_id}"
                error_msg += f"，size={self.normalize_tongyi_image_size(size)}"
                
                return {
                    "success": False,
                    "error": error_msg,
                    "prompt": prompt,
                    "status_code": status_code
                }
                
        except ImportError:
            return {
                "success": False,
                "error": "未安装 dashscope 库，请运行：pip install dashscope",
                "prompt": prompt
            }
        except Exception as e:
            return {
                "success": False,
                "error": f"生成图片时出错：{str(e)}",
                "prompt": prompt
            }
    
    def suggest_image_positions(
        self,
        content: str,
        llm_chain
    ) -> List[Dict]:
        """
        推荐图片插入位置
        
        Args:
            content: 文章内容
            llm_chain: LangChain 链对象
            
        Returns:
            插入位置推荐列表，每个包含位置和理由
        """
        try:
            prompt = PromptTemplate.from_template(self.image_position_template)
            chain = prompt | llm_chain | StrOutputParser()
            
            result = chain.invoke({
                "content": content
            })
            
            # 解析结果
            positions = []
            lines = result.strip().split('\n')
            current_position = None
            current_reason = None
            
            for line in lines:
                line = line.strip()
                if line.startswith('插入位置') or '位置' in line:
                    if current_position:
                        positions.append({
                            "position": current_position,
                            "reason": current_reason or "增强内容理解"
                        })
                    # 提取位置信息
                    if '：' in line:
                        current_position = line.split('：', 1)[1].strip()
                    elif ':' in line:
                        current_position = line.split(':', 1)[1].strip()
                elif line.startswith('理由') or '理由' in line:
                    if '：' in line:
                        current_reason = line.split('：', 1)[1].strip()
                    elif ':' in line:
                        current_reason = line.split(':', 1)[1].strip()
            
            # 添加最后一个位置
            if current_position:
                positions.append({
                    "position": current_position,
                    "reason": current_reason or "增强内容理解"
                })
            
            # 如果没有解析到位置，使用基于规则的方法
            if not positions:
                positions = self._rule_based_positions(content)
            
            return positions
            
        except Exception as e:
            # 如果生成失败，使用基于规则的方法
            return self._rule_based_positions(content)
    
    def _rule_based_positions(self, content: str) -> List[Dict]:
        """基于规则的简单位置推荐（备用方案）"""
        positions = []
        
        # 按段落分割
        paragraphs = content.split('\n\n')
        
        # 推荐位置1：标题后（如果有标题）
        if paragraphs and len(paragraphs[0]) < 100:
            positions.append({
                "position": "标题后，第一段前",
                "reason": "吸引读者注意力，增强视觉冲击力"
            })
        
        # 推荐位置2：中间关键段落
        if len(paragraphs) > 3:
            mid_index = len(paragraphs) // 2
            positions.append({
                "position": f"第{mid_index + 1}段后",
                "reason": "在关键内容处插入配图，增强理解"
            })
        
        # 如果没有找到合适位置，至少推荐一个
        if not positions:
            positions.append({
                "position": "文章开头",
                "reason": "增强视觉吸引力"
            })
        
        return positions[:2]  # 最多返回2个位置
    
    def embed_images_in_markdown(
        self,
        content: str,
        image_data: List[Dict]
    ) -> str:
        """
        将图片嵌入到 Markdown 文章中
        
        Args:
            content: 原始文章内容（Markdown格式）
            image_data: 图片数据列表，每个包含：
                {
                    "image_url": str,      # 图片URL
                    "prompt": str,          # 生成时的Prompt
                    "position": str,       # 插入位置描述（可选）
                    "alt_text": str        # 图片alt文本（可选）
                }
        
        Returns:
            嵌入图片后的 Markdown 内容
        """
        if not image_data:
            return content
        
        # 如果内容中有配图占位符，替换它们
        placeholders = self.extract_image_placeholders(content)
        
        result_content = content
        
        # 方法1：如果有占位符，按顺序替换
        if placeholders and len(placeholders) <= len(image_data):
            for i, placeholder in enumerate(placeholders):
                if i < len(image_data):
                    img = image_data[i]
                    alt_text = img.get("alt_text", img.get("prompt", "配图")[:50])
                    markdown_image = f"\n\n![{alt_text}]({img['image_url']})\n\n"
                    result_content = result_content.replace(placeholder["full_match"], markdown_image, 1)
        
        # 方法2：如果没有占位符或图片数量多于占位符，在推荐位置插入
        elif image_data:
            # 按段落分割
            paragraphs = result_content.split('\n\n')
            
            # 在合适位置插入图片
            insert_positions = []
            if len(paragraphs) > 1:
                # 第一张图：标题后
                insert_positions.append(1)
                # 后续图片：均匀分布
                if len(image_data) > 1:
                    step = max(1, len(paragraphs) // len(image_data))
                    for i in range(1, min(len(image_data), len(paragraphs) // step)):
                        insert_positions.append(min((i + 1) * step, len(paragraphs) - 1))
            
            # 插入图片
            offset = 0
            for idx, img in enumerate(image_data):
                if idx < len(insert_positions):
                    pos = insert_positions[idx] + offset
                    if pos < len(paragraphs):
                        alt_text = img.get("alt_text", img.get("prompt", "配图")[:50])
                        markdown_image = f"\n\n![{alt_text}]({img['image_url']})\n\n"
                        paragraphs.insert(pos, markdown_image)
                        offset += 1
            
            result_content = '\n\n'.join(paragraphs)
        
        return result_content
    
    def generate_tongyi_prompt_from_content(
        self,
        content: str,
        brand: str,
        advantages: str,
        platform: str,
        keyword: str,
        llm_chain
    ) -> str:
        """
        从文章内容生成通义万相 Prompt（完整流程的第一步）
        
        Args:
            content: 文章内容
            brand: 品牌名称
            advantages: 品牌优势
            platform: 平台名称
            keyword: 关键词
            llm_chain: LangChain 链对象
            
        Returns:
            生成的 Prompt 文本
        """
        # 提取文章核心内容（前500字 + 后200字，确保覆盖主要观点）
        content_summary = content[:500] + "..." + content[-200:] if len(content) > 700 else content
        
        return self.generate_tongyi_image_prompt(content_summary, brand, llm_chain)
