# Tab 拆分模式说明（基于 Tab1 / Tab2 实践）

> 本文档描述早期 Streamlit 版本中「关键词蒸馏」Tab 与「自动创作」Tab 的拆分方式，供历史参考。
> 当前架构已迁移为 **FastAPI 后端 + React 前端**：原 Streamlit Tab 已拆分为 React 页面（`frontend/src/pages/`），业务逻辑由 FastAPI 服务层（`backend/app/services/`）提供。原 Streamlit 代码归档于 `legacy/streamlit/`。

## 一、项目与目录结构概览

```
geo_tool/
├── geo_tool.py              # FastAPI 后端 + React 前端（当前架构，原 Streamlit 主入口已废弃并归档至 legacy/streamlit/）
├── modules/
│   ├── *.py                 # 业务模块（data_storage, keyword_tool, content_scorer, schema_generator 等）
│   └── ui/
│       ├── __init__.py      # 导出 tab_keywords, tab_autowrite（后续增加 tab_optimize 等）
│       ├── state.py         # ss_init(), init_session_state()
│       ├── theme.py         # inject_global_theme()
│       ├── tab_keywords.py  # Tab1：关键词蒸馏
│       └── tab_autowrite.py # Tab2：自动创作
├── platform_sync/           # 平台同步（GitHub 发布、一键复制等）
├── docs/
└── scripts/
```

- **主入口**：只做页面配置、侧栏、全局变量（cfg, brand, advantages, gen_llm, verify_llms, storage）、Tabs 创建与**路由**（每个 `with tabN:` 内只调用对应 `render_tab_*`）。
- **各 Tab 逻辑**：全部放在 `modules/ui/tab_*.py` 的 `render_tab_*` 中，通过参数从主入口拿到依赖，不反向引用 `geo_tool`，避免循环依赖。

---

## 二、Tab 模块结构（统一模式）

每个 `tab_xxx.py` 大致分为三块：

### 1. 顶部：导入 + 本 Tab 用到的工具函数

- **只导入本 Tab 用到的**：`streamlit`、LangChain、以及 `modules` 下用到的业务类（如 `ContentScorer`, `SchemaGenerator`）。
- **不导入** `geo_tool` 或 `modules.ui` 里会间接依赖主入口的模块，避免循环依赖。
- 若该 Tab 用到了主入口里的**工具函数**（如 `sanitize_filename`、`safe_decode_uploaded`），在 Tab 模块里**复制一份**实现，并注释说明「从 geo_tool 复制，避免循环依赖」。

示例（tab_autowrite.py）：

```python
import io, json, re, time, zipfile
from datetime import datetime
import streamlit as st
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import PromptTemplate
from modules.content_scorer import ContentScorer
from modules.schema_generator import SchemaGenerator
# ...

INVALID_FS_CHARS = r'<>:"/\\|?*\n\r\t'

def sanitize_filename(name: str, max_len: int = 80) -> str:
    """Copy of utility from geo_tool, kept local to avoid circular imports."""
    # ...
```

### 2. 入口函数签名：`render_tab_*(...) -> None`

- 函数名：`render_tab_keywords` / `render_tab_autowrite` / 后续 `render_tab_optimize` 等。
- 参数：由主入口「按需传入」该 Tab 用到的所有依赖，常见包括：
  - `storage`：数据存储
  - `ss_init`：会话状态初始化
  - `gen_llm`：生成用 LLM（若该 Tab 有调用）
  - `brand`, `advantages`：品牌与优势文案
  - `cfg`：当前配置（若该 Tab 需要读 gen_provider、tongyi_wanxiang_api_key 等）
  - `record_api_cost`, `model_defaults`：若该 Tab 需要记录 API 成本
  - 其他 Tab 特有依赖（如 Tab4 可能需 `verify_llms`）
- 返回值：`None`，仅负责渲染和写 `st.session_state`。

**Tab1（关键词蒸馏）** 不需要记录成本，参数较少：

```python
def render_tab_keywords(storage, ss_init, gen_llm, brand: str, advantages: str) -> None:
```

**Tab2（自动创作）** 需要记录成本与 cfg，参数更多：

```python
def render_tab_autowrite(
    storage, ss_init, gen_llm, brand: str, advantages: str,
    cfg: dict, record_api_cost, model_defaults,
) -> None:
```

### 3. 函数体：原样迁移「该 Tab 内部」的 UI + 逻辑

- 原主入口里是：`with tab1:` / `with tab2:` 下面的**整块代码**（标题、表单、结果区、子 Tabs 等）。
- 迁移时：把这块代码**整体**挪到 `render_tab_*` 里，作为函数体；**缩进**保持与原先在 `with tabN:` 下一致（相当于原 4 空格变成函数体第一层缩进）。
- **不要**在 Tab 模块里改业务逻辑或变量命名，只做「剪切 + 粘贴 + 补参数」，保证行为一致。

**表单提交后的变量**：若在 `if run_opt:` / `if run_content:` 等分支里用到了表单里选的（如「优化技巧」），提交后下一轮 rerun 时表单控件可能还未再执行，需要在分支开头从 `st.session_state` 取一次（例如 `opt_selected_technique_names = st.session_state.get("opt_techniques", [])`），与 tab_autowrite 里对 `content_techniques` 的处理一致。

---

## 三、主入口中的调用方式（geo_tool.py）

- 主导航：`tab1, tab2, ..., tab10 = st.tabs([...])` 不变。
- 每个 Tab 只做两件事：进入上下文 + 调用对应 `render_*`：

```python
# =======================
# Tab1：关键词蒸馏
# =======================
with tab1:
    tab_keywords.render_tab_keywords(storage, ss_init, gen_llm, brand, advantages)

# =======================
# Tab2：自动创作内容（含批量 ZIP / GitHub 模板）
# =======================
with tab2:
    tab_autowrite.render_tab_autowrite(
        storage, ss_init, gen_llm, brand, advantages,
        cfg, record_api_cost, model_defaults
    )

# Tab3 及以后：同样模式，with tab3: tab_optimize.render_tab_optimize(...)
```

- 主入口保留：侧栏、cfg、brand/advantages、gen_llm/verify_llms、storage、`record_api_cost` / `model_defaults` 等**跨 Tab 共享**的构造与配置；Tab 内部不创建这些，只通过参数使用。

---

## 四、state 与 theme（已集中）

- **state.py**：`ss_init(key, default)` + `init_session_state()`。主入口在启动时调用 `init_session_state()`；各 Tab 在需要时调用 `ss_init("xxx", default)`。
- **theme.py**：`inject_global_theme()`。主入口在页面配置后调用一次即可。

Tab 模块只接收并调用 `ss_init`，不直接依赖 state/theme 的实现细节。

---

## 五、新增 Tab 时的检查清单

1. 在 `modules/ui/` 下新建 `tab_<name>.py`。
2. 按上面「结构」写好：导入、本 Tab 用到的工具函数（必要时从 geo_tool 复制）、`render_tab_<name>(...)` 及完整函数体。
3. 在 `modules/ui/__init__.py` 中增加 `from . import tab_<name>`（并对外暴露）。
4. 在 `geo_tool.py` 中：删除该 Tab 对应的整块内联代码，改为 `with tabN: tab_<name>.render_tab_<name>(...)`，并传入该 Tab 所需的全部参数。
5. 确认：无对 `geo_tool` 或会反向依赖主入口的模块的 import；表单提交后若用到表单值，从 `st.session_state` 按 key 读取。

按此模式，Tab3（文章优化）及后续 Tab 可与 Tab1/Tab2 保持一致、可维护的拆分方式。
