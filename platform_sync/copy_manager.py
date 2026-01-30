"""
一键复制管理器 - 用于无API平台的内容格式化
"""
import pyperclip
from typing import Dict, Any, Optional
import re


class CopyManager:
    """一键复制管理器"""
    
    def __init__(self):
        self.templates = self._init_templates()
    
    def _init_templates(self) -> Dict[str, Dict[str, Any]]:
        """初始化平台格式模板"""
        return {
            "头条号（资讯软文）": {
                "format": "title_content",
                "max_length": 2000,
                "supports_tags": True
            },
            "小红书（生活种草）": {
                "format": "title_content_tags",
                "max_length": 1000,
                "supports_tags": True,
                "supports_images": True
            },
            "抖音图文（短内容）": {
                "format": "title_content_tags",
                "max_length": 500,
                "supports_tags": True,
                "supports_images": True
            },
            "简书（文艺）": {
                "format": "title_content",
                "max_length": 3000,
                "supports_tags": True
            },
            "QQ空间（社交）": {
                "format": "title_content",
                "max_length": 1500,
                "supports_tags": True,
                "supports_images": True
            },
            "新浪博客（博客）": {
                "format": "title_content",
                "max_length": 3000,
                "supports_tags": True
            },
            "新浪新闻（资讯）": {
                "format": "title_content",
                "max_length": 2000,
                "supports_tags": False
            },
            "搜狐号（资讯）": {
                "format": "title_content",
                "max_length": 2500,
                "supports_tags": True
            },
            "一点号（资讯）": {
                "format": "title_content",
                "max_length": 2500,
                "supports_tags": True
            },
            "东方财富（财经）": {
                "format": "title_content",
                "max_length": 3000,
                "supports_tags": False
            },
            "邦阅网（外贸）": {
                "format": "title_content",
                "max_length": 2500,
                "supports_tags": True
            },
            "原创力文档（文档）": {
                "format": "title_content",
                "max_length": 5000,
                "supports_tags": False
            }
        }
    
    def format_for_platform(self, platform: str, content: str, title: str, 
                           keyword: str = "", brand: str = "", **kwargs) -> str:
        """
        为平台格式化内容
        
        Args:
            platform: 平台名称
            content: 原始内容
            title: 标题
            keyword: 关键词
            brand: 品牌
            **kwargs: 其他参数（标签、摘要等）
        
        Returns:
            格式化后的内容
        """
        template_config = self.templates.get(platform, {})
        format_type = template_config.get("format", "title_content")
        max_length = template_config.get("max_length", 2000)
        
        # 提取标题（如果内容中包含标题）
        if not title and content:
            # 尝试从内容第一行提取标题
            first_line = content.split('\n')[0].strip()
            if len(first_line) < 100 and not first_line.startswith('#'):
                title = first_line
            else:
                title = keyword or "文章标题"
        
        # 清理内容
        formatted_content = self._clean_content(content, platform)
        
        # 截断内容（如果需要）
        if max_length and len(formatted_content) > max_length:
            formatted_content = formatted_content[:max_length] + "..."
        
        # 根据格式类型格式化
        if format_type == "title_content":
            return f"{title}\n\n{formatted_content}"
        elif format_type == "title_content_tags":
            tags = kwargs.get('tags', [])
            tags_str = " ".join([f"#{tag}" for tag in tags[:10]]) if tags else ""
            return f"{title}\n\n{formatted_content}\n\n{tags_str}"
        else:
            return f"{title}\n\n{formatted_content}"
    
    def _clean_content(self, content: str, platform: str) -> str:
        """清理内容，移除平台不支持的格式"""
        # 移除Markdown图片语法，保留描述
        content = re.sub(r'!\[([^\]]*)\]\([^\)]+\)', r'【配图：\1】', content)
        
        # 移除Markdown链接，保留文本
        content = re.sub(r'\[([^\]]+)\]\([^\)]+\)', r'\1', content)
        
        # 移除Markdown代码块标记，保留内容
        content = re.sub(r'```[\w]*\n', '', content)
        content = re.sub(r'```', '', content)
        
        # 移除Markdown标题标记
        content = re.sub(r'^#+\s+', '', content, flags=re.MULTILINE)
        
        # 移除Markdown加粗/斜体
        content = re.sub(r'\*\*([^\*]+)\*\*', r'\1', content)
        content = re.sub(r'\*([^\*]+)\*', r'\1', content)
        content = re.sub(r'__([^_]+)__', r'\1', content)
        content = re.sub(r'_([^_]+)_', r'\1', content)
        
        return content.strip()
    
    def copy_to_clipboard(self, text: str) -> bool:
        """复制到剪贴板"""
        try:
            pyperclip.copy(text)
            return True
        except Exception as e:
            print(f"复制失败: {e}")
            return False
    
    def generate_publish_guide(self, platform: str) -> str:
        """生成发布指南"""
        guides = {
            "头条号（资讯软文）": """
📝 发布步骤：
1. 登录头条号后台（https://mp.toutiao.com/）
2. 点击"发布" → "文章"
3. 粘贴标题和内容
4. 添加封面图和标签
5. 选择分类和频道
6. 点击"发布"

💡 提示：
- 标题要吸引人，控制在30字以内
- 内容建议800-2000字
- 配图建议3-5张
            """,
            "小红书（生活种草）": """
📝 发布步骤：
1. 打开小红书APP
2. 点击"+"号发布
3. 选择"图文"
4. 粘贴标题和内容
5. 添加图片（建议3-9张）
6. 添加标签和话题
7. 选择位置（可选）
8. 发布

💡 提示：
- 标题要吸引人，控制在20字以内
- 内容建议500-1000字
- 图片要清晰美观
- 标签要相关且热门
            """,
            "抖音图文（短内容）": """
📝 发布步骤：
1. 打开抖音APP
2. 点击"+"号发布
3. 选择"图文"
4. 粘贴标题和内容
5. 添加图片（建议3-9张）
6. 添加话题标签
7. 选择位置（可选）
8. 发布

💡 提示：
- 标题要吸引人，控制在30字以内
- 内容建议200-500字
- 图片要清晰美观
- 话题要热门
            """,
            "简书（文艺）": """
📝 发布步骤：
1. 登录简书（https://www.jianshu.com/）
2. 点击"写文章"
3. 粘贴标题和内容
4. 添加标签
5. 选择专题（可选）
6. 点击"发布"

💡 提示：
- 标题要有文艺范
- 内容建议1500-3000字
- 标签要相关
            """,
            "QQ空间（社交）": """
📝 发布步骤：
1. 打开QQ空间
2. 点击"说说"或"日志"
3. 粘贴标题和内容
4. 添加图片（可选）
5. 选择可见范围
6. 发布

💡 提示：
- 内容要轻松活泼
- 建议500-1500字
- 配图要生活化
            """,
            "新浪博客（博客）": """
📝 发布步骤：
1. 登录新浪博客（https://blog.sina.com.cn/）
2. 点击"发博文"
3. 粘贴标题和内容
4. 添加标签
5. 选择分类
6. 点击"发布"

💡 提示：
- 内容要有深度
- 建议1500-3000字
- 配图要相关
            """,
            "新浪新闻（资讯）": """
📝 发布步骤：
1. 登录新浪新闻后台
2. 点击"发布文章"
3. 粘贴标题和内容
4. 添加配图
5. 选择分类
6. 提交审核

💡 提示：
- 内容要客观专业
- 建议800-2000字
- 配图要清晰
            """,
            "搜狐号（资讯）": """
📝 发布步骤：
1. 登录搜狐号（https://mp.sohu.com/）
2. 点击"发布" → "文章"
3. 粘贴标题和内容
4. 添加封面图和标签
5. 选择分类
6. 点击"发布"

💡 提示：
- 内容要专业
- 建议1000-2500字
- 配图要相关
            """,
            "一点号（资讯）": """
📝 发布步骤：
1. 登录一点号后台
2. 点击"发布文章"
3. 粘贴标题和内容
4. 添加配图和标签
5. 选择分类
6. 提交审核

💡 提示：
- 内容要有深度
- 建议1000-2500字
            """,
            "东方财富（财经）": """
📝 发布步骤：
1. 登录东方财富后台
2. 点击"发布文章"
3. 粘贴标题和内容
4. 添加配图
5. 选择财经分类
6. 提交审核

💡 提示：
- 内容要专业准确
- 建议1500-3000字
- 数据要准确
            """,
            "邦阅网（外贸）": """
📝 发布步骤：
1. 登录邦阅网后台
2. 点击"发布文章"
3. 粘贴标题和内容
4. 添加标签
5. 选择外贸分类
6. 提交审核

💡 提示：
- 内容要专业实用
- 建议1000-2500字
            """,
            "原创力文档（文档）": """
📝 发布步骤：
1. 登录原创力文档（https://www.doc88.com/）
2. 点击"上传文档"
3. 选择"新建文档"
4. 粘贴标题和内容
5. 设置文档属性
6. 提交审核

💡 提示：
- 内容要结构化
- 建议2000-5000字
- 格式要规范
            """
        }
        return guides.get(platform, "请参考平台官方发布指南")
