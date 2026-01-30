"""
技术配置生成模块
生成 robots.txt、sitemap.xml 等技术配置文件，提升内容收录效果
"""
from typing import List, Dict, Optional
from datetime import datetime
from urllib.parse import urljoin, urlparse
import xml.etree.ElementTree as ET


class TechnicalConfigGenerator:
    """技术配置文件生成器"""
    
    def __init__(self):
        pass
    
    def generate_robots_txt(
        self,
        base_url: str = "",
        allow_paths: List[str] = None,
        disallow_paths: List[str] = None,
        sitemap_url: str = "",
        user_agent: str = "*",
        crawl_delay: Optional[int] = None
    ) -> str:
        """
        生成 robots.txt 文件
        
        Args:
            base_url: 网站基础 URL（如 https://example.com）
            allow_paths: 允许爬取的路径列表（如 ["/", "/blog", "/docs"]）
            disallow_paths: 禁止爬取的路径列表（如 ["/admin", "/private"]）
            sitemap_url: sitemap.xml 的 URL
            user_agent: User-Agent（默认 "*" 表示所有爬虫）
            crawl_delay: 爬取延迟（秒，可选）
            
        Returns:
            robots.txt 文件内容
        """
        lines = []
        
        # User-Agent 规则
        lines.append(f"User-agent: {user_agent}")
        
        # 允许路径
        if allow_paths:
            for path in allow_paths:
                lines.append(f"Allow: {path}")
        
        # 禁止路径
        if disallow_paths:
            for path in disallow_paths:
                lines.append(f"Disallow: {path}")
        else:
            # 默认禁止路径（如果未指定）
            default_disallow = [
                "/admin",
                "/private",
                "/api",
                "/_next",
                "/static",
            ]
            for path in default_disallow:
                lines.append(f"Disallow: {path}")
        
        # 爬取延迟
        if crawl_delay is not None:
            lines.append(f"Crawl-delay: {crawl_delay}")
        
        # Sitemap
        if sitemap_url:
            lines.append(f"Sitemap: {sitemap_url}")
        elif base_url:
            # 自动生成 sitemap URL
            sitemap_url = urljoin(base_url.rstrip('/') + '/', 'sitemap.xml')
            lines.append(f"Sitemap: {sitemap_url}")
        
        return "\n".join(lines)
    
    def generate_sitemap_xml(
        self,
        base_url: str,
        urls: List[Dict[str, any]] = None,
        keywords: List[str] = None,
        lastmod: Optional[str] = None,
        changefreq: str = "weekly",
        priority: float = 0.8
    ) -> str:
        """
        生成 sitemap.xml 文件
        
        Args:
            base_url: 网站基础 URL（如 https://example.com）
            urls: URL 列表，每个元素包含：
                - loc: URL 路径（如 "/blog/post-1"）
                - lastmod: 最后修改时间（ISO 格式，如 "2025-01-26"）
                - changefreq: 更新频率（如 "daily", "weekly", "monthly"）
                - priority: 优先级（0.0-1.0）
            keywords: 关键词列表（如果提供，会基于关键词生成 URL）
            lastmod: 默认最后修改时间（ISO 格式）
            changefreq: 默认更新频率
            priority: 默认优先级
            
        Returns:
            sitemap.xml 文件内容
        """
        # 如果没有提供 lastmod，使用当前日期
        if lastmod is None:
            lastmod = datetime.now().strftime("%Y-%m-%d")
        
        # 创建 XML 根元素
        root = ET.Element("urlset")
        root.set("xmlns", "http://www.sitemaps.org/schemas/sitemap/0.9")
        
        # 如果提供了 URLs，使用它们
        if urls:
            for url_data in urls:
                url_elem = ET.SubElement(root, "url")
                
                # loc（URL）
                loc = url_data.get("loc", "")
                if not loc.startswith("http"):
                    loc = urljoin(base_url.rstrip('/') + '/', loc.lstrip('/'))
                ET.SubElement(url_elem, "loc").text = loc
                
                # lastmod
                url_lastmod = url_data.get("lastmod", lastmod)
                ET.SubElement(url_elem, "lastmod").text = url_lastmod
                
                # changefreq
                url_changefreq = url_data.get("changefreq", changefreq)
                ET.SubElement(url_elem, "changefreq").text = url_changefreq
                
                # priority
                url_priority = url_data.get("priority", priority)
                ET.SubElement(url_elem, "priority").text = str(url_priority)
        
        # 如果提供了关键词，基于关键词生成 URL
        elif keywords:
            for keyword in keywords:
                url_elem = ET.SubElement(root, "url")
                
                # 生成 URL（基于关键词）
                # 将关键词转换为 URL 友好的格式
                url_path = keyword.lower().replace(" ", "-").replace("_", "-")
                # 移除特殊字符
                import re
                url_path = re.sub(r'[^\w\-]', '', url_path)
                full_url = urljoin(base_url.rstrip('/') + '/', url_path)
                
                ET.SubElement(url_elem, "loc").text = full_url
                ET.SubElement(url_elem, "lastmod").text = lastmod
                ET.SubElement(url_elem, "changefreq").text = changefreq
                ET.SubElement(url_elem, "priority").text = str(priority)
        
        # 如果没有提供 URLs 或关键词，至少添加首页
        else:
            url_elem = ET.SubElement(root, "url")
            ET.SubElement(url_elem, "loc").text = base_url.rstrip('/') + '/'
            ET.SubElement(url_elem, "lastmod").text = lastmod
            ET.SubElement(url_elem, "changefreq").text = changefreq
            ET.SubElement(url_elem, "priority").text = "1.0"
        
        # 格式化 XML
        ET.indent(root, space="  ")
        xml_str = ET.tostring(root, encoding="unicode", xml_declaration=True)
        
        return xml_str
    
    def generate_sitemap_from_articles(
        self,
        base_url: str,
        articles: List[Dict[str, str]],
        lastmod: Optional[str] = None,
        changefreq: str = "weekly",
        priority: float = 0.8
    ) -> str:
        """
        基于文章列表生成 sitemap.xml
        
        Args:
            base_url: 网站基础 URL
            articles: 文章列表，每个元素包含：
                - keyword: 关键词
                - platform: 平台
                - content: 内容（可选）
                - created_at: 创建时间（可选）
            lastmod: 默认最后修改时间
            changefreq: 默认更新频率
            priority: 默认优先级
            
        Returns:
            sitemap.xml 文件内容
        """
        urls = []
        
        for article in articles:
            keyword = article.get("keyword", "")
            platform = article.get("platform", "")
            created_at = article.get("created_at", "")
            
            # 生成 URL 路径
            # 将关键词转换为 URL 友好的格式
            url_path = keyword.lower().replace(" ", "-").replace("_", "-")
            import re
            url_path = re.sub(r'[^\w\-]', '', url_path)
            
            # 如果有平台信息，可以添加到路径中
            if platform:
                platform_slug = platform.lower().replace(" ", "-").replace("（", "").replace("）", "")
                platform_slug = re.sub(r'[^\w\-]', '', platform_slug)
                url_path = f"{platform_slug}/{url_path}"
            
            # 使用创建时间作为 lastmod
            article_lastmod = lastmod
            if created_at:
                try:
                    # 尝试解析时间字符串
                    if "T" in created_at:
                        dt = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
                    else:
                        dt = datetime.strptime(created_at, "%Y-%m-%d")
                    article_lastmod = dt.strftime("%Y-%m-%d")
                except:
                    pass
            
            urls.append({
                "loc": url_path,
                "lastmod": article_lastmod or lastmod or datetime.now().strftime("%Y-%m-%d"),
                "changefreq": changefreq,
                "priority": priority
            })
        
        return self.generate_sitemap_xml(
            base_url=base_url,
            urls=urls,
            lastmod=lastmod,
            changefreq=changefreq,
            priority=priority
        )
    
    def generate_htaccess_redirects(
        self,
        redirects: List[Dict[str, str]]
    ) -> str:
        """
        生成 .htaccess 重定向规则
        
        Args:
            redirects: 重定向列表，每个元素包含：
                - from: 源路径
                - to: 目标路径
                - type: 重定向类型（301 永久重定向，302 临时重定向）
                
        Returns:
            .htaccess 文件内容
        """
        lines = []
        lines.append("# .htaccess 重定向规则")
        lines.append("# 由 GEO 工具自动生成")
        lines.append("")
        
        for redirect in redirects:
            from_path = redirect.get("from", "")
            to_path = redirect.get("to", "")
            redirect_type = redirect.get("type", "301")
            
            if from_path and to_path:
                lines.append(f"Redirect {redirect_type} {from_path} {to_path}")
        
        return "\n".join(lines)
    
    def generate_meta_tags(
        self,
        title: str,
        description: str,
        keywords: List[str] = None,
        og_type: str = "website",
        og_image: str = "",
        canonical_url: str = ""
    ) -> str:
        """
        生成 HTML meta 标签
        
        Args:
            title: 页面标题
            description: 页面描述
            keywords: 关键词列表
            og_type: Open Graph 类型（如 "website", "article"）
            og_image: Open Graph 图片 URL
            canonical_url: 规范 URL
            
        Returns:
            HTML meta 标签字符串
        """
        tags = []
        
        # 基础 meta 标签
        tags.append(f'<meta charset="UTF-8">')
        tags.append(f'<meta name="viewport" content="width=device-width, initial-scale=1.0">')
        tags.append(f'<title>{title}</title>')
        tags.append(f'<meta name="description" content="{description}">')
        
        # 关键词
        if keywords:
            keywords_str = ", ".join(keywords)
            tags.append(f'<meta name="keywords" content="{keywords_str}">')
        
        # Open Graph 标签
        tags.append(f'<meta property="og:type" content="{og_type}">')
        tags.append(f'<meta property="og:title" content="{title}">')
        tags.append(f'<meta property="og:description" content="{description}">')
        if og_image:
            tags.append(f'<meta property="og:image" content="{og_image}">')
        
        # Canonical URL
        if canonical_url:
            tags.append(f'<link rel="canonical" href="{canonical_url}">')
        
        return "\n".join(tags)
    
    def validate_url(self, url: str) -> bool:
        """
        验证 URL 格式
        
        Args:
            url: URL 字符串
            
        Returns:
            是否为有效 URL
        """
        try:
            result = urlparse(url)
            return all([result.scheme, result.netloc])
        except:
            return False
    
    def sanitize_url_path(self, path: str) -> str:
        """
        清理 URL 路径，使其符合 URL 规范
        
        Args:
            path: 原始路径
            
        Returns:
            清理后的路径
        """
        import re
        # 转换为小写
        path = path.lower()
        # 替换空格为连字符
        path = path.replace(" ", "-")
        # 移除特殊字符
        path = re.sub(r'[^\w\-/]', '', path)
        # 移除多余的连字符
        path = re.sub(r'-+', '-', path)
        # 移除开头和结尾的连字符
        path = path.strip('-')
        return path
