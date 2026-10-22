# GEO 智能内容优化平台 - 架构设计文档

## 1.1 项目理解

### 功能模块及职责

| 模块 | 文件 | 职责 | 类型 |
|------|------|------|------|
| 入口与配置 | `geo_tool.py` | Streamlit 页面入口、侧边栏配置、KPI 总览、Tab 路由 | UI 耦合 |
| 数据存储 | `modules/data_storage.py` | SQLite/JSON 双后端 CRUD，存储关键词、文章、优化记录、验证结果、API 调用、工作流、平台账号、发布记录 | 业务逻辑 |
| LLM 工厂 | `modules/llm_factory.py` | 统一构建 7 种 LLM 提供商（DeepSeek/OpenAI/通义/Groq/Kimi/豆包/文心）实例 | 业务逻辑 |
| 豆包封装 | `modules/chat_doubao.py` | LangChain 兼容的豆包聊天模型封装 | 业务逻辑 |
| 托词工具 | `modules/keyword_tool.py` | 词库组合生成关键词（笛卡尔积 + 相似度去重），LLM 润色 | 业务逻辑 |
| 关键词挖掘 | `modules/keyword_mining.py` | 竞品关键词挖掘、趋势分析（含搜索引擎结果抓取） | 业务逻辑 |
| 语义扩展 | `modules/semantic_expander.py` | LLM 驱动的语义足迹扩展（相关概念、长尾词、意图词） | 业务逻辑 |
| 关键词数据增强 | `modules/keyword_data_enhancer.py` | 基于历史数据增强关键词表现 | 业务逻辑 |
| 内容评分 | `modules/content_scorer.py` | 4 维度 LLM 评分（结构化/品牌提及/权威性/可引用性）+ 规则快速评估 | 业务逻辑 |
| 内容指标 | `modules/content_metrics.py` | 内容质量指标分析（可读性、关键词密度等） | 业务逻辑 |
| 内容独特性 | `modules/content_uniqueness.py` | 内容独特性检测（相似度、原创度） | 业务逻辑 |
| E-E-A-T 增强 | `modules/eeat_enhancer.py` | 经验/专业/权威/可信度信号注入 | 业务逻辑 |
| 事实密度增强 | `modules/fact_density_enhancer.py` | 可验证事实密度提升、结构化块生成 | 业务逻辑 |
| Schema 生成 | `modules/schema_generator.py` | Schema.org 结构化数据（JSON-LD）生成 | 业务逻辑 |
| 话题聚类 | `modules/topic_cluster.py` | 话题集群分析、内容地图 | 业务逻辑 |
| 知识库 | `modules/knowledge_base.py` | RAG 知识库管理（文档上传、向量化、检索） | 业务逻辑 |
| AI 搜索验证 | `modules/ai_search_verifier.py` | 多模型品牌提及验证、竞品对比 | 业务逻辑 |
| ROI 分析 | `modules/roi_analyzer.py` | API 成本计算、成本分析、ROI 估算、优化建议 | 业务逻辑 |
| 工作流自动化 | `modules/workflow_automation.py` | 可配置多步骤工作流（关键词→生成→优化→验证）、定时执行 | 业务逻辑 |
| 多模态提示 | `modules/multimodal_prompt.py` | 多模态内容生成（配图描述、视频脚本等） | 业务逻辑 |
| 优化技巧 | `modules/optimization_techniques.py` | GEO 优化技巧库管理 | 业务逻辑 |
| 配置优化器 | `modules/config_optimizer.py` | AI 辅助配置优化建议 | 业务逻辑 |
| 负面监控 | `modules/negative_monitor.py` | 品牌负面提及监控 | 业务逻辑 |
| 资源推荐 | `modules/resource_recommender.py` | GEO 学习资源推荐 | 业务逻辑 |
| 技术配置生成 | `modules/technical_config_generator.py` | 技术 SEO 配置（robots.txt、sitemap 等）生成 | 业务逻辑 |
| 平台同步-基础 | `platform_sync/base_publisher.py` | 发布器抽象基类 | 业务逻辑 |
| 平台同步-复制 | `platform_sync/copy_manager.py` | 复制到剪贴板管理 | 业务逻辑 |
| 平台同步-GitHub | `platform_sync/github_publisher.py` | GitHub Issue/PR 发布 | 业务逻辑 |
| UI 状态 | `modules/ui/state.py` | Streamlit session_state 初始化 | UI 耦合 |
| UI 主题 | `modules/ui/theme.py` | CSS 主题注入 | UI 耦合 |
| UI 组件 | `modules/ui/components.py` | 可复用 UI 组件 | UI 耦合 |
| Tab-关键词 | `modules/ui/tab_keywords.py` | 关键词蒸馏页面 UI | UI 耦合 |
| Tab-自动创作 | `modules/ui/tab_autowrite.py` | 批量内容创作 UI（平台选择、批量生成、ZIP 下载） | UI 耦合 |
| Tab-优化 | `modules/ui/tab_optimize.py` | 文章优化 UI（E-E-A-T/事实密度/Schema/独特性等） | UI 耦合 |
| Tab-验证 | `modules/ui/tab_validation.py` | 多模型验证 UI | UI 耦合 |
| Tab-历史 | `modules/ui/tab_history.py` | 历史记录 UI | UI 耦合 |
| Tab-报表 | `modules/ui/tab_reports.py` | 数据报表 UI（图表、ROI） | UI 耦合 |
| Tab-工作流 | `modules/ui/tab_workflow.py` | 工作流自动化 UI | UI 耦合 |
| Tab-资源 | `modules/ui/tab_resources.py` | 资源库 UI | UI 耦合 |
| Tab-平台同步 | `modules/ui/tab_platform_sync.py` | 平台同步 UI | UI 耦合 |
| Tab-配置优化 | `modules/ui/tab_config_optimizer.py` | 配置优化助手 UI | UI 耦合 |
| Tab-知识库 | `modules/ui/tab_knowledge.py` | 知识库管理 UI | UI 耦合 |

