# JSON-LD Schema.org 结构化数据生成功能说明

## 📋 功能概述

JSON-LD Schema.org 结构化数据生成模块是 GEO 工具的核心功能之一，用于生成符合 Schema.org 规范的 JSON-LD 代码，直接提升品牌在 AI 模型中的实体识别和权威性。

### 核心价值

- **直接提升实体识别**：2026 年 AI 模型越来越依赖结构化数据识别实体
- **立竿见影的效果**：用户可直接将代码贴到官网/GitHub，无需等待索引
- **权威性提升**：结构化数据明确标识品牌信息，提升在知识图谱中的权威性
- **符合标准**：使用 Schema.org 标准，被 Google、百度、AI 模型广泛支持

## 🎯 功能位置

### 1. Tab2（自动创作）- 独立生成模块

在 Tab2 顶部，提供独立的 JSON-LD Schema 生成功能：

1. **选择 Schema 类型**
   - Organization（组织/公司）
   - SoftwareApplication（软件应用）
   - Product（产品）
   - Service（服务）
   - 组合（Organization + SoftwareApplication）

2. **一键生成**
   - 点击"🚀 生成 JSON-LD"按钮
   - 自动基于品牌信息和优势生成 Schema

3. **查看和下载**
   - 查看 JSON-LD 代码
   - 查看 HTML Script 标签
   - 下载 JSON 文件或 HTML 文件

### 2. Tab2（自动创作）- 自动生成

在生成 GitHub README 时，系统会自动生成对应的 JSON-LD Schema：

- 自动生成 SoftwareApplication 类型的 Schema
- 在内容预览区域显示 JSON-LD 代码
- 提供下载功能

## 📊 支持的 Schema 类型

### 1. Organization（组织/公司）

适合：企业品牌、公司官网

**包含字段：**
- name（名称）
- description（描述）
- url（官网 URL）
- logo（Logo URL）
- foundingDate（成立日期）
- contactPoint（联系方式）

**使用场景：**
- 公司官网
- 企业介绍页面
- 关于我们页面

### 2. SoftwareApplication（软件应用）

适合：SaaS 产品、软件工具、应用程序

**包含字段：**
- name（应用名称）
- description（应用描述）
- url（应用 URL）
- applicationCategory（应用类别）
- operatingSystem（操作系统）
- publisher（发布者）
- featureList（功能列表）
- offers（价格信息）
- aggregateRating（评分信息）

**使用场景：**
- GitHub 项目
- 软件官网
- 应用商店页面

### 3. Product（产品）

适合：实体产品或数字产品

**包含字段：**
- name（产品名称）
- description（产品描述）
- url（产品 URL）
- category（产品类别）
- brand（品牌信息）
- offers（价格信息）
- aggregateRating（评分信息）

**使用场景：**
- 产品详情页
- 电商页面
- 产品介绍页

### 4. Service（服务）

适合：服务类业务

**包含字段：**
- name（服务名称）
- description（服务描述）
- url（服务 URL）
- serviceType（服务类型）
- provider（服务提供者）
- areaServed（服务区域）
- offers（价格信息）

**使用场景：**
- 服务介绍页
- 服务详情页
- 业务介绍页

### 5. 组合 Schema

同时生成 Organization + SoftwareApplication/Product/Service

**优势：**
- 同时标识组织信息和产品/服务信息
- 建立更完整的品牌知识图谱
- 提升权威性

## 🔄 使用方法

### 方法一：独立生成（推荐）

1. **进入 Tab2（自动创作）**
2. **选择 Schema 类型**
   - 根据您的业务类型选择（软件产品选 SoftwareApplication，公司选 Organization）
3. **点击"🚀 生成 JSON-LD"**
4. **查看生成的代码**
   - JSON-LD 代码：可直接使用
   - HTML Script 标签：可直接嵌入网页
5. **下载代码**
   - 下载 JSON 文件：用于 GitHub 等平台
   - 下载 HTML 文件：用于官网嵌入

### 方法二：自动生成（GitHub README）

1. **在 Tab2 生成 GitHub README 内容**
2. **系统自动生成对应的 JSON-LD Schema**
3. **在内容预览区域查看 JSON-LD 代码**
4. **下载并添加到 GitHub 项目**

## 📝 使用示例

### 示例 1：嵌入官网

```html
<!DOCTYPE html>
<html>
<head>
    <title>我的品牌</title>
    <!-- 将生成的 HTML Script 标签粘贴到这里 -->
    <script type="application/ld+json">
    {
      "@context": "https://schema.org",
      "@type": "SoftwareApplication",
      "name": "汇信云AI软件",
      "description": "AI赋能外贸ERP...",
      ...
    }
    </script>
</head>
<body>
    ...
</body>
</html>
```

### 示例 2：添加到 GitHub README

在 GitHub 项目的 README.md 文件中，可以添加 JSON-LD Schema 的说明：

```markdown
# 我的项目

项目描述...

<!-- JSON-LD Schema -->
<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "SoftwareApplication",
  ...
}
</script>
```

## 🎯 最佳实践

1. **选择合适的 Schema 类型**
   - SaaS 产品：SoftwareApplication
   - 企业品牌：Organization
   - 实体产品：Product
   - 服务业务：Service

2. **完善 Schema 信息**
   - 添加官网 URL
   - 添加 Logo URL
   - 添加联系方式
   - 添加功能列表（如适用）

3. **验证 Schema**
   - 使用 [Google Rich Results Test](https://search.google.com/test/rich-results) 验证
   - 使用 [Schema.org Validator](https://validator.schema.org/) 验证

4. **多平台部署**
   - 官网：嵌入 HTML Script 标签
   - GitHub：添加到 README.md
   - 其他平台：根据平台要求调整

## ⚠️ 注意事项

1. **不要编造信息**
   - 所有信息必须真实
   - URL 必须可访问
   - Logo 必须存在

2. **保持更新**
   - 品牌信息变化时及时更新 Schema
   - 定期检查 Schema 有效性

3. **遵循规范**
   - 使用标准的 Schema.org 类型
   - 确保 JSON 格式正确
   - 避免使用不支持的属性

4. **测试验证**
   - 部署前使用验证工具测试
   - 确保 AI 模型能正确解析

## 🔗 相关资源

- [Schema.org 官方文档](https://schema.org/)
- [Google Rich Results Test](https://search.google.com/test/rich-results)
- [Schema.org Validator](https://validator.schema.org/)
- [JSON-LD 规范](https://json-ld.org/)

## 💡 预期效果

使用 JSON-LD Schema.org 结构化数据后：

1. **AI 模型识别**
   - AI 模型能更准确地识别品牌实体
   - 提升品牌在知识图谱中的权威性
   - 改善品牌信息的准确性

2. **搜索引擎优化**
   - 提升在 Google、百度等搜索引擎中的展示
   - 可能获得 Rich Results（富媒体结果）
   - 提升点击率

3. **知识图谱**
   - 建立品牌在知识图谱中的节点
   - 与其他实体建立关联
   - 提升品牌权威性

---

**版本**：v1.0  
**更新日期**：2025-01-26
