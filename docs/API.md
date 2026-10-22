# API 接口文档

> 启动后端后，访问 `http://localhost:8000/docs` 可查看交互式 Swagger UI 文档（含在线调试）。

## 通用说明

### Base URL

```
http://localhost:8000/api/v1
```

### 认证

所有接口（除 `/health` 和 `/`）需要 `X-API-Key` 请求头：

```bash
curl -H "X-API-Key: your-api-key" http://localhost:8000/api/v1/config
```

未配置 `API_KEY` 环境变量时，认证跳过（开发模式）。

### 响应格式

**成功响应：**
```json
{
  "code": 0,
  "message": "ok",
  "data": { ... }
}
```

**分页响应：**
```json
{
  "code": 0,
  "message": "ok",
  "data": {
    "items": [ ... ],
    "total": 100,
    "page": 1,
    "page_size": 20,
    "total_pages": 5
  }
}
```

**错误响应：**
```json
{
  "code": "LLM_TIMEOUT",
  "message": "请求超时（60秒），请稍后重试"
}
```

常见错误码：

| code | HTTP 状态 | 说明 |
|------|----------|------|
| `AUTH_ERROR` | 401 | API Key 无效 |
| `VALIDATION_ERROR` | 422 | 参数校验失败 |
| `NOT_FOUND` | 404 | 资源不存在 |
| `LLM_AUTH_ERROR` | 502 | LLM API Key 无效 |
| `LLM_BALANCE_ERROR` | 502 | LLM 余额不足 |
| `LLM_TIMEOUT` | 502 | 请求超时 |
| `LLM_RATE_LIMIT` | 502 | 速率限制 |
| `LLM_MODEL_NOT_FOUND` | 502 | 模型名称无效 |
| `LLM_NETWORK_ERROR` | 502 | 网络错误 |
| `INTERNAL_ERROR` | 500 | 服务器内部错误 |

### SSE 流式接口

流式接口（生成/验证/工作流）使用 Server-Sent Events：

```
Content-Type: text/event-stream
Cache-Control: no-cache
Connection: keep-alive
X-Accel-Buffering: no
```

事件格式：
```
event: start
data: {"total": 10, "keywords": [...]}

event: progress
data: {"current": 3, "total": 10, "message": "正在生成..."}

event: chunk
data: {"content": "生成的文本片段"}

event: complete
data: {"full_content": "...", "results": [...]}

event: error
data: {"message": "错误信息", "error_type": "timeout"}

event: done
data: {"message": "完成"}
```

---

## 接口一览

### 配置 `/config`

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/config` | 获取当前配置（Key 打码） |
| PUT | `/config` | 更新配置 |
| POST | `/config/test-connection` | 测试 LLM API 连接 |

### 关键词 `/keywords`

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/keywords` | 关键词列表（分页，支持 brand/tag/is_favorite/search 筛选） |
| POST | `/keywords` | 批量创建关键词（自动去重） |
| DELETE | `/keywords/{id}` | 删除单个关键词 |
| DELETE | `/keywords` | 清空所有关键词 |
| POST | `/keywords/generate` | **SSE** AI 生成关键词 |
| POST | `/keywords/mine` | **SSE** 竞品关键词挖掘 |
| POST | `/keywords/expand` | **SSE** 语义扩展 |
| POST | `/keywords/cluster` | 主题聚类 |
| POST | `/keywords/combinations` | 词库组合生成 |
| GET | `/keywords/meta/industry-presets` | 行业预设词库 |
| POST | `/keywords/analyze-quality` | 关键词质量分析 |
| POST | `/keywords/{id}/favorite` | 切换收藏状态 |
| PUT | `/keywords/{id}/tags` | 设置标签 |
| POST | `/keywords/import` | 从历史导入关键词 |
| GET | `/keywords/search` | 搜索关键词（selector） |

### 文章 `/articles`

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/articles` | 文章列表（分页） |
| GET | `/articles/{id}` | 获取文章详情 |
| POST | `/articles` | 手动创建文章 |
| PUT | `/articles/{id}` | 更新文章（含版本快照） |
| DELETE | `/articles/{id}` | 删除文章 |
| POST | `/articles/generate` | **SSE** 单平台内容生成 |
| POST | `/articles/batch-generate` | **SSE** 批量生成 |
| GET | `/articles/search` | 搜索文章（selector） |
| GET | `/articles/{id}/original` | 获取文章原文（版本1） |
| POST | `/articles/{id}/multimodal` | **SSE** 多模态描述生成 |
| GET | `/articles/{id}/download` | 下载文章为 .md |
| GET | `/articles/batch-download` | 批量下载为 ZIP |
| GET | `/articles/{id}/versions` | 版本历史列表 |
| GET | `/articles/{id}/versions/{vid}` | 获取指定版本 |
| POST | `/articles/{id}/rollback/{ver}` | 回滚到指定版本 |
| GET | `/articles/{id}/diff` | 两版本 Diff 对比 |
| GET | `/articles/meta/platforms` | 支持的平台列表 |
| GET | `/articles/meta/platform-groups` | 平台分组 |

### 优化 `/optimizations`

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/optimizations/eeat` | **SSE** E-E-A-T 优化 |
| POST | `/optimizations/fact-density` | **SSE** 事实密度增强 |
| POST | `/optimizations/schema` | Schema 结构化数据生成 |
| POST | `/optimizations/analyze` | 内容指标分析 |
| POST | `/optimizations/check-uniqueness` | 内容独特性检查 |
| POST | `/optimizations/tech-config` | 技术配置生成 |
| GET | `/optimizations` | 优化记录列表（分页） |
| GET | `/optimizations/articles/{id}/original-content` | 获取原文内容 |