### 模块间调用关系和数据流

```
用户浏览器
    ↓
[Streamlit App: geo_tool.py]
    ├── 侧边栏配置 → cfg dict → 各 Tab
    ├── DataStorage (SQLite geo_data.db)
    │     ├── keywords 表
    │     ├── articles 表
    │     ├── optimizations 表
    │     ├── verify_results 表
    │     ├── api_calls 表
    │     ├── workflows / workflow_executions / workflow_templates 表
    │     ├── platform_accounts 表
    │     └── publish_records 表
    ├── KnowledgeBase (knowledge_base/ 目录, RAG)
    ├── KeywordTool (词库组合)
    ├── LLM Factory → 7种 LLM 客户端
    │
    ├── Tab1 关键词蒸馏: keyword_tool + keyword_mining + semantic_expander + topic_cluster + LLM
    ├── Tab2 自动创作: multimodal_prompt + platform templates + LLM → 批量ZIP
    ├── Tab3 文章优化: eeat_enhancer + fact_density_enhancer + schema_generator + content_scorer + LLM
    ├── Tab4 多模型验证: ai_search_verifier + 多个 verify_llms → record_api_cost
    ├── Tab5 历史记录: DataStorage → DataFrame 展示
    ├── Tab6 AI报表: roi_analyzer + content_metrics + negative_monitor + plotly
    ├── Tab7 工作流: workflow_automation → 串联以上所有模块
    ├── Tab8 资源库: resource_recommender + optimization_techniques
    ├── Tab9 平台同步: platform_sync (github_publisher + copy_manager)
    ├── Tab10 配置优化: config_optimizer + LLM
    └── Tab11 知识库: knowledge_base (文件上传/检索)

record_api_cost → ROIAnalyzer.calculate_cost() → DataStorage.save_api_call()
```

### 纯业务逻辑 vs UI 强耦合

