# 数据存储与备份恢复指南

> 本文档适用于当前架构（FastAPI 后端 + SQLAlchemy ORM + SQLite + ChromaDB 向量库）。
> 早期基于 Streamlit + `modules/data_storage.py` 的存储方案已废弃，请勿参考。

---

## 一、技术栈与存储总览

### 当前技术栈

| 层 | 技术 | 说明 |
|----|------|------|
| 后端框架 | FastAPI + Uvicorn | 异步 ASGI 服务 |
| ORM | SQLAlchemy 2.0 (async) + Alembic | 异步 ORM + 数据库迁移 |
| 关系数据库 | SQLite（默认，`aiosqlite` 驱动） | 可切换 PostgreSQL（`asyncpg`） |
| 向量数据库 | ChromaDB（嵌入式持久化） | 知识库语义检索，无需独立服务 |
| 文件存储 | 本地文件系统目录 | 知识库文档、上传文件 |
| LLM 集成 | LangChain（DeepSeek / OpenAI / Groq / 通义 / Kimi / 豆包 / 文心） | 通过 `app/services/llm_factory.py` 统一构建 |

### 数据存储位置

系统在运行时使用三类持久化存储，均位于后端工作目录（`backend/`）下：

| 存储类型 | 本地开发路径 | Docker 容器路径 | 对应配置项 |
|----------|-------------|----------------|-----------|
| SQLite 数据库 | `backend/geo_data.db` | `/app/data/geo_app.db` | `DATABASE_URL` |
| ChromaDB 向量库 | `backend/data/chroma_db/` | `/app/data/chroma_db/` | 代码内固定 `./data/chroma_db` |
| 知识库文档文件 | `backend/knowledge_base/` | `/app/knowledge_base/` | `KNOWLEDGE_DIR` |
| 上传文件目录 | `backend/uploads/` | `/app/uploads/` | `UPLOAD_DIR` |

> 说明：本地开发时 `DATABASE_URL` 默认为 `sqlite+aiosqlite:///./geo_data.db`；Docker 环境下改为 `/app/data/geo_app.db`。ChromaDB 路径在 `app/services/knowledge_service.py` 中固定为 `./data/chroma_db`，开发时即 `backend/data/chroma_db`，容器内即 `/app/data/chroma_db`。

### SQLite 数据库表

数据库由 Alembic 迁移管理（`backend/alembic/versions/`），主要业务表包括：

- `keywords` — 关键词
- `articles` / `article_versions` — 文章及版本
- `optimizations` — 优化记录
- `verify_results` — AI 验证结果
- `api_calls` — LLM 调用与成本记录
- `workflows` / `workflow_executions` / `workflow_templates` — 工作流
- `platform_accounts` / `publish_records` — 平台账号与发布记录
- `knowledge_docs` — 知识库文档元数据（正文存于文件）
- `monitor_tasks` / `monitor_results` — 监控任务与结果
- `app_config` — 应用配置（单行 JSON）
- `audit_logs` — 操作审计日志

### 配置入口

所有存储相关配置通过环境变量 / `.env` 文件读取，定义在 `backend/app/core/config.py`（Pydantic Settings），参考 `backend/.env.example`。

---

## 二、备份方法

### 方法 1：SQLite 数据库文件复制（最简单）

适用于停机窗口可接受或低并发场景。SQLite 是单文件数据库，直接复制文件即可完成物理备份。

```bash
# 进入后端目录
cd backend

# 方式 A：直接复制数据库文件（建议先停掉后端服务，避免写入冲突）
cp geo_data.db "geo_data.db.bak.$(date +%Y%m%d_%H%M%S)"

# 方式 B：使用 SQLite 在线备份（无需停机，推荐）
sqlite3 geo_data.db ".backup 'geo_data.db.bak.$(date +%Y%m%d_%H%M%S)'"
```

要点：
- **直接复制文件前请停止后端服务**，或在低写入时段操作，避免得到损坏的中间状态文件。
- 推荐使用 `sqlite3 .backup` 命令，它能在数据库被使用时安全地生成一致性快照。
- 备份文件建议存放到独立目录或异地存储，不要放在 `backend/` 下（避免误提交版本库）。

### 方法 2：通过 API 导出 JSON（逻辑备份，推荐）

系统提供 `GET /api/v1/data/export/all` 接口，将全部业务数据导出为结构化 JSON 文件。该方式跨数据库引擎通用（SQLite / PostgreSQL 均可），且对运行中的服务无侵入。

```bash
# 设置 API Key（若启用了认证）
API_KEY="your-secret-api-key"
BASE_URL="http://localhost:8000/api/v1"

# 全量导出 JSON
curl -H "X-API-Key: $API_KEY" \
  "$BASE_URL/data/export/all" \
  -o "geo_backup_$(date +%Y%m%d_%H%M%S).json"
```

导出内容涵盖：`keywords`、`articles`、`article_versions`、`optimizations`、`verify_results`、`workflows`、`workflow_templates`、`platform_accounts`（密钥字段已掩码）、`monitor_tasks`、`knowledge_docs`（仅元数据，不含正文）。

