# 前端（React + Ant Design）

## 技术栈

- **React 18** — 函数组件 + Hooks
- **TypeScript 5.5** — strict mode，零 any（ECharts/AntD 回调除外）
- **Vite 5** — 开发服务器 + 生产构建（Rolldown）
- **Ant Design 5** — UI 组件库
- **Zustand 4** — 轻量全局状态管理（localStorage 持久化）
- **ECharts 5** + **echarts-for-react** — 数据可视化
- **react-router-dom 6** — 客户端路由
- **react-markdown 9** — Markdown 渲染
- **Axios** — HTTP 请求

## 目录结构

```
src/
├── api/                        # API 调用层（每个模块一个文件）
│   ├── request.ts             # Axios 实例 + SSEClient（fetch ReadableStream）
│   ├── config.ts              # 配置 API
│   ├── keywords.ts            # 关键词 API
│   ├── articles.ts            # 文章 API（含 SSE 流式生成）
│   ├── optimizations.ts       # 优化 API（含 SSE）
│   ├── verification.ts        # 验证 API（含 SSE）
│   ├── workflows.ts           # 工作流 API（含 SSE）
│   ├── knowledge.ts           # 知识库 API
│   ├── platforms.ts           # 平台账号/发布 API
│   ├── monitor.ts             # 监控 API
│   ├── reports.ts             # 报表 API
│   ├── data.ts                # 数据管理 API（导出/导入/清理/审计）
│   ├── templates.ts           # 平台模板 API
│   ├── scoring.ts / dds.ts / schema.ts / analytics.ts / resources.ts
│   └── index.ts
├── components/                 # 通用可复用组件
│   ├── MarkdownEditor.tsx     # Markdown 编辑器（编辑/预览双模式）
│   ├── StreamingText.tsx      # SSE 流式文本展示组件
│   ├── FileUpload.tsx         # 文件上传组件
│   ├── PlatformSelector.tsx   # 平台多选器
│   ├── ProgressBar.tsx        # 进度条组件
│   ├── ScoreChart.tsx         # 评分雷达图
│   └── ErrorBoundary.tsx      # 错误边界
├── hooks/
│   └── useSSE.ts              # SSE Hook（封装 SSEClient）
├── layouts/
│   ├── AppLayout.tsx          # 主布局（侧边栏 + 顶栏 + 内容区）
│   └── AppRoutes.tsx          # 路由配置（React.lazy 代码分割）
├── pages/                      # 页面组件（19个）
│   ├── Dashboard.tsx           # 仪表盘（KPI + 快捷入口）
│   ├── KeywordsPage.tsx        # 关键词（生成/挖掘/扩展/质量分析/标签/收藏）
│   ├── ArticlesPage.tsx        # 内容创作（生成/编辑/版本/批量/发布）
│   ├── OptimizePage.tsx        # 内容优化（E-E-A-T/事实密度/Schema）
│   ├── VerifyPage.tsx          # 多模型验证（自然/提示模式/情感/诊断）
│   ├── WorkflowsPage.tsx       # 自动化工作流
│   ├── KnowledgePage.tsx       # 知识库管理
│   ├── PlatformsPage.tsx       # 平台账号/发布记录/重试
│   ├── MonitorPage.tsx         # 监控任务
│   ├── ReportsPage.tsx         # 数据分析（概览/趋势/成本/质量）
│   ├── DDSScorePage.tsx        # DDS 三维评分
│   ├── SchemaToolsPage.tsx     # Schema 生成工具
│   ├── AnalyticsPage.tsx       # 深度分析
│   ├── HistoryPage.tsx         # 操作历史
│   ├── ConfigOptimizerPage.tsx # 配置优化器
│   ├── MarketingReportsPage.tsx# 营销报告
│   ├── ResourcesPage.tsx       # GEO 资源库
│   └── SettingsPage.tsx        # 设置（向导/LLM配置/品牌/数据管理/模板）
├── stores/
│   ├── app.ts                 # 全局应用状态（配置、品牌信息）
│   └── index.ts
├── styles/
│   └── global.css             # 全局样式（CSS变量、主题、AntD覆盖）
├── types/
│   └── index.ts               # TypeScript 类型定义
├── utils/                     # (request.ts 在 api/ 中)
├── App.tsx
└── main.tsx
```

## 开发

```bash
cd frontend

# 安装依赖
npm install

# 启动开发服务器（默认 http://localhost:5173，自动代理 API 到 localhost:8000）
npm run dev

# 类型检查
npm run typecheck

# 生产构建（输出到 dist/）
npm run build

# 预览生产构建
npm run preview

# 运行测试
npm test
```

## 代码规范

- TypeScript strict mode，所有组件 Props 有完整类型
- API 层使用统一的 `request` Axios 实例，SSE 使用 `sseClient`
- 页面级组件使用 `React.lazy()` 按需加载
- 全局状态使用 Zustand，局部状态使用 useState
- 中文字符串直接写在 JSX 中，不使用 i18n
- API 错误统一在 axios 响应拦截器中处理，页面中处理业务级错误

## 环境变量

开发环境创建 `.env.local`：

```bash
VITE_API_BASE_URL=http://localhost:8000/api/v1
VITE_API_KEY=your-api-key-here
```

| 变量 | 说明 | 默认值 |
|------|------|--------|
| `VITE_API_BASE_URL` | 后端 API 地址 | `/api/v1`（Vite 代理到 8000） |
| `VITE_API_KEY` | API Key（可选） | 空（在界面设置中填写） |

## 构建产物

`npm run build` 输出到 `dist/`：
- 每个页面一个独立 chunk（React.lazy 代码分割）
- gzip 后主 bundle ~460KB，各页面 5-35KB
- 纯静态文件，可直接由 Nginx 托管