**可复用的纯业务逻辑（迁移到 services 层，async 化）：**
- llm_factory.py / chat_doubao.py（增加 async 支持）
- keyword_tool.py
- keyword_mining.py（去掉 requests 改用 httpx async）
- semantic_expander.py
- keyword_data_enhancer.py
- content_scorer.py
- content_metrics.py
- content_uniqueness.py
- eeat_enhancer.py
- fact_density_enhancer.py
- schema_generator.py
- topic_cluster.py
- knowledge_base.py
- ai_search_verifier.py
- roi_analyzer.py
- workflow_automation.py
- multimodal_prompt.py
- optimization_techniques.py
- config_optimizer.py
- negative_monitor.py
- resource_recommender.py
- technical_config_generator.py
- platform_sync/ 所有文件
- data_storage.py（重写为 SQLAlchemy async ORM）

**需重写（React + Ant Design 重写）：**
- geo_tool.py（整体替换为 FastAPI + React）
- modules/ui/ 所有文件（全部重写为 React 组件）

### 数据库表结构

| 表名 | 字段 | 索引 |
|------|------|------|
| keywords | id (PK, AUTOINCREMENT), keyword (TEXT NOT NULL), brand (TEXT), created_at (TIMESTAMP) | - |
| articles | id (PK), keyword (TEXT), platform (TEXT), content (TEXT), filename (TEXT), brand (TEXT), publish_status (TEXT DEFAULT 'draft'), publish_urls (TEXT), created_at (TIMESTAMP) | - |
| optimizations | id (PK), original_content (TEXT), optimized_content (TEXT), changes (TEXT), platform (TEXT), brand (TEXT), created_at (TIMESTAMP) | - |
| verify_results | id (PK), query (TEXT), brand (TEXT), verify_model (TEXT), mention_count (INTEGER), mention_position (TEXT), content_snippet (TEXT), is_mentioned (INTEGER DEFAULT 0), created_at (TIMESTAMP) | - |
| api_calls | id (PK), operation_type (TEXT NOT NULL), provider (TEXT), model (TEXT), input_tokens (INTEGER DEFAULT 0), output_tokens (INTEGER DEFAULT 0), total_tokens (INTEGER DEFAULT 0), cost_usd (REAL DEFAULT 0.0), cost_cny (REAL DEFAULT 0.0), keyword (TEXT), platform (TEXT), brand (TEXT), created_at (TIMESTAMP) | - |
| workflows | id (TEXT PK), name (TEXT NOT NULL), steps (TEXT NOT NULL, JSON), schedule (TEXT), conditions (TEXT, JSON), enabled (INTEGER DEFAULT 1), created_at (TIMESTAMP), updated_at (TIMESTAMP) | - |
| workflow_executions | id (PK AUTOINCREMENT), workflow_id (TEXT NOT NULL, FK), status (TEXT NOT NULL), result (TEXT, JSON), progress (REAL DEFAULT 0), started_at (TIMESTAMP), completed_at (TIMESTAMP), error (TEXT) | workflow_id |
| workflow_templates | id (TEXT PK), name (TEXT NOT NULL), description (TEXT), steps (TEXT NOT NULL, JSON), created_at (TIMESTAMP) | - |
| platform_accounts | id (PK AUTOINCREMENT), platform (TEXT NOT NULL), account_type (TEXT NOT NULL), account_name (TEXT), api_key (TEXT), api_secret (TEXT), access_token (TEXT), refresh_token (TEXT), token_expires_at (TIMESTAMP), config_json (TEXT, JSON), is_active (INTEGER DEFAULT 1), brand (TEXT), created_at (TIMESTAMP), updated_at (TIMESTAMP) | UNIQUE(platform, brand, account_name) |
| publish_records | id (PK AUTOINCREMENT), article_id (INTEGER, FK), platform (TEXT NOT NULL), publish_method (TEXT NOT NULL), publish_status (TEXT NOT NULL), publish_url (TEXT), publish_id (TEXT), error_message (TEXT), retry_count (INTEGER DEFAULT 0), published_at (TIMESTAMP), created_at (TIMESTAMP) | article_id |
| knowledge_docs | id (PK), filename (TEXT NOT NULL), content (TEXT NOT NULL), content_hash (TEXT), file_type (TEXT), brand (TEXT), chunk_count (INTEGER DEFAULT 0), created_at (TIMESTAMP) | 新增表 |
| app_config | id (INTEGER PK DEFAULT 1), config_json (TEXT NOT NULL), updated_at (TIMESTAMP) | 新增表（替代 config.json） |

