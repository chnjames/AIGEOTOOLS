# 技术配置生成功能说明

## 📋 功能概述

技术配置生成模块是 GEO 工具的重要功能之一，用于生成 robots.txt、sitemap.xml 等技术配置文件，帮助搜索引擎更好地发现和索引内容，提升内容收录效果。

### 核心价值

- **加速内容收录**：社区测试显示可提升 20-30% 的收录效果
- **控制爬虫访问**：通过 robots.txt 控制搜索引擎爬虫的访问权限
- **提升索引效率**：通过 sitemap.xml 帮助搜索引擎快速发现所有页面
- **简化配置流程**：自动化生成技术配置文件，无需手动编写

## 🎯 功能位置

### Tab2（自动创作）- 技术配置生成模块

在 Tab2 中，技术配置生成模块位于 JSON-LD Schema.org 结构化数据生成之后、内容生成之前。

## 📊 功能模块

### 1. robots.txt 生成

**功能说明**：
- 生成标准的 robots.txt 文件
- 控制搜索引擎爬虫的访问权限
- 配置允许和禁止爬取的路径
- 自动添加 sitemap 链接

**配置选项**：
- **网站基础 URL**：您的网站基础 URL（如 https://example.com）
- **允许爬取的路径**：每行一个路径（如 /、/blog、/docs）
- **禁止爬取的路径**：每行一个路径（如 /admin、/private、/api）

**默认配置**：
- 默认禁止路径：/admin、/private、/api、/_next、/static
- 自动生成 sitemap URL

**使用说明**：
1. 输入网站基础 URL
2. 配置允许和禁止的路径（可选）
3. 点击"生成 robots.txt"
4. 下载文件并上传到网站根目录

---

### 2. sitemap.xml 生成

**功能说明**：
- 生成符合标准的 sitemap.xml 文件
- 支持基于关键词生成
- 支持基于历史文章生成
- 自动设置更新频率和优先级

**数据源选项**：
- **基于关键词生成**：使用【1 关键词蒸馏】中生成的关键词
- **基于历史文章生成**：使用【2 自动创作】中生成的历史文章

**配置选项**：
- **网站基础 URL**：您的网站基础 URL（如 https://example.com）
- **更新频率**：weekly（每周更新，默认）
- **优先级**：0.8（默认）

**URL 生成规则**：
- 关键词转换为 URL 友好格式（小写、连字符分隔）
- 移除特殊字符
- 基于平台信息生成路径（如适用）

**使用说明**：
1. 输入网站基础 URL
2. 选择数据源（基于关键词或历史文章）
3. 点击"生成 sitemap.xml"
4. 下载文件并上传到网站根目录
5. 在 Google Search Console 中提交 sitemap

## 🔄 工作流程

### robots.txt 生成流程

1. **输入配置**：
   - 输入网站基础 URL
   - 配置允许/禁止路径（可选）

2. **生成文件**：
   - 点击"生成 robots.txt"按钮
   - 系统自动生成标准格式的 robots.txt

3. **下载使用**：
   - 下载生成的 robots.txt 文件
   - 上传到网站根目录（如 https://example.com/robots.txt）

### sitemap.xml 生成流程

1. **选择数据源**：
   - 选择"基于关键词生成"：使用关键词列表
   - 选择"基于历史文章生成"：使用历史文章数据

2. **输入配置**：
   - 输入网站基础 URL

3. **生成文件**：
   - 点击"生成 sitemap.xml"按钮
   - 系统自动生成符合标准的 sitemap.xml

4. **下载使用**：
   - 下载生成的 sitemap.xml 文件
   - 上传到网站根目录（如 https://example.com/sitemap.xml）
   - 在 Google Search Console 中提交 sitemap

## 💡 使用建议

### 1. robots.txt 最佳实践

- **允许重要路径**：确保允许爬取重要内容路径（如 /、/blog、/docs）
- **禁止敏感路径**：禁止爬取管理后台、API 接口等敏感路径
- **定期更新**：根据网站结构变化更新 robots.txt

### 2. sitemap.xml 最佳实践

- **及时更新**：每次发布新内容后更新 sitemap.xml
- **提交到搜索引擎**：在 Google Search Console、Bing Webmaster Tools 中提交 sitemap
- **保持 URL 格式一致**：确保 sitemap 中的 URL 格式与网站实际 URL 一致

### 3. 技术配置组合使用

- **robots.txt + sitemap.xml**：组合使用效果最佳
- **JSON-LD Schema + 技术配置**：结构化数据 + 技术配置可进一步提升收录效果

## 🔧 技术实现

### 模块位置

- **生成模块**：`modules/technical_config_generator.py`
- **UI 集成**：`modules/geo_tool.py` Tab2

### 核心类

- `TechnicalConfigGenerator`：技术配置文件生成器
  - `generate_robots_txt()`：生成 robots.txt
  - `generate_sitemap_xml()`：生成 sitemap.xml
  - `generate_sitemap_from_articles()`：基于文章生成 sitemap
  - `sanitize_url_path()`：清理 URL 路径

### 文件格式

**robots.txt 格式**：
```
User-agent: *
Allow: /
Allow: /blog
Disallow: /admin
Disallow: /private
Sitemap: https://example.com/sitemap.xml
```

**sitemap.xml 格式**：
```xml
<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
  <url>
    <loc>https://example.com/keyword-1</loc>
    <lastmod>2025-01-26</lastmod>
    <changefreq>weekly</changefreq>
    <priority>0.8</priority>
  </url>
</urlset>
```

## 📝 更新日志

- **2025-01-26**：初始版本发布
  - 实现 robots.txt 生成功能
  - 实现 sitemap.xml 生成功能
  - 支持基于关键词和历史文章生成 sitemap
  - 集成到 Tab2（自动创作）

---

**版本**：1.0.0  
**最后更新**：2025-01-26
