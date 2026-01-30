## GEO 主 Tab 与模块映射（结构拆分基础）

> 说明：本文件用于记录 `geo_tool.py` 中主导航 Tabs 与后续 `modules/ui/tab_*.py` 模块之间的映射关系，作为拆分与维护参考。

### 顶层主导航 Tabs

- **Tab1：🎯 关键词蒸馏**
  - 代码位置：`geo_tool.py` 中 `# Tab1：关键词蒸馏` 段落起始（约 L930）
  - 顶部定义：`tab1, tab2, ... = st.tabs([...])` 中第 1 个元素
  - 计划对应模块：`modules/ui/tab_keywords.py`
  - 职责简介：关键词生成模式选择、词库管理（含导入/导出）、生成控制与结果展示等。

- **Tab2：✍️ 自动创作**
  - 代码位置：`# Tab2：自动创作内容（含批量 ZIP / GitHub 模板）` 段落（约 L2270）
  - 计划对应模块：`modules/ui/tab_autowrite.py`
  - 职责简介：基于关键词与模版的自动内容创作，支持批量 ZIP 导出与 GitHub 模板生成。

- **Tab3：🔧 文章优化**
  - 代码位置：`# Tab3：文章优化` 段落（约 L4175）
  - 计划对应模块：`modules/ui/tab_optimize.py`
  - 职责简介：对已生成或外部导入文章进行优化，包含结构优化、风格调整、事实密度增强，以及折叠区中的「结构化 Schema & 技术 SEO 配置」等高级功能。

- **Tab4：✅ 多模型验证 & 竞品对比**
  - 代码位置：`# Tab4：多模型验证 & 竞品对比` 段落（约 L5244）
  - 计划对应模块：`modules/ui/tab_validation.py`
  - 职责简介：多模型内容验证、评分与竞品对比分析。

- **Tab5：📚 历史记录**
  - 代码位置：`# Tab5：历史记录` 段落（约 L5532）
  - 计划对应模块：`modules/ui/tab_history.py`
  - 职责简介：展示历史任务与结果、统计数据、筛选与回溯等。

- **Tab6：📊 AI 数据报表**
  - 代码位置：`# Tab6：AI 数据报表` 段落（约 L5643）
  - 计划对应模块：`modules/ui/tab_reports.py`
  - 职责简介：围绕 GEO 结果的可视化报表，包括关键词、话题集群、平台表现等数据视图。

- **Tab7：🔄 工作流自动化**
  - 代码位置：`# Tab7：工作流自动化` 段落（约 L6629）
  - 计划对应模块：`modules/ui/tab_workflow.py`
  - 职责简介：基于 `WorkflowManager` 的自动化流程编排，一键跑通从关键词到验证的完整流程。

- **Tab8：📦 GEO 资源库**
  - 代码位置：`# Tab8：GEO 资源库` 段落（约 L7051）
  - 计划对应模块：`modules/ui/tab_resources.py`
  - 职责简介：展示 GEO 相关工具、代理、论文和社区资源，为用户提供扩展生态。

- **Tab9：🔄 平台同步**
  - 代码位置：`# Tab9：平台同步` 段落（约 L7291）
  - 计划对应模块：`modules/ui/tab_platform_sync.py`
  - 职责简介：将生成的文章同步到各内容平台，支持 API 发布和一键复制。

- **Tab10：🛠️ 配置优化助手**
  - 代码位置：`# Tab10：配置优化助手` 段落（约 L7584）
  - 计划对应模块：`modules/ui/tab_config_optimizer.py`
  - 职责简介：分析品牌名与优势的 GEO 友好度，提供可一键应用到全局配置的优化建议。

### 备注

- `geo_tool.py` 仍然作为 Streamlit 主入口，负责：
  - 全局 CSS/主题注入（后续迁移到 `modules/ui/theme.py`）。
  - 会话状态初始化（后续迁移到 `modules/ui/state.py`）。
  - 布局与主 Tabs 路由（未来仅保留对 `tab_*.py` 的调用）。
- 各 Tab 内部的子 `st.tabs(...)`（例如词库管理、结果分析子 Tab）将保留在对应的 `tab_*.py` 模块内部实现。