---

## 1.2 目标技术栈

- **后端**：Python 3.11+ / FastAPI / SQLAlchemy 2.0 (async) / Alembic / Pydantic v2 / httpx (async HTTP)
- **前端**：React 18 / TypeScript / Ant Design 5 / Vite / Zustand / ECharts / Axios
- **通信**：REST API（JSON）+ SSE（text/event-stream，用于 LLM 流式生成和进度通知）
- **部署**：Docker Compose（Nginx 反向代理 + FastAPI (Uvicorn) + React 静态文件）

---

## 1.3 架构设计

### 后端目录结构

```
backend/
├── app/
│   ├── __init__.py
│   ├── main.py                    # FastAPI 应用入口（CORS、路由、生命周期）
│   ├── core/
│   │   ├── __init__.py
│   │   ├── config.py              # Pydantic Settings 配置管理
│   │   ├── database.py            # SQLAlchemy async engine/session 工厂
│   │   ├── exceptions.py          # 层级化自定义异常类
│   │   ├── logging.py             # 结构化日志配置
│   │   ├── security.py            # API Key 认证依赖
│   │   └── cache.py               # LLM 响应内存缓存（TTL + LRU）
│   ├── models/
│   │   ├── __init__.py
│   │   ├── base.py                # SQLAlchemy DeclarativeBase
│   │   ├── keyword.py             # keywords 表 ORM 模型
│   │   ├── article.py             # articles 表 ORM 模型
│   │   ├── optimization.py        # optimizations 表 ORM 模型
│   │   ├── verify_result.py       # verify_results 表 ORM 模型
│   │   ├── api_call.py            # api_calls 表 ORM 模型
│   │   ├── workflow.py            # workflows/executions/templates 表 ORM 模型
│   │   ├── platform_account.py    # platform_accounts 表 ORM 模型
│   │   ├── publish_record.py      # publish_records 表 ORM 模型
│   │   ├── knowledge_doc.py       # knowledge_docs 表 ORM 模型
│   │   └── app_config.py          # app_config 表 ORM 模型
│   ├── schemas/
│   │   ├── __init__.py
│   │   ├── common.py              # 通用响应 schema（PageResponse 等）
│   │   ├── keyword.py             # Keyword Create/Update/Response
│   │   ├── article.py             # Article Create/Update/Response
│   │   ├── optimization.py        # Optimization Create/Response
│   │   ├── verify.py              # Verify 请求/响应/流式事件
│   │   ├── config.py              # AppConfig 请求/响应
│   │   ├── workflow.py            # Workflow/Execution 请求/响应
│   │   ├── platform.py            # PlatformAccount/Publish 请求/响应
│   │   ├── knowledge.py           # KnowledgeDoc 请求/响应
│   │   └── roi.py                 # ROI 分析响应 schema
│   ├── api/
│   │   ├── __init__.py
│   │   └── v1/
│   │       ├── __init__.py
│   │       ├── router.py          # API v1 总路由
│   │       ├── config.py          # GET/PUT /api/v1/config
│   │       ├── keywords.py        # /api/v1/keywords CRUD + LLM生成
│   │       ├── articles.py        # /api/v1/articles CRUD + 生成+流式+批量ZIP
│   │       ├── optimizations.py   # /api/v1/optimizations CRUD + 优化+流式
│   │       ├── verification.py    # /api/v1/verify 多模型验证（SSE）
│   │       ├── reports.py         # /api/v1/reports ROI/成本/提及率
│   │       ├── workflows.py       # /api/v1/workflows CRUD + 执行+SSE进度
│   │       ├── platforms.py       # /api/v1/platforms 账号管理+发布
│   │       ├── knowledge.py       # /api/v1/knowledge 文件上传+检索
│   │       ├── resources.py       # /api/v1/resources 资源推荐
│   │       └── scoring.py         # /api/v1/scoring 内容评分（SSE）
│   ├── services/
│   │   ├── __init__.py
│   │   ├── llm_factory.py         # async LLM 构建工厂
│   │   ├── llm_service.py         # LLM 调用封装（含缓存、流式、成本记录）
│   │   ├── keyword_service.py     # 关键词生成/挖掘/扩展/聚类业务逻辑
│   │   ├── article_service.py     # 内容生成（多平台模板+多模态）
│   │   ├── optimization_service.py # E-E-A-T/事实密度/Schema/独特性优化
│   │   ├── scoring_service.py     # 内容评分+指标分析
│   │   ├── verify_service.py      # 多模型验证+竞品对比
│   │   ├── roi_service.py         # ROI 分析+成本统计
│   │   ├── workflow_service.py    # 工作流引擎（含进度SSE）
│   │   ├── knowledge_service.py   # 知识库管理（文档上传/分块/检索）
│   │   ├── platform_service.py    # 平台账号+发布管理
│   │   ├── config_service.py      # 应用配置CRUD
│   │   └── progress.py            # 实时进度通知管理器（SSE）
│   ├── prompts/
│   │   ├── __init__.py
│   │   ├── keyword_prompts.py     # 关键词相关 Prompt 模板常量
│   │   ├── article_prompts.py     # 内容生成 Prompt 模板
│   │   ├── optimization_prompts.py # 优化相关 Prompt 模板
│   │   ├── verify_prompts.py      # 验证相关 Prompt 模板
│   │   ├── scoring_prompts.py     # 评分 Prompt 模板
│   │   └── workflow_prompts.py    # 工作流 Prompt 模板
│   └── utils/
│       ├── __init__.py
│       ├── token_estimator.py     # Token 估算
│       └── text_utils.py          # 文本处理工具
├── alembic/
│   ├── env.py                     # Alembic 环境配置（async）
│   └── versions/                  # 迁移脚本目录
├── alembic.ini                    # Alembic 配置文件
├── tests/
│   ├── __init__.py
│   ├── conftest.py                # pytest fixtures（async client, mock DB）
│   ├── test_services/             # 服务层单元测试
│   └── test_api/                  # API 集成测试
├── requirements.txt
├── Dockerfile
└── .env.example
```

