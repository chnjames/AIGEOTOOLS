# GEO 智能内容优化平台

<div align="center">

![Python](https://img.shields.io/badge/Python-3.10+-blue.svg)
![Streamlit](https://img.shields.io/badge/Streamlit-1.30+-red.svg)
![LangChain](https://img.shields.io/badge/LangChain-0.4+-green.svg)
![License](https://img.shields.io/badge/License-MIT-yellow.svg)

**让您的品牌在 AI 搜索中被优先引用**

[快速开始](#-快速开始) · [功能特性](#-功能特性) · [使用指南](#-使用指南) · [文档](#-文档)

</div>



---

## 📖 项目简介

**GEO（Generative Engine Optimization）智能内容优化平台** 是一款 AI 驱动的品牌内容策略工具，帮助企业在 AI 搜索引擎（如 ChatGPT、Perplexity、Google SGE）的回答中被优先、准确、可信地提及。

### 解决什么问题？

当用户向 AI 提问"最好的外贸 ERP 软件是什么？"时，AI 会从互联网内容中检索信息并生成回答。**GEO 工具帮助您的品牌出现在这个回答中**。

### 核心价值


| 价值          | 说明                 |
| ----------- | ------------------ |
| 🎯 **品牌曝光** | 在 AI 回答中被优先提及      |
| 📈 **搜索排名** | 内容被 AI 引用，间接提升 SEO |
| 🏆 **权威建立** | 多平台、多角度内容建立专业形象    |
| 📊 **数据驱动** | 基于验证数据持续优化策略       |


---

## ✨ 功能特性

### 🔍 关键词策略

- **智能关键词生成**：AI 生成 + 词库组合 + 混合模式
- **搜索意图覆盖**：对比、评测、使用、购买、问题、推荐
- **数据增强**：基于历史验证数据反哺关键词策略
- **语义扩展**：自动扩展相关关键词

### ✍️ 内容生成

- **20+ 平台模板**：知乎、小红书、CSDN、B站、微信公众号等
- **E-E-A-T 内嵌**：专业性、经验性、权威性、可信度
- **品牌植入策略**：自然提及 2-4 次，避免过度营销
- **结构化输出**：结论摘要、清单、FAQ 格式

### 📚 知识库（RAG）

- **文档管理**：上传品牌文档、产品手册、案例库
- **智能检索**：生成内容时自动检索相关信息
- **来源保障**：基于真实品牌信息生成内容

### 🔧 内容优化

- **E-E-A-T 强化**：四维评估与自动优化
- **事实密度增强**：添加数据支撑和来源引用
- **结构化数据**：自动生成 JSON-LD Schema（FAQ、HowTo、Article 等）
- **内容评分**：量化评估内容质量

### ✅ 验证监控

- **多模型验证**：DeepSeek、OpenAI、通义千问等多模型交叉验证
- **AI 搜索验证**：接入 Perplexity 真实搜索引擎验证
- **竞品对比**：同时验证自有品牌和竞品
- **负面防护**：主动生成负面查询并监控

### 📊 数据分析

- **提及率趋势**：按日期跟踪品牌提及率变化
- **平台贡献度**：分析各平台的内容贡献
- **ROI 分析**：API 调用成本统计与优化建议
- **内容独特性**：检测批量内容的相似度

### 🔄 平台同步

- **GitHub API**：一键发布到 GitHub
- **12 平台复制**：知乎、小红书、CSDN 等平台一键复制
- **发布记录**：跟踪发布状态

---

## 🚀 快速开始

### 环境要求

- Python 3.10+
- pip 或 conda

### 安装步骤

```bash
# 1. 克隆仓库
git clone https://github.com/your-username/geo_tool.git
cd geo_tool

# 2. 安装依赖
pip install -r requirements.txt

# 3. 运行应用
streamlit run geo_tool.py
```

### 配置 API Key

首次运行后，在侧边栏配置 LLM API Key：


| 提供商      | 说明          |
| -------- | ----------- |
| DeepSeek | 推荐，性价比高     |
| OpenAI   | GPT-4o-mini |
| 通义千问     | 阿里云         |
| Groq     | 推理加速        |
| Moonshot | Kimi        |
| 豆包       | 字节跳动        |
| 文心一言     | 百度          |


---

## 📋 使用指南

### 基本工作流程

```
1. 关键词蒸馏 → 生成 GEO 优化关键词
        ↓
2. 品牌知识库 → 上传品牌文档和案例
        ↓
3. 自动创作 → 基于知识库生成内容
        ↓
4. 内容优化 → E-E-A-T 强化 + Schema 生成
        ↓
5. 多模型验证 → 验证品牌是否被提及
        ↓
6. 平台同步 → 发布到各平台
        ↓
7. 数据报表 → 监控效果并优化
```

### Tab 功能说明


| Tab        | 功能      | 说明             |
| ---------- | ------- | -------------- |
| 🎯 关键词蒸馏   | 关键词生成   | AI/词库/混合三种模式   |
| ✍️ 自动创作    | 内容生成    | 20+ 平台模板       |
| 🔧 文章优化    | 内容优化    | E-E-A-T 强化     |
| ✅ 多模型验证    | 效果验证    | 多模型交叉验证        |
| 📚 历史记录    | 数据查看    | 历史数据回顾         |
| 📊 AI 数据报表 | 数据分析    | 趋势图、ROI 分析     |
| ⚙️ 工作流自动化  | 自动化     | 一键完成全流程        |
| 📦 GEO 资源库 | 资源管理    | 优化资源推荐         |
| 🔄 平台同步    | 内容分发    | GitHub + 12 平台 |
| 🛠️ 配置优化助手 | 配置管理    | 智能配置建议         |
| 📚 品牌知识库   | RAG 知识库 | 文档管理与检索        |


---

## 🏗️ 项目结构

```
geo_tool/
├── .streamlit/              # Streamlit 配置
│   └── config.toml          # 主题配置
├── docs/                    # 项目文档
│   ├── features/            # 功能文档
│   ├── guides/              # 使用指南
│   ├── implementation/      # 实现文档
│   └── analysis/            # 分析报告
├── modules/                 # 核心模块
│   ├── ui/                  # UI 模块（Tab）
│   │   ├── tab_keywords.py  # 关键词 Tab
│   │   ├── tab_autowrite.py # 自动创作 Tab
│   │   ├── tab_optimize.py  # 文章优化 Tab
│   │   ├── tab_validation.py # 验证 Tab
│   │   ├── tab_reports.py   # 报表 Tab
│   │   ├── tab_workflow.py  # 工作流 Tab
│   │   ├── tab_resources.py # 资源库 Tab
│   │   ├── tab_platform_sync.py # 平台同步 Tab
│   │   ├── tab_config_optimizer.py # 配置优化 Tab
│   │   ├── tab_knowledge.py # 知识库 Tab
│   │   ├── components.py    # 公共组件
│   │   ├── state.py         # 状态管理
│   │   └── theme.py         # 主题样式
│   ├── knowledge_base.py    # RAG 知识库
│   ├── ai_search_verifier.py # AI 搜索验证
│   ├── content_uniqueness.py # 内容独特性检测
│   ├── keyword_data_enhancer.py # 关键词数据增强
│   ├── llm_factory.py       # LLM 工厂
│   ├── data_storage.py      # 数据存储
│   ├── content_scorer.py    # 内容评分
│   ├── eeat_enhancer.py     # E-E-A-T 强化
│   ├── schema_generator.py  # Schema 生成
│   └── ...                  # 其他模块
├── platform_sync/           # 平台同步模块
│   ├── base_publisher.py    # 发布器基类
│   ├── github_publisher.py  # GitHub 发布器
│   └── copy_manager.py      # 复制管理器
├── geo_tool.py              # 主程序入口
├── requirements.txt         # 依赖声明
├── README.md                # 项目说明
└── DOCS.md                  # 文档索引
```

---

## 📊 技术栈


| 技术                                   | 用途        |
| ------------------------------------ | --------- |
| [Streamlit](https://streamlit.io/)   | Web UI 框架 |
| [LangChain](https://langchain.com/)  | LLM 编排框架  |
| [SQLite](https://sqlite.org/)        | 数据存储      |
| [Plotly](https://plotly.com/)        | 数据可视化     |
| [Pandas](https://pandas.pydata.org/) | 数据处理      |


### 支持的 LLM


| 提供商      | 模型                   |
| -------- | -------------------- |
| DeepSeek | deepseek-chat        |
| OpenAI   | gpt-4o-mini, gpt-4   |
| 通义千问     | qwen-max, qwen-turbo |
| Groq     | llama3-70b-8192      |
| Moonshot | moonshot-v1-128k     |
| 豆包       | 自定义                  |
| 文心一言     | ernie-bot-turbo      |


---

## 📚 文档


| 文档                                         | 说明         |
| ------------------------------------------ | ---------- |
| [DOCS.md](DOCS.md)                         | 完整文档索引     |
| [快速开始指南](docs/guides/QUICK_START_GUIDE.md) | 新用户入门      |
| [平台设置指南](docs/guides/PLATFORM_SETUP.md)    | API Key 配置 |
| [数据存储指南](docs/guides/STORAGE_GUIDE.md)     | 存储方案说明     |
| [产品规格文档](docs/PRODUCT_SPEC.md)             | 产品定位与规划    |


### 功能文档

- [品牌知识库（RAG）](docs/features/KNOWLEDGE_BASE_FEATURE.md)
- [AI 搜索验证](docs/features/AI_SEARCH_VERIFIER_FEATURE.md)
- [内容独特性检测](docs/features/CONTENT_UNIQUENESS_FEATURE.md)
- [关键词数据增强](docs/features/KEYWORD_DATA_ENHANCER_FEATURE.md)
- [E-E-A-T 评估与强化](docs/features/EEAT_FEATURE.md)
- [JSON-LD Schema 生成](docs/features/JSON_LD_SCHEMA_FEATURE.md)

---

## 🤝 贡献

欢迎贡献代码、报告问题或提出建议！

### 贡献方式

1. Fork 本仓库
2. 创建特性分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 创建 Pull Request

### 开发规范

- 遵循 PEP 8 代码规范
- 添加必要的注释和文档
- 确保所有测试通过

---

## 📄 许可证

本项目采用 MIT 许可证 - 详见 [LICENSE](LICENSE) 文件

---

## 🙏 致谢

- [Streamlit](https://streamlit.io/) - 优秀的 Web UI 框架
- [LangChain](https://langchain.com/) - 强大的 LLM 编排框架
- 所有贡献者和用户

---



**如果这个项目对您有帮助，请给一个 ⭐ Star 支持一下！**

---

## 👨‍💻 关于作者

**一点一木（Grant Liu）** — 独立开发者 · 掘金LV.5（593K+阅读）· 2024人气作者No.91

- 📝 掘金：[juejin.cn/user/1063982986187486](https://juejin.cn/user/1063982986187486)
- 📱 公众号：**一点一木**
- 🐙 GitHub：[github.com/chnjames](https://github.com/chnjames)
- 🌐 博客：[chnjames.github.io/blogs](https://chnjames.github.io/blogs)
- 🏗️ 更多作品：[echo-suno-writer](https://github.com/chnjames/echo-suno-writer) · [tradehot-skill](https://github.com/chnjames/tradehot-skill)

> Work harder! Keep on!

