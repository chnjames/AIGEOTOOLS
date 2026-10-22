# GEO 智能内容优化平台

<div align="center">

![Python](https://img.shields.io/badge/Python-3.10+-blue.svg)
![FastAPI](https://img.shields.io/badge/FastAPI-0.110+-009688.svg)
![React](https://img.shields.io/badge/React-18-61dafb.svg)
![TypeScript](https://img.shields.io/badge/TypeScript-5.5-3178c6.svg)
![Ant Design](https://img.shields.io/badge/Ant%20Design-5-blue.svg)
![License](https://img.shields.io/badge/License-MIT-yellow.svg)

**让您的品牌在 AI 搜索引擎中被优先引用**

[快速开始](#-快速开始) · [功能特性](#-功能特性) · [架构说明](#-架构说明) · [部署指南](docs/DEPLOYMENT.md) · [API 文档](docs/API.md)

</div>

---

## 📖 项目简介

**GEO（Generative Engine Optimization）智能内容优化平台** 是一款 AI 驱动的品牌内容策略工具，帮助企业在 AI 搜索引擎（ChatGPT、Perplexity、Google AI Overview、DeepSeek 等）的回答中被优先、准确、可信地提及。

### 核心价值

| 价值 | 说明 |
|------|------|
| 🎯 品牌曝光 | 在 AI 回答中被优先、正面提及 |
| 📈 内容策略 | AI 生成适配多平台的优质内容 |
| 🏆 权威建立 | E-E-A-T 优化、事实密度增强、结构化数据 |
| 📊 效果验证 | 多模型交叉验证品牌提及率，数据驱动优化 |

---

## ✨ 功能特性

### 🔍 关键词策略
- **AI 智能生成**：基于品牌定位生成高价值关键词
- **行业预设**：SaaS / 电商 / 教育 / 医疗 / 金融 / 制造业预设词库
- **语义扩展**：LLM 语义扩展相关长尾词（支持多级撤销）
- **质量分析**：意图分布饼图、品牌词比例、问题词比例
- **标签收藏**：关键词收藏、自定义标签、跨项目复用
- **自动去重**：与历史关键词自动去重

### ✍️ 内容创作
- **22+ 平台模板**：知乎、小红书、微信公众号、B站、CSDN、掘金、GitHub 等，支持自定义
- **Markdown 在线编辑**：即时预览，版本历史（保留最近 10 版）
- **Diff 对比**：任意两版本差异可视化对比
- **混合批量**：不同关键词可选择不同目标平台
- **一键流转**：生成 → 优化 → 验证
- **平台分组**：推荐 / 技术社区 / 社交媒体 / 资讯平台

### 📚 知识库（RAG）
- **文档支持**：TXT / Markdown / PDF / Word（.docx）
- **ChromaDB 向量搜索**：语义检索相关内容
- **智能注入**：内容生成和优化时自动注入相关知识
- **可配置开关**：设置中可全局启用/禁用

### 🔧 内容优化
- **E-E-A-T 强化**：经验、专业、权威、可信度四维增强
- **事实密度增强**：自动添加数据支撑，⚠️待验证来源标注
- **Schema 结构化数据**：FAQ / HowTo / Article JSON-LD 自动生成
- **版本还原**：一键还原为原始内容
- **DDS 三维评分**：语义深度 / 数据支撑 / 权威来源

### ✅ 多模型验证
- **7 大模型支持**：DeepSeek / OpenAI / 通义千问 / Groq / Kimi / 豆包 / 文心一言
- **自然模式**：不暴露品牌名，模拟真实 AI 搜索结果
- **提示模式**：传统验证模式（品牌在提示中）
- **情感分析**：正面 / 中立 / 负面提及分类
- **失败诊断**：品牌未提及时 LLM 自动诊断原因并给出建议
- **完整响应存储**：保存完整 AI 回答供后续分析

### ⚙️ 自动化工作流
- **可视化编排**：关键词 → 内容 → 优化 → 验证全流程
- **定时执行**：每日 / 每周自动运行
- **步骤状态实时追踪**：等待 / 运行中 / 成功 / 失败
- **失败重试**：单步失败可单独重试

### 📊 数据分析
- **提及率趋势**：ECharts 双轴图展示日趋势
- **成本分析**：按提供商/模型/操作类型统计 API 成本
- **ROI 估算**：设置单次提及价值和平台系数
- **负面案例**：负面情感案例一览与诊断
- **报表导出**：CSV 导出

### 🔄 平台发布
- **复制发布**：一键复制 Markdown 内容
- **GitHub 发布**：通过 GitHub API 直接发布到仓库
- **失败重试**：发布失败记录可一键重试
- **发布历史**：完整发布记录追踪

### 🗂️ 数据管理
- **全量导出**：JSON 格式完整备份
- **模块 CSV 导出**：关键词 / 文章 / 验证记录 / API 调用
- **数据导入**：支持跳过 / 覆盖 / 追加三种策略
- **数据清理**：按时间范围清理历史数据
- **存储监控**：数据库大小、各表记录数
- **审计日志**：所有关键操作留痕

### 🔒 生产就绪
- **LLM 错误分类**：API Key 无效/余额不足/超时/速率限制等，中文友好提示
- **超时重试**：统一超时（60s 默认），可重试错误指数退避重试
- **速率限制**：提供商间调用间隔 ≥1 秒
- **Prompt 注入检测**：自动检测常见注入模式并警告
- **API Key 认证**：X-API-Key 请求头，hmac 常量时间比较
- **操作确认**：所有删除/清空操作二次确认
- **服务端分页**：所有列表默认 20 条/页

---

## 🏗️ 架构说明

```
┌─────────────────────────────────────────────────────────┐
│                    前端 (React 18)                       │
│  Ant Design 5 · TypeScript · Vite · Zustand · ECharts   │
└────────────────────────┬────────────────────────────────┘
                         │  HTTP / SSE
┌────────────────────────┴────────────────────────────────┐
│                  后端 (FastAPI async)                    │
│                                                         │
│  API 层  →  服务层  →  数据层                            │
│  (路由)     (业务逻辑)   (SQLAlchemy)                    │
│                                                         │
│  LLM 服务（超时/重试/速率限制/错误分类/缓存）            │
│  ChromaDB 向量搜索（知识库 RAG）                         │
│  APScheduler 定时任务（后台监控）                        │
│  SSE 流式输出                                           │
└────────────────────────┬────────────────────────────────┘
              ┌──────────┴──────────┐
              │  SQLite / PgSQL     │  数据持久化
              │  ChromaDB files     │  向量存储
              │  uploads/           │  文件上传
              └─────────────────────┘
```

**技术栈**
- 后端：FastAPI 0.110+ / SQLAlchemy 2.0 async / Alembic / LangChain / ChromaDB / APScheduler / Pydantic v2
- 前端：React 18 / TypeScript 5.5 strict / Ant Design 5 / Vite / Zustand / ECharts
- 支持的 LLM：DeepSeek / OpenAI(GPT) / 通义千问 / Groq / Kimi / 豆包 / 文心一言

---

## 🚀 快速开始

### 方式一：Docker Compose（推荐）

```bash
# 1. 克隆项目
git clone <repo-url> && cd geo-platform

# 2. 配置环境变量
cp .env.example .env
# 编辑 .env，设置 API_KEY

# 3. 启动服务
docker-compose up -d

# 4. 访问
# 前端：http://localhost
# 后端 API 文档：http://localhost:8000/docs
```

### 方式二：本地开发

**后端**
```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
alembic upgrade head
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
# 访问 http://localhost:8000/docs 查看 API 文档
```

**前端**
```bash
cd frontend
npm install
npm run dev
# 访问 http://localhost:5173
```

---

## 📁 项目结构

```
geo-platform/
├── backend/                    # FastAPI 后端
│   ├── app/
│   │   ├── api/v1/            # API 路由（16个模块）
│   │   ├── core/              # 配置/数据库/异常/调度/缓存
│   │   ├── models/            # SQLAlchemy ORM 模型（15个表）
│   │   ├── schemas/           # Pydantic 请求/响应模型
│   │   ├── services/          # 业务逻辑服务（20个）
│   │   ├── prompts/           # LLM Prompt 模板
│   │   └── utils/             # 工具函数
│   ├── alembic/               # 数据库迁移
│   ├── tests/                 # 测试
│   └── requirements.txt
│
├── frontend/                   # React 前端
│   ├── src/
│   │   ├── api/               # API 调用封装
│   │   ├── components/        # 通用组件
│   │   ├── hooks/             # 自定义 Hooks
│   │   ├── layouts/           # 布局
│   │   ├── pages/             # 页面（19个）
│   │   ├── stores/            # Zustand 状态
│   │   ├── styles/            # 全局样式
│   │   └── utils/             # 工具
│   ├── Dockerfile
│   └── nginx.conf
│
├── docs/                       # 文档
│   ├── DEPLOYMENT.md          # 部署指南
│   ├── API.md                 # API 接口文档
│   └── RUNBOOK.md             # 运维手册
├── deploy/nginx/              # Nginx 部署配置
├── legacy/                    # 旧版 Streamlit 代码（归档）
├── docker-compose.yml
├── .env.example
└── README.md
```

---

## 📖 文档

- [部署指南](docs/DEPLOYMENT.md) — 生产部署、Docker、Nginx、HTTPS
- [API 文档](docs/API.md) — REST API 端点概览（启动后也可访问 `/docs` 交互式文档）
- [运维手册](docs/RUNBOOK.md) — 日常运维、数据备份、故障排查

---

## 🔧 环境变量

| 变量 | 说明 | 默认值 |
|------|------|--------|
| `API_KEY` | API 请求认证密钥 | 建议设置强密码 |
| `DATABASE_URL` | 数据库连接串 | `sqlite+aiosqlite:///./data/app.db` |
| `CORS_ORIGINS` | 跨域允许源（逗号分隔） | `*` |
| `BACKEND_PORT` | 后端服务端口（Docker） | `8000` |
| `FRONTEND_PORT` | 前端服务端口（Docker） | `80` |
| `LLM_CACHE_ENABLED` | LLM 响应缓存开关 | `true` |
| `LLM_CACHE_TTL_SECONDS` | 缓存有效期秒数 | `3600` |
| `MAX_UPLOAD_SIZE` | 单文件上传上限 | `10MB` |
| `USD_TO_CNY_RATE` | 美元人民币汇率 | `7.2` |

> LLM 提供商的 API Key 在界面首次使用向导中配置，无需环境变量。

---

## 📝 首次使用流程

1. 启动服务后首次访问，自动弹出 **3步配置向导**
2. **步骤1**：选择默认 LLM 提供商，输入 API Key，点击"测试连接"
3. **步骤2**：输入品牌名称和品牌优势
4. **步骤3**：进入工作台
5. **关键词** → 生成/选择目标关键词
6. **内容创作** → 选中关键词批量生成文章 → 在线编辑
7. **优化** → 一键发送文章到优化页执行 E-E-A-T/事实密度增强
8. **验证** → 一键发送优化后的内容进行多模型品牌验证

---

## 📄 License

MIT License

---

## ⚠️ 注意事项

- 生成内容建议人工审核后再发布
- API Key 请妥善保管，不要提交到代码仓库
- 生产环境请修改默认 `API_KEY`，使用 HTTPS
- 知识库单文件建议不超过 10MB，总量建议 50MB 以内