### API 设计

#### 配置管理
| 方法 | 路径 | 请求体 | 响应 | 说明 |
|------|------|--------|------|------|
| GET | /api/v1/config | - | AppConfigResponse | 获取当前配置（API Key 掩码） |
| PUT | /api/v1/config | AppConfigUpdate | AppConfigResponse | 更新配置 |
| POST | /api/v1/config/test | ProviderTestRequest | {"success": bool, "message": str} | 测试 LLM 连通性 |

#### 关键词管理
| 方法 | 路径 | 请求体 | 响应 | 说明 |
|------|------|--------|------|------|
| GET | /api/v1/keywords | ?brand=&page=&page_size= | PageResponse[KeywordResponse] | 关键词列表（分页） |
| POST | /api/v1/keywords | KeywordCreate | list[KeywordResponse] | 保存托词工具生成的关键词 |
| DELETE | /api/v1/keywords/{id} | - | {"ok": true} | 删除关键词 |
| POST | /api/v1/keywords/generate | KeywordGenerateRequest (SSE) | text/event-stream | LLM 生成关键词（流式） |
| POST | /api/v1/keywords/mine | KeywordMineRequest (SSE) | text/event-stream | 竞品关键词挖掘（流式） |
| POST | /api/v1/keywords/expand | KeywordExpandRequest (SSE) | text/event-stream | 语义扩展（流式） |
| POST | /api/v1/keywords/cluster | KeywordClusterRequest | TopicClusterResponse | 话题聚类分析 |
| DELETE | /api/v1/keywords | ?brand= | {"deleted": int} | 批量删除关键词 |