补充：按模块导出 CSV（适合用 Excel 查看）：

```bash
# 支持的模块：keywords / articles / verify_results / api_calls
curl -H "X-API-Key: $API_KEY" \
  "$BASE_URL/data/export/csv/keywords" \
  -o "keywords_$(date +%Y%m%d_%H%M%S).csv"
```

查看当前存储用量统计：

```bash
curl -H "X-API-Key: $API_KEY" "$BASE_URL/data/storage"
```

> 接口定义见 `backend/app/api/v1/data.py`，服务实现见 `backend/app/services/data_service.py`。

### 方法 3：ChromaDB 向量库目录复制

知识库的向量索引由 ChromaDB 以嵌入式方式持久化在 `backend/data/chroma_db/` 目录。备份时直接复制整个目录即可。

```bash
cd backend

# 复制整个 ChromaDB 目录（建议先停止后端服务）
cp -r data/chroma_db "data/chroma_db.bak.$(date +%Y%m%d_%H%M%S)"
```

要点：
- ChromaDB 目录与 `knowledge_base/` 文件目录**配套备份**：向量索引依赖原始文档，二者缺一不可。
- 若仅复制了 `knowledge_base/` 文件，可在恢复后调用知识库重建索引功能重新生成向量（见下文恢复说明）。

### 完整备份建议（三者结合）

一次完整的备份应同时包含：

1. SQLite 数据库文件（或 JSON 导出）—— 业务数据
2. `backend/knowledge_base/` 目录 —— 知识库原始文档
3. `backend/data/chroma_db/` 目录 —— 向量索引（可选，可重建）
4. `backend/uploads/` 目录 —— 已上传的附件文件

示例脚本（本地开发）：

```bash
#!/bin/bash
# backup_geo.sh - GEO 平台完整备份脚本
BACKUP_DIR="backups/$(date +%Y%m%d_%H%M%S)"
mkdir -p "$BACKUP_DIR"

cd backend

# 1. SQLite 数据库（在线备份）
sqlite3 geo_data.db ".backup '../$BACKUP_DIR/geo_data.db'"

# 2. 知识库文档
cp -r knowledge_base "../$BACKUP_DIR/knowledge_base"

# 3. ChromaDB 向量库
cp -r data/chroma_db "../$BACKUP_DIR/chroma_db"

# 4. 上传文件
cp -r uploads "../$BACKUP_DIR/uploads" 2>/dev/null || true

echo "备份完成: $BACKUP_DIR"
```

---

## 三、恢复方法

### 恢复方法 1：SQLite 数据库文件还原

```bash
cd backend

# 停止后端服务
# （Ctrl+C 停止 uvicorn，或通过进程管理工具停止）

# 用备份文件覆盖当前数据库
cp geo_data.db.bak.YYYYMMDD_HHMMSS geo_data.db

# 重新启动后端服务
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### 恢复方法 2：通过 API 导入 JSON

使用 `POST /api/v1/data/import` 接口，将此前导出的 JSON 文件回灌。支持三种冲突策略：

- `skip`（默认）：跳过已存在的主键记录
- `overwrite`：覆盖已存在的记录
- `append`：始终作为新记录插入

```bash
API_KEY="your-secret-api-key"
BASE_URL="http://localhost:8000/api/v1"
BACKUP_FILE="geo_backup_YYYYMMDD_HHMMSS.json"

# 先启动一个空库的后端服务，并执行迁移
cd backend && alembic upgrade head && uvicorn app.main:app --reload

# 通过 API 导入（使用 python 构造请求体）
python -c "
import json, requests
data = json.load(open('$BACKUP_FILE', encoding='utf-8'))
resp = requests.post(
    '$BASE_URL/data/import',
    headers={'X-API-Key': '$API_KEY', 'Content-Type': 'application/json'},
    json={'data': data, 'strategy': 'skip'},
)
print(resp.json())
"
```

> 注意：`platform_accounts` 表中的密钥类字段在导出时已被掩码，导入后需要在前端「平台同步」页面重新填写真实的 API 凭据。

### 恢复方法 3：ChromaDB 向量库还原

```bash
cd backend

# 停止后端服务后，用备份目录覆盖
rm -rf data/chroma_db
cp -r data/chroma_db.bak.YYYYMMDD_HHMMSS data/chroma_db

# 同时恢复知识库原始文档
rm -rf knowledge_base
cp -r ../backups/YYYYMMDD_HHMMSS/knowledge_base knowledge_base

# 重启服务
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

若向量库丢失但 `knowledge_base/` 原始文档仍在，可通过知识库服务提供的重建索引功能重新生成向量（`KnowledgeService._reindex_all()` 会读取所有文档重新分块并向量化）。

---

## 四、Docker 环境下的备份与恢复

### Docker 卷挂载说明

`docker-compose.yml` 定义了三个命名卷，分别承载不同存储：

| 卷名 | 容器路径 | 承载内容 |
|------|---------|---------|
| `backend_data` | `/app/data` | SQLite 数据库（`geo_app.db`）+ ChromaDB 向量库（`chroma_db/`） |
| `uploads` | `/app/uploads` | 上传的附件文件 |
| `knowledge_data` | `/app/knowledge_base` | 知识库原始文档 |

