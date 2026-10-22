# 后端服务（FastAPI）

## 目录结构

```
backend/
├── app/
│   ├── __init__.py
│   ├── main.py                 # FastAPI 应用入口（lifespan、CORS、中间件、路由注册）
│   ├── api/
│   │   ├── deps.py             # FastAPI 依赖注入（所有 Service 的工厂函数）
│   │   ├── sse.py              # SSE 流式响应工具（格式化、错误处理、keep-alive）
│   │   └── v1/                 # v1 API 路由（16个模块）
│   │       ├── router.py       # 总路由（聚合所有子路由）
│   │       ├── config.py       # 应用配置读取/更新
│   │       ├── keywords.py     # 关键词 CRUD / 生成 / 挖掘 / 扩展 / 聚类
│   │       ├── articles.py     # 文章 CRUD / 生成 / 批量 / 版本 / 下载 / 搜索
│   │       ├── optimizations.py # E-E-A-T / 事实密度 / Schema 优化
│   │       ├── verification.py # 多模型品牌验证 / 竞品验证
│   │       ├── scoring.py      # 内容评分
│   │       ├── dds.py          # DDS 三维评分
│   │       ├── workflows.py    # 工作流 CRUD / 执行
│   │       ├── knowledge.py    # 知识库文档上传 / 搜索 / 删除
│   │       ├── platforms.py    # 平台账号 / 文章发布
│   │       ├── monitor.py      # 监控任务 CRUD / 执行
│   │       ├── reports.py      # 报表数据（KPI / 成本 / 提及率）
│   │       ├── data.py         # 数据导出 / 导入 / 清理 / 存储统计 / 审计日志
│   │       ├── templates.py    # 平台模板 CRUD / 导入导出
│   │       ├── resources.py    # 资源/工具接口
│   │       ├── schema_tools.py # Schema 生成工具
│   │       └── attribution.py  # ROI 归因
│   ├── core/
│   │   ├── config.py           # Pydantic Settings（环境变量读取）
│   │   ├── database.py         # SQLAlchemy 异步引擎 / Session 工厂
│   │   ├── exceptions.py       # 层级化异常体系（10+ 异常类）
│   │   ├── cache.py            # 线程安全 LRU + TTL 内存缓存
│   │   ├── scheduler.py        # APScheduler 定时任务调度
│   │   ├── security.py         # API Key 常量时间认证
│   │   └── logging.py          # 结构化日志配置
│   ├── models/                 # SQLAlchemy ORM 模型（15个表）
│   ├── schemas/                # Pydantic v2 请求/响应模型
│   ├── services/               # 业务逻辑服务（20个）
│   ├── prompts/                # LLM Prompt 模板（7个模块）
│   └── utils/
│       ├── llm_errors.py       # LLM 错误分类 / 速率限制 / 指数退避重试
│       ├── prompt_guard.py     # Prompt 注入检测 / 输入长度校验
│       ├── text_utils.py       # 文本工具（JSON提取、Key打码等）
│       ├── token_estimator.py  # Token 估算（中英混合）
│       └── diff_utils.py       # 版本差异计算（HTML diff）
├── alembic/                    # 数据库迁移
│   └── versions/               # 迁移脚本（001~004）
├── alembic.ini
├── tests/                      # pytest 测试
├── Dockerfile
├── pytest.ini
└── requirements.txt
```

## 开发环境搭建

```bash
cd backend

# 创建虚拟环境
python3 -m venv .venv
source .venv/bin/activate

# 安装依赖
pip install -r requirements.txt

# 运行数据库迁移（自动创建表）
alembic upgrade head

# 启动开发服务器（热重载）
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

启动后：
- API 地址：`http://localhost:8000/api/v1`
- 交互式文档（Swagger UI）：`http://localhost:8000/docs`
- ReDoc 文档：`http://localhost:8000/redoc`
- 健康检查：`http://localhost:8000/health`

## 数据库迁移

```bash
# 生成新迁移（在修改 models/ 后执行）
alembic revision --autogenerate -m "描述改动"

# 升级到最新版本
alembic upgrade head

# 回滚一个版本
alembic downgrade -1
```

## 添加新的 LLM 提供商

1. 在 `app/services/llm_factory.py` 中添加 `build_xxx()` 函数
2. 在 `build_llm()` 中添加分支
3. 在 `get_default_model()` 中添加默认模型名
4. 在 `get_supported_providers()` 中添加提供商显示名

## API 认证

所有 `/api/v1/*` 端点（除 `/health` 和 `/`）需要 X-API-Key 请求头：

```bash
curl -H "X-API-Key: your-secret-key" http://localhost:8000/api/v1/config
```

未配置 `API_KEY` 环境变量时，认证跳过（开发模式）。

## 核心服务说明

| 服务 | 职责 |
|------|------|
| `LLMService` | 统一 LLM 调用（超时/重试/速率限制/缓存/成本记录） |
| `ArticleService` | 文章 CRUD / 生成 / 批量 / 版本管理 |
| `KeywordService` | 关键词 CRUD / 生成 / 语义扩展 / 聚类 |
| `VerifyService` | 多模型品牌验证 / 情感分析 / 失败诊断 |
| `OptimizationService` | E-E-A-T / 事实密度 / Schema 优化 |
| `KnowledgeService` | 知识库文档管理 / ChromaDB 向量搜索 |
| `WorkflowService` | 工作流编排 / 定时执行 |
| `MonitorService` | AI 搜索监控任务执行 |
| `DataService` | 数据导出/导入/清理/审计日志 |
| `TemplateService` | 平台内容模板管理 |
| `ConfigService` | 应用配置持久化（单表 JSON） |
| `ROIService` | API 成本计算 |

## 异常体系

```
GEOAppException (基础异常，code/message/status_code)
├── ConfigError           配置错误 (400)
├── AuthError             认证失败 (401)
├── NotFoundError         资源不存在 (404)
├── ValidationError       参数校验失败 (422)
├── LLMError              LLM 调用失败基类 (502)
│   ├── LLMAuthError      API Key 无效
│   ├── LLMBalanceError   余额不足
│   ├── LLMTimeoutError   请求超时
│   ├── LLMRateLimitError 速率限制
│   ├── LLMModelNotFoundError 模型不存在
│   └── LLMNetworkError   网络错误
├── FileError             文件操作错误 (400)
└── WorkflowError         工作流错误 (500)
```

## 环境变量

| 变量 | 说明 | 默认值 |
|------|------|--------|
| `DATABASE_URL` | 数据库连接串 | `sqlite+aiosqlite:///./data/app.db` |
| `API_KEY` | API 认证密钥 | 空（不启用认证） |
| `CORS_ORIGINS` | CORS 允许源（逗号分隔） | `http://localhost:5173,http://localhost:3000` |
| `DEBUG` | 调试模式（SQL 日志） | `false` |
| `LLM_CACHE_ENABLED` | LLM 缓存开关 | `true` |
| `LLM_CACHE_TTL_SECONDS` | 缓存 TTL | `3600` |
| `LLM_CACHE_MAX_SIZE` | 缓存最大条目 | `1000` |
| `UPLOAD_DIR` | 上传文件目录 | `./uploads` |
| `KNOWLEDGE_DIR` | 知识库文件目录 | `./knowledge_data` |
| `MAX_UPLOAD_SIZE` | 最大上传大小（字节） | `10485760`（10MB） |
| `USD_TO_CNY_RATE` | 美元兑人民币汇率 | `7.2` |