#### 文章/内容管理
| 方法 | 路径 | 请求体 | 响应 | 说明 |
|------|------|--------|------|------|
| GET | /api/v1/articles | ?brand=&platform=&page= | PageResponse[ArticleResponse] | 文章列表 |
| GET | /api/v1/articles/{id} | - | ArticleResponse | 获取单篇文章 |
| POST | /api/v1/articles | ArticleCreate | ArticleResponse | 保存文章 |
| PUT | /api/v1/articles/{id} | ArticleUpdate | ArticleResponse | 更新文章 |
| DELETE | /api/v1/articles/{id} | - | {"ok": true} | 删除文章 |
| POST | /api/v1/articles/generate (SSE) | ArticleGenerateRequest | text/event-stream | 单平台内容生成（流式） |
| POST | /api/v1/articles/batch-generate (SSE) | BatchGenerateRequest | text/event-stream | 批量多平台生成（进度流式） |
| GET | /api/v1/articles/batch-download | ?ids= | application/zip | 批量下载为 ZIP |
| POST | /api/v1/articles/{id}/multimodal | MultimodalRequest (SSE) | text/event-stream | 生成配图描述/视频脚本（流式） |

#### 内容优化
| 方法 | 路径 | 请求体 | 响应 | 说明 |
|------|------|--------|------|------|
| GET | /api/v1/optimizations | ?brand=&page= | PageResponse[OptimizationResponse] | 优化记录列表 |
| POST | /api/v1/optimizations/eeat (SSE) | OptimizeRequest | text/event-stream | E-E-A-T 增强（流式） |
| POST | /api/v1/optimizations/fact-density (SSE) | OptimizeRequest | text/event-stream | 事实密度增强（流式） |
| POST | /api/v1/optimizations/schema | SchemaGenerateRequest | SchemaResponse | Schema.org JSON-LD 生成 |
| POST | /api/v1/optimizations/tech-config | TechConfigRequest | TechConfigResponse | 技术配置生成（robots.txt 等） |
| POST | /api/v1/optimizations/uniqueness | UniquenessRequest | UniquenessResponse | 独特性检测 |

#### 内容评分
| 方法 | 路径 | 请求体 | 响应 | 说明 |
|------|------|--------|------|------|
| POST | /api/v1/scoring/score (SSE) | ScoreRequest | text/event-stream | LLM 4维度评分（流式） |
| POST | /api/v1/scoring/metrics | MetricsRequest | MetricsResponse | 规则指标分析（同步） |
| POST | /api/v1/scoring/quick | QuickScoreRequest | QuickScoreResponse | 快速规则评估（同步） |

#### AI 搜索验证
| 方法 | 路径 | 请求体 | 响应 | 说明 |
|------|------|--------|------|------|
| GET | /api/v1/verification/results | ?brand=&page= | PageResponse[VerifyResultResponse] | 验证历史 |
| POST | /api/v1/verification/verify (SSE) | VerifyRequest | text/event-stream | 多模型品牌验证（流式） |
| POST | /api/v1/verification/competitor (SSE) | CompetitorVerifyRequest | text/event-stream | 竞品对比验证（流式） |
| DELETE | /api/v1/verification/results/{id} | - | {"ok": true} | 删除验证记录 |

#### 数据报表
| 方法 | 路径 | 请求体 | 响应 | 说明 |
|------|------|--------|------|------|
| GET | /api/v1/reports/roi | ?brand=&start_date=&end_date= | ROIReportResponse | ROI 分析报告 |
| GET | /api/v1/reports/costs | ?brand=&start_date=&end_date= | CostReportResponse | 成本统计 |
| GET | /api/v1/reports/mentions | ?brand=&start_date=&end_date= | MentionReportResponse | 品牌提及率趋势 |
| GET | /api/v1/reports/kpi | ?brand= | KPIResponse | 首页 KPI 概览 |
| GET | /api/v1/reports/negative | ?brand= | list[NegativeMentionResponse] | 负面监控 |
| GET | /api/v1/reports/optimization-suggestions | ?brand= | list[SuggestionResponse] | 成本优化建议 |