### 验证 `/verification`

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/verification/results` | 验证结果列表（分页） |
| DELETE | `/verification/results/{rid}` | 删除验证结果 |
| POST | `/verification/verify` | **SSE** 多模型品牌验证（支持 natural/prompted 模式） |
| POST | `/verification/competitor` | **SSE** 竞品对比验证 |

### 工作流 `/workflows`

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/workflows` | 工作流列表 |
| POST | `/workflows` | 创建工作流 |
| PUT | `/workflows/{id}` | 更新工作流 |
| DELETE | `/workflows/{id}` | 删除工作流 |
| POST | `/workflows/{id}/execute` | **SSE** 执行工作流 |
| GET | `/workflows/{id}/executions` | 执行历史 |
| GET | `/workflows/templates` | 工作流模板列表 |

### 知识库 `/knowledge`

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/knowledge/docs` | 文档列表（分页） |
| POST | `/knowledge/upload` | 上传文档（multipart/form-data） |
| DELETE | `/knowledge/docs/{id}` | 删除文档 |
| POST | `/knowledge/search` | 语义搜索 |

### 平台发布 `/platforms`

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/platforms/accounts` | 平台账号列表 |
| POST | `/platforms/accounts` | 添加平台账号 |
| PUT | `/platforms/accounts/{id}` | 更新账号 |
| DELETE | `/platforms/accounts/{id}` | 删除账号 |
| POST | `/platforms/publish/{article_id}` | 发布文章 |
| GET | `/platforms/records` | 发布记录列表 |
| POST | `/platforms/publish/{record_id}/retry` | 重试失败发布 |

### 监控 `/monitor`

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/monitor/tasks` | 监控任务列表 |
| POST | `/monitor/tasks` | 创建监控任务 |
| PUT | `/monitor/tasks/{id}` | 更新任务 |
| DELETE | `/monitor/tasks/{id}` | 删除任务 |
| POST | `/monitor/tasks/{id}/run` | **SSE** 立即执行 |
| GET | `/monitor/tasks/{id}/results` | 监控结果 |
| GET | `/monitor/alerts` | 告警列表 |

### 报表 `/reports`

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/reports/kpi` | KPI 统计数据 |
| GET | `/reports/costs` | 成本报表 |
| GET | `/reports/mentions` | 提及率报表 |
| GET | `/reports/markdown` | Markdown 报表 |
| POST | `/reports/generate` | **SSE** 生成营销报告 |

### 数据管理 `/data`

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/data/storage` | 存储统计（DB大小、表记录数、知识库大小） |
| GET | `/data/export/all` | 全量导出（JSON 文件下载） |
| GET | `/data/export/csv/{module}` | 模块 CSV 导出（keywords/articles/verify_results/api_calls） |
| POST | `/data/import` | 数据导入（skip/overwrite/append 策略） |
| POST | `/data/cleanup` | 清理 N 天前的数据 |
| GET | `/data/audit-logs` | 审计日志（分页） |

### 平台模板 `/templates`

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/templates` | 模板列表 |
| POST | `/templates` | 创建自定义模板 |
| PUT | `/templates/{id}` | 更新模板 |
| DELETE | `/templates/{id}` | 删除/禁用模板 |
| POST | `/templates/{id}/reset` | 重置默认模板 |
| GET | `/templates/groups` | 分组平台列表 |
| GET | `/templates/config` | 平台配置 dict |
| GET | `/templates/export` | 导出模板配置 |
| POST | `/templates/import` | 导入模板配置 |

### 其他

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/scoring/score` | 内容评分 |
| POST | `/dds/score` | DDS 三维评分 |
| POST | `/schema/generate` | Schema 生成 |
| GET | `/resources/geo-techniques` | GEO 技术列表 |
| GET | `/health` | 健康检查（无需认证） |

---

## SSE 事件类型

### 内容生成（generate/batch-generate）

| event | data 字段 | 说明 |
|-------|----------|------|
| `start` | `total`, `keywords`, `platforms`, `warnings?` | 开始 |
| `progress` | `current`, `total`, `keyword`, `platform`, `progress`, `message` | 进度 |
| `chunk` | `content` | 文本片段（单平台生成） |
| `article_done` | `id`, `keyword`, `platform`, `filename` | 单篇完成 |
| `article_error` | `keyword`, `platform`, `error`, `error_type?` | 单篇失败 |
| `complete` | `total_articles`, `articles` | 全部完成 |
| `error` | `message`, `error_type?` | 致命错误 |

### 多模型验证（verify）

| event | data 字段 | 说明 |
|-------|----------|------|
| `start` | `query`, `brand`, `mode`, `total` | 开始 |
| `model_start` | `step`, `total`, `provider`, `model`, `message` | 某模型开始 |
| `chunk` | `provider`, `model`, `content` | 文本片段 |
| `model_complete` | `provider`, `model`, `is_mentioned`, `mention_count`, `sentiment`, ... | 某模型完成 |
| `model_error` | `provider`, `model`, `error`, `error_type` | 某模型失败 |
| `complete` | `total`, `success`, `failed`, `results`, `errors` | 全部完成 |
| `error` | `message` | 致命错误 |

### 工作流执行

| event | data 字段 | 说明 |
|-------|----------|------|
| `start` | `workflow_id`, `steps` | 开始 |
| `step_start` | `step`, `step_name` | 步骤开始 |
| `log` | `message` | 日志 |
| `chunk` | `content` | 生成内容 |
| `step_complete` | `step`, `result` | 步骤完成 |
| `step_error` | `step`, `error`, `error_type?` | 步骤失败 |
| `complete` | `status`, `result`, `summary` | 执行完成 |
| `error` | `message` | 致命错误 |
