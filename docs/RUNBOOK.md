# 运维手册

本文档描述 GEO 平台日常运维操作流程、故障排查、监控告警与应急处理。

## 目录

- [服务概览](#服务概览)
- [日常操作](#日常操作)
  - [启动服务](#启动服务)
  - [停止服务](#停止服务)
  - [重启服务](#重启服务)
  - [查看日志](#查看日志)
- [健康检查](#健康检查)
- [数据备份与恢复](#数据备份与恢复)
- [常见故障排查](#常见故障排查)
- [LLM 供应商错误对照表](#llm-供应商错误对照表)
- [定时任务管理](#定时任务管理)
- [版本升级](#版本升级)
- [数据清理](#数据清理)
- [审计日志](#审计日志)
- [性能监控指标](#性能监控指标)

---

## 服务概览

| 服务     | 容器名         | 默认端口 | 说明                   |
|----------|----------------|----------|------------------------|
| 后端 API | `geo-backend`  | 8000     | FastAPI + SQLite/PG    |
| 前端 Web | `geo-frontend` | 80       | Nginx 静态托管 + 代理   |

**数据卷（Docker）：**

| 卷名            | 容器路径               | 说明         |
|-----------------|------------------------|--------------|
| `backend_data`  | `/app/data`            | 数据库、ChromaDB 向量库 |
| `uploads`       | `/app/uploads`         | 上传文件（知识库文档） |

---

## 日常操作

### 启动服务

```bash
# Docker Compose 方式（推荐）
cd /path/to/project
docker compose up -d

# 指定环境变量文件
API_KEY=your-secret-key CORS_ORIGINS=https://yourdomain.com docker compose up -d
```

首次启动会自动执行：
1. 数据库迁移（Alembic head）
2. 平台模板初始化（写入默认模板）
3. 调度器启动（加载已有定时任务）

### 停止服务

```bash
# 安全停止（等待请求完成）
docker compose stop

# 停止并删除容器（数据卷保留）
docker compose down
```

> **注意**：`docker compose down -v` 会删除所有数据卷，导致数据丢失，生产环境严禁使用。

### 重启服务

```bash
# 重启所有服务
docker compose restart

# 仅重启后端（代码更新后通常只需重启后端）
docker compose restart backend

# 仅重启前端（Nginx 配置变更后）
docker compose restart frontend
```

### 查看日志

```bash
# 查看所有服务日志（实时跟踪）
docker compose logs -f

# 仅查看后端日志
docker compose logs -f backend

# 仅查看前端/Nginx 日志
docker compose logs -f frontend

# 查看最近 100 行后端日志
docker compose logs --tail=100 backend

# 查看包含关键词的日志
docker compose logs backend 2>&1 | grep -i "error"
```

**日志级别说明（后端）：**
- `INFO`：正常启动/关闭、任务调度、LLM 调用成功
- `WARNING`：模板种子失败、调度器启动异常、单条任务失败（不影响整体）
- `ERROR`：未捕获异常、LLM 连续重试失败、数据库错误

---

## 健康检查

### 手动健康检查

```bash
# 后端健康检查
curl -s http://localhost:8000/health
# 预期返回: {"status":"ok","version":"x.x.x"}

# 根路径信息
curl -s http://localhost:8000/
# 预期返回: {"app":"GEO Platform","version":"x.x.x","docs":"/docs"}

# 前端可用性检查
curl -s -o /dev/null -w "%{http_code}" http://localhost:
# 预期返回: 200
```

### Docker 自动健康检查

后端容器内置 healthcheck（每 30 秒检测 `/health`，超时 10 秒，失败 3 次标记为 unhealthy）：

```bash
# 查看容器健康状态
docker compose ps
#  unhealthy 状态说明后端已故障
```

```bash
# 查看健康检查历史
docker inspect geo-backend --format='{{json .State.Health}}' | python3 -m json.tool
```

### 健康状态异常处理

若后端 `unhealthy`：
1. 查看日志：`docker compose logs --tail=200 backend`
2. 常见原因：数据库文件损坏、端口冲突、内存不足、API Key 配置错误
3. 尝试重启：`docker compose restart backend`
4. 如仍失败，参照[故障排查](#常见故障排查)章节

---

## 数据备份与恢复

### 备份内容

需要备份的数据：
- SQLite 数据库：`backend_data` 卷中的 `geo_app.db`
- ChromaDB 向量库：`backend_data` 卷中的 `chroma/` 目录
- 上传文件：`uploads` 卷中的所有文件

### 自动备份脚本

```bash
#!/bin/bash
# backup.sh - 每日备份脚本，建议加入 crontab

set -euo pipefail

BACKUP_DIR="/path/to/backups"
DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="$BACKUP_DIR/geo_backup_$DATE.tar.gz"
KEEP_DAYS=30

mkdir -p "$BACKUP_DIR"

# 使用 docker run 挂载卷进行备份（无需停止服务）
docker run --rm \
  -v backend_data:/data/backend \
  -v uploads:/data/uploads \
  -v "$BACKUP_DIR":/backup \
  alpine tar czf "/backup/geo_backup_$DATE.tar.gz" -C /data .

# 删除超过保留天数的备份
find "$BACKUP_DIR" -name "geo_backup_*.tar.gz" -mtime +$KEEP_DAYS -delete

echo "Backup completed: $BACKUP_FILE"
```

```bash
# 加入 crontab（每天凌晨 3 点执行）
crontab -e
# 添加: 0 3 * * * /path/to/backup.sh >> /var/log/geo-backup.log 2>&1
```

### 手动备份

```bash
# 方式一：停止服务后直接打包（一致性最好）
docker compose stop
docker run --rm \
  -v backend_data:/data/backend \
  -v uploads:/data/uploads \
  -v $(pwd):/backup \
  alpine tar czf /backup/geo_manual_backup.tar.gz -C /data .
docker compose start

# 方式二：通过应用 API 导出 JSON（无需停止，适合逻辑备份）
curl -H "X-API-Key: your-api-key" \
  http://localhost:8000/api/v1/data/export/all \
  -o geo_data_export.json
```

### 数据恢复

```bash
# 从 tar.gz 备份恢复（先停止服务）
docker compose down

docker run --rm \
  -v backend_data:/data/backend \
  -v uploads:/data/uploads \
  -v $(pwd):/backup \
  alpine sh -c "cd /data && tar xzf /backup/geo_manual_backup.tar.gz"

docker compose up -d

# 验证恢复
curl -s http://localhost:8000/health
```

> 恢复后建议在前端检查关键词、文章、平台账号等数据是否完整。

---

## 常见故障排查

### 1. 前端页面无法访问（502/连接拒绝）

**症状：** 浏览器访问显示 502 Bad Gateway 或无法连接。

**排查步骤：**
```bash
# 1. 检查容器是否运行
docker compose ps
# geo-frontend 状态应为 Up

# 2. 检查后端是否健康
curl -s http://localhost:8000/health
# 若失败，后端未启动导致 Nginx 代理失败

# 3. 检查 Nginx 配置
docker compose exec frontend nginx -t

# 4. 检查端口占用
ss -tlnp | grep -E ':(80|8000)\s'
```

**常见原因：**
- 后端容器启动失败（见后端排查）
- 80 端口被其他服务占用：修改 `.env` 中 `FRONTEND_PORT=8080`
- 防火墙未放行端口

---

### 2. 后端启动失败 / 持续重启

**症状：** `docker compose ps` 中 backend 状态为 `Restarting` 或 `unhealthy`。

**排查步骤：**
```bash
# 查看启动日志
docker compose logs --tail=100 backend
```

**常见原因与解决：**

| 日志关键词 | 原因 | 解决方法 |
|-----------|------|---------|
| `database is locked` | SQLite 文件锁冲突 | 检查是否有多个后端实例同时写入，或文件权限问题 |
| `no such table` | 数据库未迁移 | `docker compose exec backend alembic upgrade head` |
| `Permission denied` | 数据卷权限问题 | `docker run --rm -v backend_data:/data alpine chmod -R 755 /data` |
| `Address already in use` | 端口被占用 | 修改 `BACKEND_PORT` 环境变量 |
| `Could not connect to scheduler` | APScheduler 初始化失败（非致命） | 通常会自动降级，检查是否安装了 apscheduler 依赖 |

---

### 3. LLM 调用失败（生成/优化/验证无响应）

**症状：** 生成文章时报错，提示模型调用失败。

**排查步骤：**
1. 打开浏览器开发者工具 → Network 面板，查看 SSE 请求响应状态
2. 检查后端日志中的错误信息：
```bash
docker compose logs backend 2>&1 | grep -iE "error|llm|timeout|auth|rate"
```

**按错误类型处理：**

| 错误类型 | 提示信息 | 处理方法 |
|---------|---------|---------|
| 认证失败 (auth) | "API Key 无效/已过期" | 检查平台账号中的 API Key 是否正确、余额是否充足 |
| 余额不足 (balance) | "账户余额不足" | 前往 LLM 供应商控制台充值 |
| 请求超时 (timeout) | "请求超时" | 检查网络连接，或稍后重试；连续超时需检查供应商服务状态 |
| 频率限制 (rate_limit) | "请求频率超限" | 系统已内置 1 秒间隔限流，若仍触发请等待自动重试（2次指数退避） |
| 模型不存在 (model_not_found) | "模型不存在" | 检查默认模型配置，确认模型名称是否正确（区分大小写） |
| 网络错误 (network) | "网络连接异常" | 检查服务器能否访问对应 API 域名（DNS/防火墙/代理） |

**网络连通性测试（在后端容器内）：**
```bash
docker compose exec backend sh -c "curl -s -o /dev/null -w '%{http_code}' https://api.deepseek.com/v1/models"
# 应返回 401（认证失败说明网络连通）；若返回 000 则网络不通
```

---

### 4. 知识库文档上传后无法检索

**症状：** 上传了文档但生成时不引用知识库内容。

**排查步骤：**
```bash
# 1. 检查文件是否存储在 uploads 卷
docker compose exec backend ls -la /app/uploads/

# 2. 检查 ChromaDB 数据是否存在
docker compose exec backend ls -la /app/data/chroma/ 2>/dev/null

# 3. 查看后端日志是否有解析错误
docker compose logs backend 2>&1 | grep -iE "upload|chroma|parse|embedding"
```

**常见原因：**
- 文件格式不支持（仅支持 txt/md/pdf/docx）
- PDF 解析依赖缺失（需安装 `pdfplumber`，通常已包含）
- 文件为空或内容全是图片（OCR 暂不支持）
- 文档分块后无有效文本内容

---

### 5. SSE 流式响应中断

**症状：** 生成过程中进度条卡在某个百分比后报错。

**排查步骤：**
1. 检查 Nginx 超时配置是否正确（默认已配置 `proxy_read_timeout 600s`）
2. 检查浏览器控制台是否有网络错误
3. 后端日志是否有 `CancelledError` 或 `asyncio.TimeoutError`

**常见原因：**
- 单次 LLM 调用超过 60 秒超时（正常现象，系统会自动重试）
- 验证模型调用超过 90 秒超时（大型模型/长文本）
- 浏览器页面关闭/刷新导致连接断开（正常）
- Nginx 代理层超时（若自定义 Nginx 配置需确保 `proxy_read_timeout` 足够大）

---

### 6. 定时任务未执行

**症状：** 设定了定时工作流，但到时间没有触发。

**排查步骤：**
```bash
# 1. 查看调度器是否正常启动
docker compose logs backend 2>&1 | grep -i "scheduler"

# 2. 通过 API 查看执行记录
curl -s -H "X-API-Key: your-api-key" \
  "http://localhost:8000/api/v1/workflows?page=1&page_size=5" | python3 -m json.tool

# 3. 检查任务状态是否为 enabled
```

**常见原因：**
- 工作流被设置为 `enabled: false`（禁用状态）
- 容器重启后调度器重新加载，需等待调度周期
- `apscheduler` 未安装（检查 requirements.txt 及镜像）
- 上次执行卡住（检查执行记录中的 started_at 是否很久未完成）

---

## LLM 供应商错误对照表

| HTTP 状态码 | 错误来源 | 分类 | 是否自动重试 |
|------------|---------|------|------------|
| 401 | 供应商 | auth（认证失败） | 否 |
| 403 | 供应商 | auth（禁止访问） | 否 |
| 402 | 供应商 | balance（余额不足） | 否 |
| 404 | 供应商 | model_not_found | 否 |
| 429 | 供应商 | rate_limit（频率超限） | 是（指数退避） |
| 500 | 供应商 | network（服务端错误） | 是 |
| 502/503/504 | 供应商 | network（网关错误） | 是 |
| 超时（60s） | 网络 | timeout | 是 |
| ConnectionError | 网络 | network | 是 |

自动重试配置：最多重试 **2 次**，退避间隔为 `2^n 秒`（2s、4s）。

---

## 定时任务管理

平台内置 APScheduler 调度器，用于执行定时工作流。

### 查看当前调度任务

目前无直接 CLI 命令，通过前端「工作流」页面管理：
- 启用/禁用工作流
- 查看执行历史（含日志和错误信息）
- 手动触发执行

### 调度器配置

调度器在应用启动时自动加载所有 `enabled=true` 的工作流：
- IntervalTrigger：按固定间隔（分钟/小时/天）执行
- CronTrigger：按 Cron 表达式执行（特定时间点）
- DateTrigger：单次执行（手动触发）

容器重启后调度器会自动恢复所有启用的定时任务。

---

## 版本升级

### 升级前准备

```bash
# 1. 备份数据（必须！）
./backup.sh

# 2. 记录当前版本
curl -s http://localhost:8000/health
```

### Docker Compose 升级

```bash
# 1. 拉取最新代码
git pull origin main

# 2. 重新构建并启动（自动执行数据库迁移）
docker compose up -d --build

# 3. 检查服务状态
docker compose ps
curl -s http://localhost:8000/health

# 4. 验证前端可访问
curl -s -o /dev/null -w "%{http_code}" http://localhost/
```

### 数据库迁移说明

启动时后端容器会自动执行 `alembic upgrade head`。若需要手动执行：

```bash
# 手动执行数据库迁移
docker compose exec backend alembic upgrade head

# 查看当前迁移版本
docker compose exec backend alembic current

# 查看迁移历史
docker compose exec backend alembic history
```

### 升级回滚

若新版本出现问题：
```bash
# 1. 停止新版本
docker compose down

# 2. 切回旧版本代码
git checkout <previous-tag-or-commit>

# 3. 使用旧镜像启动
docker compose up -d --build

# 4. 若数据库已迁移且不兼容，需从备份恢复
```

---

## 数据清理

通过前端「设置」页面或 API 进行数据清理，释放存储空间。

### 清理历史数据（API）

```bash
# 清理 90 天前的验证记录和 API 调用日志
curl -X POST -H "X-API-Key: your-api-key" \
  -H "Content-Type: application/json" \
  -d '{"days": 90, "modules": ["verify_results", "api_calls"]}' \
  http://localhost:8000/api/v1/data/cleanup

# 清理 30 天前的工作流执行记录
curl -X POST -H "X-API-Key: your-api-key" \
  -H "Content-Type: application/json" \
  -d '{"days": 30, "modules": ["workflow_executions"]}' \
  http://localhost:8000/api/v1/data/cleanup
```

### 查看存储统计

```bash
curl -s -H "X-API-Key: your-api-key" \
  http://localhost:8000/api/v1/data/storage | python3 -m json.tool
```

返回各模块记录数、数据库大小和上传文件总大小。

---

## 审计日志

所有关键操作（增删改、数据导入导出、配置变更）均有审计日志。

### 查询审计日志

```bash
# 最近 50 条审计日志
curl -s -H "X-API-Key: your-api-key" \
  "http://localhost:8000/api/v1/data/audit-logs?page=1&page_size=50" | python3 -m json.tool
```

**日志字段说明：**
- `action`：操作类型（create/update/delete/import/export/login 等）
- `resource_type`：资源类型（keyword/article/platform/workflow 等）
- `resource_id`：操作对象 ID
- `detail`：操作详情（JSON）
- `result`：操作结果（success/failure）
- `error_message`：失败原因（如有）
- `created_at`：操作时间

---

## 性能监控指标

### 关键指标参考

| 指标 | 正常范围 | 告警阈值 | 说明 |
|------|---------|---------|------|
| 后端响应时间（健康检查） | < 50ms | > 500ms | `/health` 接口响应时间 |
| LLM 首次 Token 延迟 | 1-10s | > 30s | 取决于供应商和模型 |
| 数据库文件大小 | < 100MB | > 1GB | SQLite 建议不超过 1GB，超量应切换 PG |
| ChromaDB 目录大小 | 取决于文档量 | - | 每上传 1MB 文档约增加 0.3-0.5MB |
| 内存占用（后端） | 200-500MB | > 1.5GB | 注意 ChromaDB 加载时内存峰值 |

### 系统资源检查

```bash
# 查看容器资源占用
docker stats --no-stream

# 查看数据卷大小
docker system df -v | grep -E "backend_data|uploads"

# 查看磁盘使用
df -h /var/lib/docker
```

### 推荐定期检查项

| 频率 | 检查项 | 操作 |
|------|-------|------|
| 每日 | 容器健康状态 | `docker compose ps` |
| 每日 | 后端错误日志 | `docker compose logs --tail=50 backend \| grep ERROR` |
| 每周 | 磁盘空间 | `df -h`，清理不需要的旧镜像 `docker image prune` |
| 每周 | 数据备份是否正常执行 | 检查备份目录文件大小和时间戳 |
| 每月 | 数据库大小 | 通过 `/api/v1/data/storage` 查看 |
| 每月 | LLM 平台余额 | 登录各 LLM 供应商控制台查看余额 |
| 每季 | 密码/API Key 轮换 | 更新 `API_KEY` 环境变量并重启 |

---

## 紧急联系方式与 escalation

| 问题级别 | 定义 | 响应方式 |
|---------|------|---------|
| P0 - 致命 | 服务完全不可用，所有用户无法访问 | 立即查看日志，重启服务；若数据损坏则从备份恢复 |
| P1 - 严重 | 核心功能（生成文章）不可用 | 检查 LLM 配置和网络，查看供应商状态页 |
| P2 - 一般 | 非核心功能异常（如某个平台发布失败） | 记录错误，在工作时间处理 |
| P3 - 轻微 | UI 显示问题、文案错误 | 下个版本修复 |