#### 工作流
| 方法 | 路径 | 请求体 | 响应 | 说明 |
|------|------|--------|------|------|
| GET | /api/v1/workflows | ?brand= | list[WorkflowResponse] | 工作流列表 |
| POST | /api/v1/workflows | WorkflowCreateRequest | WorkflowResponse | 创建工作流 |
| PUT | /api/v1/workflows/{id} | WorkflowUpdateRequest | WorkflowResponse | 更新工作流 |
| DELETE | /api/v1/workflows/{id} | - | {"ok": true} | 删除工作流 |
| POST | /api/v1/workflows/{id}/toggle | {"enabled": bool} | WorkflowResponse | 启用/禁用工作流 |
| POST | /api/v1/workflows/{id}/execute (SSE) | WorkflowExecuteRequest | text/event-stream | 执行工作流（进度流式） |
| GET | /api/v1/workflows/{id}/executions | ?page= | PageResponse[WorkflowExecutionResponse] | 执行历史 |
| GET | /api/v1/workflows/templates | - | list[WorkflowTemplateResponse] | 工作流模板列表 |

#### 平台账号与发布
| 方法 | 路径 | 请求体 | 响应 | 说明 |
|------|------|--------|------|------|
| GET | /api/v1/platforms/accounts | ?brand= | list[PlatformAccountResponse] | 平台账号列表 |
| POST | /api/v1/platforms/accounts | PlatformAccountCreate | PlatformAccountResponse | 添加平台账号 |
| PUT | /api/v1/platforms/accounts/{id} | PlatformAccountUpdate | PlatformAccountResponse | 更新账号 |
| DELETE | /api/v1/platforms/accounts/{id} | - | {"ok": true} | 删除账号 |
| POST | /api/v1/platforms/publish/{article_id} | PublishRequest | PublishResponse | 发布文章到平台 |
| GET | /api/v1/platforms/publish-records | ?article_id= | list[PublishRecordResponse] | 发布记录 |
| GET | /api/v1/platforms/supported | - | list[PlatformInfo] | 获取支持的平台列表 |

#### 知识库
| 方法 | 路径 | 请求体 | 响应 | 说明 |
|------|------|--------|------|------|
| GET | /api/v1/knowledge | ?brand=&page= | PageResponse[KnowledgeDocResponse] | 知识库文档列表 |
| POST | /api/v1/knowledge/upload | multipart/form-data | KnowledgeDocResponse | 上传文档（PDF/TXT/DOCX/MD） |
| POST | /api/v1/knowledge/search | KnowledgeSearchRequest | list[KnowledgeChunkResponse] | 检索知识库内容 |
| DELETE | /api/v1/knowledge/{id} | - | {"ok": true} | 删除文档 |

#### 资源库
| 方法 | 路径 | 请求体 | 响应 | 说明 |
|------|------|--------|------|------|
| GET | /api/v1/resources | ?category= | list[ResourceResponse] | 获取推荐资源 |
| GET | /api/v1/resources/techniques | - | list[TechniqueResponse] | 获取 GEO 优化技巧 |
| POST | /api/v1/config-optimizer (SSE) | ConfigOptimizeRequest | text/event-stream | 配置优化建议（流式） |

### SSE 事件格式

所有流式接口统一使用 Server-Sent Events：

```
event: start
data: {"operation": "generate", "total_steps": 3}

event: progress
data: {"step": 1, "message": "正在生成内容...", "progress": 33.3}

event: chunk
data: {"content": "生成的文本片段"}

event: complete
data: {"result": {...完整结果...}, "usage": {"input_tokens": 100, "output_tokens": 200}}

event: error
data: {"code": "LLM_ERROR", "message": "API 调用失败"}
```

### 前端路由设计