> Docker 中 `DATABASE_URL=sqlite+aiosqlite:////app/data/geo_app.db`，ChromaDB 路径 `./data/chroma_db` 解析为 `/app/data/chroma_db`，二者都落在 `backend_data` 卷内。

### 使用 docker cp 备份

```bash
# 1. 备份 SQLite 数据库（从 backend_data 卷）
docker cp geo-backend:/app/data/geo_app.db ./geo_app.db.bak.$(date +%Y%m%d_%H%M%S)

# 2. 备份 ChromaDB 向量库
docker cp geo-backend:/app/data/chroma_db ./chroma_db.bak.$(date +%Y%m%d_%H%M%S)

# 3. 备份知识库文档（从 knowledge_data 卷）
docker cp geo-backend:/app/knowledge_base ./knowledge_base.bak.$(date +%Y%m%d_%H%M%S)

# 4. 备份上传文件（从 uploads 卷）
docker cp geo-backend:/app/uploads ./uploads.bak.$(date +%Y%m%d_%H%M%S)
```

### 使用 docker cp 恢复

```bash
# 恢复前建议先停止容器
docker compose stop backend

# 1. 恢复 SQLite 数据库
docker cp ./geo_app.db.bak.YYYYMMDD_HHMMSS geo-backend:/app/data/geo_app.db

# 2. 恢复 ChromaDB 向量库
docker cp ./chroma_db.bak.YYYYMMDD_HHMMSS/. geo-backend:/app/data/chroma_db/

# 3. 恢复知识库文档
docker cp ./knowledge_base.bak.YYYYMMDD_HHMMSS/. geo-backend:/app/knowledge_base/

# 4. 恢复上传文件
docker cp ./uploads.bak.YYYYMMDD_HHMMSS/. geo-backend:/app/uploads/

# 重启服务
docker compose start backend
```

### 使用 docker volume 直接操作卷

```bash
# 查看卷的实际存储路径
docker volume inspect geo-platform_backend_data

# 备份整个卷（tar 打包）
docker run --rm -v geo-platform_backend_data:/data -v $(pwd):/backup \
  alpine tar czf /backup/backend_data.tar.gz -C /data .

# 恢复整个卷
docker run --rm -v geo-platform_backend_data:/data -v $(pwd):/backup \
  alpine sh -c "rm -rf /data/* && tar xzf /backup/backend_data.tar.gz -C /data"
```

### Docker 环境下的 API 逻辑备份

容器内服务正常运行时，同样可通过 API 导出 JSON，无需进入容器：

```bash
API_KEY="your-secret-api-key"

# 通过映射的端口访问后端 API
curl -H "X-API-Key: $API_KEY" \
  "http://localhost:8000/api/v1/data/export/all" \
  -o "geo_backup_$(date +%Y%m%d_%H%M%S).json"
```

---

## 五、数据清理与维护

### 清理历史数据

通过 `POST /api/v1/data/cleanup` 可删除指定表中早于 N 天的记录，支持清理的表：`api_calls`、`verify_results`、`workflow_executions`、`monitor_results`。

```bash
curl -X POST -H "X-API-Key: $API_KEY" -H "Content-Type: application/json" \
  "$BASE_URL/data/cleanup" \
  -d '{"days": 90, "tables": ["api_calls", "workflow_executions"]}'
```

### 查看审计日志

所有导出 / 导入 / 清理操作都会写入 `audit_logs` 表，可通过 `GET /api/v1/data/audit-logs` 查询。

### 数据库迁移

修改 `backend/app/models/` 中的 ORM 模型后，使用 Alembic 生成并应用迁移：

```bash
cd backend

# 生成迁移脚本
alembic revision --autogenerate -m "描述改动"

# 应用迁移
alembic upgrade head

# 回滚一个版本
alembic downgrade -1
```

---

## 六、切换到 PostgreSQL（可选）

生产环境或高并发场景可将 SQLite 切换为 PostgreSQL：

1. 修改 `.env` 中的 `DATABASE_URL`：
   ```env
   DATABASE_URL=postgresql+asyncpg://user:password@localhost:5432/geo_db
   ```
2. 安装驱动：`pip install asyncpg`
3. 执行迁移：`alembic upgrade head`
4. 数据迁移：先用 API 从 SQLite 导出 JSON，再切换连接串后通过 API 导入。

> ChromaDB 与文件存储路径不受数据库切换影响。

---

## 七、备份频率建议

| 数据类型 | 建议频率 | 保留策略 |
|----------|---------|---------|
| SQLite 数据库 / JSON 导出 | 每日 1 次 | 保留 30 天 |
| 知识库文档目录 | 每周 1 次或变更时 | 保留 4 周 |
| ChromaDB 向量库 | 每周 1 次 | 保留 4 周（可重建） |
| 上传文件目录 | 每周 1 次 | 保留 4 周 |

建议将物理备份（文件复制）与逻辑备份（JSON 导出）结合使用：物理备份恢复快，逻辑备份跨引擎且可校验数据完整性。