| 路由 | 页面组件 | 对应原 Tab | 功能 |
|------|----------|-----------|------|
| / | Dashboard | KPI 总览 | KPI 卡片 + 快捷入口 |
| /keywords | KeywordsPage | Tab1 关键词蒸馏 | 托词工具、LLM 生成、挖掘、扩展、聚类 |
| /articles | ArticlesPage | Tab2 自动创作 | 平台选择、内容生成、批量操作、ZIP下载 |
| /articles/:id | ArticleDetailPage | Tab2 详情 | 单篇文章编辑、多模态描述 |
| /optimize | OptimizePage | Tab3 文章优化 | E-E-A-T/事实密度/Schema/技术配置/独特性 |
| /verify | VerifyPage | Tab4 多模型验证 | 多模型验证、竞品对比 |
| /history | HistoryPage | Tab5 历史记录 | 所有历史数据查看/筛选/导出 |
| /reports | ReportsPage | Tab6 AI 数据报表 | ROI/成本/提及率图表、负面监控 |
| /workflows | WorkflowsPage | Tab7 工作流自动化 | 工作流 CRUD、执行、进度监控 |
| /resources | ResourcesPage | Tab8 GEO 资源库 | 资源推荐、优化技巧 |
| /platforms | PlatformsPage | Tab9 平台同步 | 账号管理、文章发布 |
| /config-optimizer | ConfigOptimizerPage | Tab10 配置优化助手 | AI 辅助配置诊断 |
| /knowledge | KnowledgePage | Tab11 品牌知识库 | 文件上传、文档管理、检索 |
| /settings | SettingsPage | 侧边栏配置 | LLM 配置、品牌信息、高级设置 |

### 迁移映射表

| 原模块 | 新位置 | 改动类型 |
|--------|--------|---------|
| geo_tool.py | backend/app/main.py + frontend/ | 重写（入口→FastAPI，UI→React） |
| modules/data_storage.py | backend/app/models/ + backend/app/core/database.py | 重写（裸SQL→SQLAlchemy async ORM） |
| modules/llm_factory.py | backend/app/services/llm_factory.py | async 改造 |
| modules/chat_doubao.py | backend/app/services/chat_doubao.py | async 改造（增加 _agenerate） |
| modules/keyword_tool.py | backend/app/services/keyword_service.py（部分） | 直接迁移（纯逻辑） |
| modules/keyword_mining.py | backend/app/services/keyword_service.py（部分） | async 改造（requests→httpx.AsyncClient） |
| modules/semantic_expander.py | backend/app/services/keyword_service.py（部分） | async 改造 |
| modules/keyword_data_enhancer.py | backend/app/services/keyword_service.py（部分） | async 改造 |
| modules/content_scorer.py | backend/app/services/scoring_service.py | async 改造 |
| modules/content_metrics.py | backend/app/services/scoring_service.py | 直接迁移 |
| modules/content_uniqueness.py | backend/app/services/optimization_service.py | 直接迁移 |
| modules/eeat_enhancer.py | backend/app/services/optimization_service.py | async 改造 + Prompt 提取 |
| modules/fact_density_enhancer.py | backend/app/services/optimization_service.py | async 改造 + Prompt 提取 |
| modules/schema_generator.py | backend/app/services/optimization_service.py | async 改造 |
| modules/topic_cluster.py | backend/app/services/keyword_service.py（部分） | async 改造 |
| modules/knowledge_base.py | backend/app/services/knowledge_service.py | async 改造 |
| modules/ai_search_verifier.py | backend/app/services/verify_service.py | async 改造 + SSE |
| modules/roi_analyzer.py | backend/app/services/roi_service.py | 直接迁移 |
| modules/workflow_automation.py | backend/app/services/workflow_service.py | async 改造 + 进度通知 |
| modules/multimodal_prompt.py | backend/app/services/article_service.py（部分） | async 改造 + Prompt 提取 |
| modules/optimization_techniques.py | backend/app/services/optimization_service.py（资源部分） | 直接迁移 |
| modules/config_optimizer.py | backend/app/services/config_service.py | async 改造 |
| modules/negative_monitor.py | backend/app/services/verify_service.py（部分） | async 改造 |
| modules/resource_recommender.py | backend/app/services/resource_service.py（新建） | 直接迁移 |
| modules/technical_config_generator.py | backend/app/services/optimization_service.py | 直接迁移 |
| platform_sync/*.py | backend/app/services/platform_service.py | async 改造（httpx） |
| modules/ui/*.py | frontend/src/pages/ + frontend/src/components/ | 完全重写（Streamlit→React+AntD） |
