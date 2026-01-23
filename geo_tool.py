import streamlit as st
import pandas as pd
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import JsonOutputParser, StrOutputParser
import zipfile
import io
import plotly.express as px
import re
import json
from data_storage import DataStorage
from keyword_tool import KeywordTool
from content_scorer import ContentScorer

APP_TITLE = "GEO 智能内容优化平台"

# ------------------- 页面配置 & 极简美学 CSS（产品级精修，仍然克制） -------------------
st.set_page_config(page_title="GEO 智能内容优化平台", layout="wide", initial_sidebar_state="expanded")

st.markdown(
    """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600&family=Noto+Sans+SC:wght@400;500;600&display=swap');

:root{
  --bg:#FFFFFF;
  --panel:#F7FAFC;
  --text:#1A202C;
  --muted:#4A5568;
  --border:#E2E8F0;
  --primary:#2563EB;
  --shadow: 0 1px 2px rgba(16,24,40,.04), 0 6px 16px rgba(16,24,40,.06);
  --radius:12px;
}

.stApp { background: var(--bg); }
html, body, [class*="css"]  { font-family: "Inter","Noto Sans SC",-apple-system,BlinkMacSystemFont,"Segoe UI",Arial,sans-serif; color: var(--text); }

.block-container { max-width: 980px; padding-top: 1.6rem; padding-bottom: 3.5rem; }

/* Sidebar 更轻 */
section[data-testid="stSidebar"] { background: var(--panel); border-right: 1px solid var(--border); }

/* 标题层级 */
h1 { font-size: 2.15rem; font-weight: 600; letter-spacing: -0.4px; margin-bottom: 1.0rem; }
h2 { font-size: 1.25rem; font-weight: 600; color: var(--text); margin: 1.8rem 0 0.75rem; }
p, li { color: var(--muted); }

/* 按钮 */
.stButton > button { border-radius: 10px; }

/* 输入 */
.stTextInput input, .stTextArea textarea, .stSelectbox div[data-baseweb="select"] {
  border-radius: 10px !important;
}
.stTextInput input, .stTextArea textarea {
  border: 1px solid var(--border) !important;
  padding: 0.75rem !important;
}
.stTextInput input:focus, .stTextArea textarea:focus {
  border-color: var(--primary) !important;
  box-shadow: 0 0 0 3px rgba(37,99,235,.12) !important;
}

/* Tabs 产品化 */
.stTabs [data-baseweb="tab-list"] { gap: 8px; }
.stTabs [data-baseweb="tab"]{
  padding: 10px 14px;
  border-radius: 10px;
  background: transparent;
  border: 1px solid transparent;
}
.stTabs [aria-selected="true"]{
  background: rgba(37,99,235,.08);
  border: 1px solid rgba(37,99,235,.20);
}

/* “卡片感”：尽量使用 st.container(border=True) */
div[data-testid="stVerticalBlockBorderWrapper"]{
  border-radius: var(--radius);
  box-shadow: var(--shadow);
}
/* ========== Button radius override (works across Streamlit versions) ========== */

/* st.button */
div[data-testid="stButton"] button {
  border-radius: 10px !important;
}

/* st.form_submit_button */
div[data-testid="stFormSubmitButton"] button {
  border-radius: 10px !important;
}

/* BaseWeb buttons (Streamlit internal) */
button[data-testid^="baseButton-"] {
  border-radius: 10px !important;
}

/* 防止出现“圆形外圈/描边” */
div[data-testid="stButton"] button:focus,
div[data-testid="stButton"] button:focus-visible,
div[data-testid="stFormSubmitButton"] button:focus,
div[data-testid="stFormSubmitButton"] button:focus-visible,
button[data-testid^="baseButton-"]:focus,
button[data-testid^="baseButton-"]:focus-visible {
  outline: none !important;
  box-shadow: 0 0 0 3px rgba(37,99,235,.12) !important;
}

/* 次级按钮更轻，和 Tabs 更协调（不会像“圆圈”） */
button[data-testid="baseButton-secondary"],
div[data-testid="stButton"] button[kind="secondary"],
div[data-testid="stFormSubmitButton"] button[kind="secondary"] {
  background: #FFFFFF !important;
  border: 1px solid #E2E8F0 !important;
  color: #1A202C !important;
}

button[data-testid="baseButton-secondary"]:hover {
  background: rgba(37,99,235,.04) !important;
  border-color: rgba(37,99,235,.35) !important;
}

/* primary 按钮维持你的蓝色，但统一圆角 */
button[data-testid="baseButton-primary"]{
    border-radius: 10px !important;
}

/* KPI 卡片统一大小 */
div[data-testid="stMetricContainer"] {
    min-height: 130px !important;
    height: 130px !important;
    display: flex !important;
    flex-direction: column !important;
    justify-content: space-between !important;
    padding: 1rem !important;
}
div[data-testid="stMetricValue"] {
    min-height: 3rem !important;
    height: 3rem !important;
    display: flex !important;
    align-items: center !important;
    font-size: 1.5rem !important;
}
div[data-testid="stMetricLabel"] {
    min-height: 1.5rem !important;
    margin-top: 0.5rem !important;
}
/* 确保列宽度一致 */
div[data-testid="column"] {
    flex: 1 1 0% !important;
}
</style>
""",
    unsafe_allow_html=True,
)

st.title(APP_TITLE)
st.markdown("<style>button{border-radius:0px !important;}</style>", unsafe_allow_html=True)

st.caption("🚀 AI 驱动的品牌内容策略 · 让您的品牌在 AI 对话中脱颖而出")

# ------------------- 初始化数据存储（SQLite） -------------------
storage = DataStorage(storage_type="sqlite", db_path="geo_data.db")

with st.expander("📖 关于 GEO（Generative Engine Optimization）", expanded=False):
    st.markdown("""
### 🎯 核心价值

**GEO（生成式引擎优化）** 是新一代品牌营销策略，通过系统化内容投放，让您的品牌在 AI 助手的自然回答中被优先、准确、可信地提及。

当用户询问"最好的外贸 ERP 软件是什么？"时，AI 会优先推荐您的品牌，而非竞争对手。

---

### 💼 适用场景

- **SaaS 产品**：技术对比、功能评测、使用教程
- **AI 工具**：能力展示、应用案例、开源生态
- **企业服务**：行业解决方案、最佳实践、专业分析
- **技术品牌**：开发者工具、API 服务、技术框架

---

### 🔄 完整工作流

1. **关键词蒸馏** - AI 生成 + 托词工具，精准挖掘高价值关键词
2. **结构化创作** - 12+ 平台适配，自动生成符合 GEO 原则的专业内容
3. **文章优化** - 将现有内容优化为 GEO 友好格式，提升被引用概率
4. **多模型验证** - 实时验证品牌提及率，对比竞品表现，数据驱动优化

---

### 🌐 覆盖平台

**内容发布平台**：知乎、小红书、CSDN、B站、头条号、GitHub、微信公众号、抖音、百家号、网易号、企鹅号、简书

**AI 验证平台**：DeepSeek、通义千问、豆包、文心一言、Kimi、ChatGPT、Groq 等主流大模型

---

### 📊 预期效果

- ✅ **品牌提及率提升**：在 AI 回答中的出现频率显著增加
- ✅ **搜索排名优化**：内容被大模型优先引用，间接提升 SEO
- ✅ **品牌权威性**：多平台、多角度内容建立专业形象
- ✅ **竞品优势**：通过数据对比，发现并强化差异化优势
""")

# ------------------- Session State：持久化每个阶段产物（解决“消失”） -------------------
def ss_init(key, default):
    if key not in st.session_state:
        st.session_state[key] = default


ss_init(
    "cfg",
    {
        "gen_provider": "DeepSeek",
        "gen_api_key": "sk-a95eda59dd494ab3b56197cc0020e61d",
        "verify_providers": ["DeepSeek"],
        "verify_keys": {"DeepSeek": "sk-a95eda59dd494ab3b56197cc0020e61d"},
        "brand": "汇信云AI软件",
        "advantages": "AI赋能外贸ERP、打造外贸智能新引擎、AI驱动型ERP、赋能外贸全流程管理、全链路价值闭环",
        "competitors": "南北软件\n睿贝软件\n孚盟软件\n小满软件",
        "temperature": 0.7,
    },
)
ss_init("cfg_applied", False)
ss_init("cfg_valid", False)
ss_init("cfg_errors", [])

# 模块1：关键词
ss_init("keywords", [])
ss_init("kw_last_num", 40)
ss_init("kw_generation_mode", "AI生成")  # 生成模式：AI生成 / 托词工具 / 混合模式
ss_init("wordbanks", None)  # 词库字典
ss_init("keyword_tool", KeywordTool())  # 托词工具实例

# 模块2：内容
ss_init("generated_contents", [])  # list[dict]
ss_init("zip_bytes", None)
ss_init("zip_filename", "")

# 模块3：文章优化
ss_init("optimized_article", "")
ss_init("opt_changes", "")
ss_init("opt_platform", "通用优化")

# 模块4：验证
ss_init("verify_combined", None)  # DataFrame or None
ss_init("verify_last_queries", "")

# ------------------- 工具函数 -------------------
INVALID_FS_CHARS = r'<>:"/\\|?*\n\r\t'


def sanitize_filename(name: str, max_len: int = 80) -> str:
    if not name:
        return "untitled"
    name = name.strip()
    name = re.sub(rf"[{re.escape(INVALID_FS_CHARS)}]", "_", name)
    name = re.sub(r"_+", "_", name).strip("_")
    return name[:max_len] if len(name) > max_len else name


def safe_decode_uploaded(uploaded) -> str:
    if not uploaded:
        return ""
    b = uploaded.getvalue()
    for enc in ("utf-8-sig", "utf-8", "gb18030"):
        try:
            return b.decode(enc)
        except Exception:
            pass
    return b.decode("utf-8", errors="replace")


def extract_json_array(text: str):
    """从模型输出中抽取 JSON 数组（JsonOutputParser 失败时兜底）。"""
    if not text:
        return None
    m = re.search(r"\[[\s\S]*\]", text)
    if not m:
        return None
    try:
        return json.loads(m.group(0))
    except Exception:
        return None


def validate_cfg(cfg: dict):
    """保留你原本的“必须填写所有 API Key”约束，但不 st.stop：改为禁用按钮 + 提示。"""
    errors = []
    if not cfg.get("gen_api_key", "").strip():
        errors.append("生成&优化 LLM 的 API Key 未填写")

    verify_providers = cfg.get("verify_providers", [])
    verify_keys = cfg.get("verify_keys", {})
    if not verify_providers:
        errors.append("至少选择一个验证模型")

    for vp in verify_providers:
        if not verify_keys.get(vp, "").strip():
            errors.append(f"验证模型 {vp} 的 API Key 未填写")

    return (len(errors) == 0), errors


def model_defaults(provider: str) -> str:
    if provider == "DeepSeek":
        return "deepseek-chat"
    if provider == "OpenAI (GPT)":
        return "gpt-4o-mini"
    if provider == "Tongyi (通义千问)":
        return "qwen-max"
    if provider == "Groq":
        return "llama3-70b-8192"
    if provider == "Moonshot (Kimi)":
        return "moonshot-v1-128k"
    if provider == "豆包（字节跳动）":
        return ""  # 豆包使用 ENDPOINT_ID，不需要模型名
    if provider == "文心一言（百度）":
        return "ernie-bot-turbo"
    return ""


# ------------------- 缓存 LLM 客户端（显著降低“频繁 Loading”） -------------------
@st.cache_resource(show_spinner=False)
def build_llm(provider: str, api_key: str, model: str, temperature: float):
    """
    - 使用 cache_resource 缓存客户端，避免每次 rerun 重建
    - Tongyi / Moonshot：保留你原功能路径，同时提供更稳的 import 兜底
    """
    if provider == "DeepSeek":
        from langchain_deepseek import ChatDeepSeek

        return ChatDeepSeek(api_key=api_key, model=model, temperature=temperature)

    if provider == "OpenAI (GPT)":
        from langchain_openai import ChatOpenAI

        return ChatOpenAI(api_key=api_key, model=model, temperature=temperature)

    if provider == "Tongyi (通义千问)":
        try:
            from langchain_community.chat_models import ChatTongyi

            return ChatTongyi(api_key=api_key, model=model, model_kwargs={"temperature": temperature})
        except Exception:
            from langchain_aliyun import ChatTongyi  # type: ignore

            return ChatTongyi(api_key=api_key, model=model, temperature=temperature)

    if provider == "Groq":
        from langchain_groq import ChatGroq

        return ChatGroq(api_key=api_key, model=model, temperature=temperature)

    if provider == "Moonshot (Kimi)":
        try:
            from langchain_moonshot import ChatMoonshot  # type: ignore

            return ChatMoonshot(api_key=api_key, model=model, temperature=temperature)
        except Exception:
            from langchain_community.chat_models import MoonshotChat  # type: ignore

            return MoonshotChat(api_key=api_key, model=model, temperature=temperature)

    if provider == "豆包（字节跳动）":
        try:
            # 尝试使用 volcengine-python-sdk[ark]
            from volcengine.ark import Ark
            from langchain_core.language_models.chat_models import BaseChatModel
            from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, SystemMessage
            from langchain_core.outputs import ChatGeneration, ChatResult
            from typing import List, Optional, Any
            
            class ChatDoubao(BaseChatModel):
                """豆包聊天模型封装（LangChain 兼容）"""
                volc_ak: str
                volc_sk: str
                endpoint_id: str
                temperature: float = 0.7
                
                def __init__(self, volc_ak: str, volc_sk: str, endpoint_id: str, temperature: float = 0.7):
                    super().__init__(temperature=temperature)
                    self.volc_ak = volc_ak
                    self.volc_sk = volc_sk
                    self.endpoint_id = endpoint_id
                    self.temperature = temperature
                    self.client = Ark(ak=volc_ak, sk=volc_sk)
                
                def _generate(self, messages: List[BaseMessage], stop: Optional[List[str]] = None, run_manager: Optional[Any] = None, **kwargs: Any) -> ChatResult:
                    # 转换消息格式
                    volc_messages = []
                    for msg in messages:
                        if isinstance(msg, SystemMessage):
                            volc_messages.append({"role": "system", "content": msg.content})
                        elif isinstance(msg, HumanMessage):
                            volc_messages.append({"role": "user", "content": msg.content})
                        elif isinstance(msg, AIMessage):
                            volc_messages.append({"role": "assistant", "content": msg.content})
                        else:
                            volc_messages.append({"role": "user", "content": str(msg.content)})
                    
                    response = self.client.chat.completions.create(
                        model=self.endpoint_id,
                        messages=volc_messages,
                        temperature=self.temperature,
                    )
                    
                    ai_message = AIMessage(content=response.choices[0].message.content)
                    return ChatResult(generations=[ChatGeneration(message=ai_message)])
                
                @property
                def _llm_type(self) -> str:
                    return "doubao"
            
            # 豆包的 api_key 格式：access_key:secret_key:endpoint_id
            parts = api_key.split(":")
            if len(parts) >= 3:
                return ChatDoubao(volc_ak=parts[0], volc_sk=parts[1], endpoint_id=parts[2], temperature=temperature)
            else:
                raise ValueError("豆包 API Key 格式错误，应为：access_key:secret_key:endpoint_id（用冒号分隔）")
        except ImportError:
            # 尝试其他导入方式
            try:
                from volcenginesdkarkruntime import Ark
                # 使用相同的 ChatDoubao 类
                from langchain_core.language_models.chat_models import BaseChatModel
                from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, SystemMessage
                from langchain_core.outputs import ChatGeneration, ChatResult
                from typing import List, Optional, Any
                
                class ChatDoubao(BaseChatModel):
                    """豆包聊天模型封装（LangChain 兼容）"""
                    volc_ak: str
                    volc_sk: str
                    endpoint_id: str
                    temperature: float = 0.7
                    
                    def __init__(self, volc_ak: str, volc_sk: str, endpoint_id: str, temperature: float = 0.7):
                        super().__init__(temperature=temperature)
                        self.volc_ak = volc_ak
                        self.volc_sk = volc_sk
                        self.endpoint_id = endpoint_id
                        self.temperature = temperature
                        self.client = Ark(ak=volc_ak, sk=volc_sk)
                    
                    def _generate(self, messages: List[BaseMessage], stop: Optional[List[str]] = None, run_manager: Optional[Any] = None, **kwargs: Any) -> ChatResult:
                        volc_messages = []
                        for msg in messages:
                            if isinstance(msg, SystemMessage):
                                volc_messages.append({"role": "system", "content": msg.content})
                            elif isinstance(msg, HumanMessage):
                                volc_messages.append({"role": "user", "content": msg.content})
                            elif isinstance(msg, AIMessage):
                                volc_messages.append({"role": "assistant", "content": msg.content})
                            else:
                                volc_messages.append({"role": "user", "content": str(msg.content)})
                        
                        response = self.client.chat.completions.create(
                            model=self.endpoint_id,
                            messages=volc_messages,
                            temperature=self.temperature,
                        )
                        
                        ai_message = AIMessage(content=response.choices[0].message.content)
                        return ChatResult(generations=[ChatGeneration(message=ai_message)])
                    
                    @property
                    def _llm_type(self) -> str:
                        return "doubao"
                
                parts = api_key.split(":")
                if len(parts) >= 3:
                    return ChatDoubao(volc_ak=parts[0], volc_sk=parts[1], endpoint_id=parts[2], temperature=temperature)
                else:
                    raise ValueError("豆包 API Key 格式错误，应为：access_key:secret_key:endpoint_id（用冒号分隔）")
            except ImportError as e:
                raise ValueError(f"豆包初始化失败：缺少依赖库。请运行：pip install 'volcengine-python-sdk[ark]'。错误：{e}")
        except Exception as e:
            raise ValueError(f"豆包初始化失败：{e}。请确保 API Key 格式为：access_key:secret_key:endpoint_id")

    if provider == "文心一言（百度）":
        # 文心一言的 api_key 格式：app_key:app_secret
        parts = api_key.split(":")
        if len(parts) != 2:
            raise ValueError("文心一言 API Key 格式错误，应为：app_key:app_secret（用冒号分隔）")
        
        app_key, app_secret = parts
        
        # 优先使用 langchain-community 的千帆接口（已包含在依赖中）
        try:
            from langchain_community.chat_models import QianfanChatEndpoint
            import os
            
            os.environ["QIANFAN_AK"] = app_key
            os.environ["QIANFAN_SK"] = app_secret
            return QianfanChatEndpoint(
                model=model if model else "ernie-bot-turbo",
                temperature=temperature,
            )
        except ImportError:
            # 备选方案：尝试 langchain-wenxin
            try:
                from langchain_wenxin import ChatWenxin
                return ChatWenxin(
                    baidu_api_key=app_key,
                    baidu_secret_key=app_secret,
                    model=model if model else "ernie-bot-turbo",
                    temperature=temperature,
                )
            except ImportError as e:
                raise ValueError(f"文心一言初始化失败：缺少依赖库。请运行：pip install qianfan（或使用已安装的 langchain-community）。错误：{e}")
        except Exception as e:
            raise ValueError(f"文心一言初始化失败：{e}")

    raise ValueError(f"Unknown provider: {provider}")


# ------------------- 侧边栏：全局配置（用 form 降低 rerun） -------------------
with st.sidebar:
    st.header("全局配置")

    with st.form("global_config_form", clear_on_submit=False):
        gen_provider = st.selectbox(
            "生成&优化 LLM",
            ["DeepSeek", "OpenAI (GPT)", "Tongyi (通义千问)", "Groq", "Moonshot (Kimi)", "豆包（字节跳动）", "文心一言（百度）"],
            index=["DeepSeek", "OpenAI (GPT)", "Tongyi (通义千问)", "Groq", "Moonshot (Kimi)", "豆包（字节跳动）", "文心一言（百度）"].index(
                st.session_state.cfg["gen_provider"]
            ) if st.session_state.cfg["gen_provider"] in ["DeepSeek", "OpenAI (GPT)", "Tongyi (通义千问)", "Groq", "Moonshot (Kimi)", "豆包（字节跳动）", "文心一言（百度）"] else 0,
            key="sb_gen_provider",
        )
        # API Key 输入提示
        if gen_provider == "豆包（字节跳动）":
            api_key_help = "格式：access_key:secret_key:endpoint_id（用冒号分隔）"
        elif gen_provider == "文心一言（百度）":
            api_key_help = "格式：app_key:app_secret（用冒号分隔）"
        else:
            api_key_help = ""
        
        gen_api_key = st.text_input(
            f"{gen_provider} API Key（生成&优化用）",
            type="password",
            value=st.session_state.cfg.get("gen_api_key", ""),
            key="sb_gen_api_key",
            help=api_key_help if api_key_help else None,
        )

        st.markdown("### 验证用LLM（多选）")
        verify_providers = st.multiselect(
            "选择验证模型",
            ["DeepSeek", "OpenAI (GPT)", "Tongyi (通义千问)", "Groq", "Moonshot (Kimi)", "豆包（字节跳动）", "文心一言（百度）"],
            default=st.session_state.cfg.get("verify_providers", []),
            key="sb_verify_providers",
        )

        verify_keys = {}
        old_keys = st.session_state.cfg.get("verify_keys", {})
        for vp in verify_providers:
            # API Key 输入提示
            if vp == "豆包（字节跳动）":
                api_key_help = "格式：access_key:secret_key:endpoint_id（用冒号分隔）"
            elif vp == "文心一言（百度）":
                api_key_help = "格式：app_key:app_secret（用冒号分隔）"
            else:
                api_key_help = None
            
            verify_keys[vp] = st.text_input(
                f"{vp} API Key（验证用）",
                type="password",
                value=old_keys.get(vp, ""),
                key=f"sb_verify_key_{vp}",
                help=api_key_help if api_key_help else None,
            )

        st.markdown("---")
        brand = st.text_input("主品牌名称", value=st.session_state.cfg.get("brand", "汇信云AI软件"), key="sb_brand")
        advantages = st.text_area(
            "核心优势/卖点（AI专属）",
            value=st.session_state.cfg.get(
                "advantages", "AI赋能外贸ERP、打造外贸智能新引擎、AI驱动型ERP、赋能外贸全流程管理、全链路价值闭环"
            ),
            height=140,
            key="sb_advantages",
        )
        competitors = st.text_area(
            "竞品品牌（每行一个，用于对比验证）",
            value=st.session_state.cfg.get("competitors", "南北软件\n睿贝软件\n孚盟软件\n小满软件"),
            height=120,
            key="sb_competitors",
        )

        st.markdown("---")
        temperature = st.slider(
            "生成温度（更稳→更低）",
            0.0,
            1.0,
            float(st.session_state.cfg.get("temperature", 0.7)),
            0.05,
            key="sb_temperature",
        )

        apply_cfg = st.form_submit_button("应用配置（推荐）", use_container_width=True)

    if apply_cfg or not st.session_state.cfg_applied:
        st.session_state.cfg = {
            "gen_provider": gen_provider,
            "gen_api_key": gen_api_key,
            "verify_providers": verify_providers,
            "verify_keys": verify_keys,
            "brand": brand,
            "advantages": advantages,
            "competitors": competitors,
            "temperature": temperature,
        }
        st.session_state.cfg_applied = True

        ok, errs = validate_cfg(st.session_state.cfg)
        st.session_state.cfg_valid = ok
        st.session_state.cfg_errors = errs

    if not st.session_state.cfg_valid:
        st.warning("配置未满足运行条件：\n- " + "\n- ".join(st.session_state.cfg_errors))
    else:
        st.success("配置已就绪，可运行全部模块。")

    st.markdown("---")
    if st.button("重置全部结果（不删除配置）", use_container_width=True, key="sb_reset_all"):
        st.session_state.keywords = []
        st.session_state.generated_contents = []
        st.session_state.zip_bytes = None
        st.session_state.zip_filename = ""
        st.session_state.optimized_article = ""
        st.session_state.opt_changes = ""
        st.session_state.verify_combined = None
        st.toast("已重置全部结果。")

    st.caption("闭环：关键词 → 创作 → 优化 → 验证")

cfg = st.session_state.cfg
brand = cfg["brand"]
advantages = cfg["advantages"]
temperature = float(cfg.get("temperature", 0.7))

competitor_list = [c.strip() for c in cfg["competitors"].split("\n") if c.strip()]
_seen = set()
clean_competitors = []
for c in competitor_list:
    cl = c.lower()
    if cl == brand.lower():
        continue
    if cl in _seen:
        continue
    _seen.add(cl)
    clean_competitors.append(c)
competitor_list = clean_competitors

# ------------------- 初始化 LLM（仅在 cfg_valid 时；且 build_llm 已缓存） -------------------
gen_llm = None
verify_llms = {}

if st.session_state.cfg_valid:
    try:
        gen_llm = build_llm(cfg["gen_provider"], cfg["gen_api_key"], model_defaults(cfg["gen_provider"]), temperature)
    except Exception as e:
        st.error(f"生成LLM加载失败：{e}")

    for vp in cfg["verify_providers"]:
        key = cfg["verify_keys"].get(vp, "").strip()
        if not key:
            continue
        try:
            verify_llms[vp] = build_llm(vp, key, model_defaults(vp), temperature)
        except Exception as e:
            st.error(f"{vp}验证LLM加载失败：{e}")

# ------------------- KPI 总览（极简但更像产品） -------------------
k1, k2, k3, k4 = st.columns(4)
try:
    k1.metric("关键词", len(st.session_state.keywords), border=True)
    k2.metric("内容包", len(st.session_state.generated_contents), border=True)
    k3.metric("文章优化", "已生成" if bool(st.session_state.optimized_article) else "未生成", border=True)
    k4.metric("验证结果", "已生成" if st.session_state.verify_combined is not None else "未生成", border=True)
except TypeError:
    k1.metric("关键词", len(st.session_state.keywords))
    k2.metric("内容包", len(st.session_state.generated_contents))
    k3.metric("文章优化", "已生成" if bool(st.session_state.optimized_article) else "未生成")
    k4.metric("验证结果", "已生成" if st.session_state.verify_combined is not None else "未生成")

st.markdown("---")

# ------------------- 主导航：Tabs（流程更清晰） -------------------
tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs(["1 关键词蒸馏", "2 自动创作", "3 文章优化", "4 多模型验证", "5 历史记录", "6 AI 数据报表"])

# =======================
# Tab1：关键词蒸馏
# =======================
with tab1:
    # 生成模式选择
    generation_mode = st.radio(
        "生成模式",
        ["AI生成", "托词工具", "混合模式"],
        index=["AI生成", "托词工具", "混合模式"].index(st.session_state.kw_generation_mode),
        horizontal=True,
        key="kw_mode_radio"
    )
    st.session_state.kw_generation_mode = generation_mode
    
    # 词库管理和组合模式选择（托词工具和混合模式需要）
    if generation_mode in ["托词工具", "混合模式"]:
        # 初始化词库
        if st.session_state.wordbanks is None:
            st.session_state.wordbanks = st.session_state.keyword_tool.load_wordbanks()
        
        # 初始化组合模式选择
        ss_init("selected_patterns", list(st.session_state.keyword_tool.combination_patterns))
        
        wordbanks = st.session_state.wordbanks
        
        # 组合模式选择
        with st.container(border=True):
            st.markdown("**组合模式选择**")
            pattern_descriptions = st.session_state.keyword_tool.get_pattern_descriptions()
            all_patterns = st.session_state.keyword_tool.combination_patterns
            
            # 显示所有可用模式
            pattern_options = []
            for pattern in all_patterns:
                pattern_str = "+".join(pattern)
                desc = pattern_descriptions.get(pattern_str, pattern_str)
                pattern_options.append((pattern_str, pattern, desc))
            
            # 多选组合模式
            selected_pattern_strs = st.multiselect(
                "选择要使用的组合模式（可多选）",
                options=[opt[0] for opt in pattern_options],
                default=[opt[0] for opt in pattern_options if opt[1] in st.session_state.selected_patterns],
                key="kw_pattern_select",
                help="选择要使用的组合模式，至少选择一个"
            )
            
            # 更新选中的模式
            selected_patterns = []
            for pattern_str, pattern, desc in pattern_options:
                if pattern_str in selected_pattern_strs:
                    selected_patterns.append(pattern)
            st.session_state.selected_patterns = selected_patterns if selected_patterns else all_patterns
            
            # 显示模式说明
            with st.expander("组合模式说明", expanded=False):
                for pattern_str, pattern, desc in pattern_options:
                    st.markdown(f"**{pattern_str}**: {' + '.join(desc)}")
        
        # 词库管理
        with st.expander("词库管理", expanded=False):
            # 词库编辑
            col1, col2 = st.columns([1, 1])
            with col1:
                st.markdown("**词库编辑**")
                bank_types = list(wordbanks.keys())
                selected_bank = st.selectbox("选择词库类型", bank_types, key="kw_bank_select")
                
                # 显示当前词库内容
                current_words = wordbanks[selected_bank]
                edited_words = st.text_area(
                    f"{selected_bank} 词汇（每行一个）",
                    "\n".join(current_words),
                    height=150,
                    key=f"kw_bank_edit_{selected_bank}"
                )
                
                if st.button("更新词库", key=f"kw_update_{selected_bank}"):
                    new_words = [w.strip() for w in edited_words.split("\n") if w.strip()]
                    wordbanks[selected_bank] = new_words
                    st.session_state.wordbanks = wordbanks
                    st.success(f"{selected_bank} 已更新（{len(new_words)} 个词汇）")
            
            with col2:
                st.markdown("**词库导入/导出**")
                # 导出
                wordbanks_json = json.dumps(wordbanks, ensure_ascii=False, indent=2)
                st.download_button(
                    "导出词库（JSON）",
                    wordbanks_json,
                    "wordbanks.json",
                    "application/json",
                    use_container_width=True,
                    key="kw_export_json"
                )
                
                # 导入
                uploaded_wordbanks = st.file_uploader(
                    "导入词库（JSON）",
                    type=["json"],
                    key="kw_import_json"
                )
                if uploaded_wordbanks:
                    try:
                        imported = json.loads(uploaded_wordbanks.read().decode('utf-8'))
                        if isinstance(imported, dict):
                            st.session_state.wordbanks = imported
                            st.success("词库导入成功！")
                            st.rerun()
                    except Exception as e:
                        st.error(f"导入失败：{e}")
                
                # 重置为默认词库
                if st.button("重置为默认词库", use_container_width=True, key="kw_reset_banks"):
                    st.session_state.wordbanks = st.session_state.keyword_tool.load_wordbanks()
                    st.success("已重置为默认词库")
                    st.rerun()
    
    # 生成控制
    with st.container(border=True):
        c1, c2, c3 = st.columns([2, 1, 1])
        with c1:
            st.session_state.kw_last_num = st.slider(
                "生成数量", 10, 100, st.session_state.kw_last_num, key="kw_num"
            )
        with c2:
            # 根据模式调整禁用条件
            if generation_mode == "托词工具":
                run_kw_disabled = False  # 托词工具不需要 LLM
            else:
                run_kw_disabled = (not st.session_state.cfg_valid) or (gen_llm is None)
            
            run_kw = st.button(
                "生成关键词",
                type="primary",
                use_container_width=True,
                disabled=run_kw_disabled,
                key="kw_run",
            )
        with c3:
            if st.button("清空本模块结果", use_container_width=True, key="kw_clear"):
                st.session_state.keywords = []
                st.toast("关键词已清空。")

        if run_kw:
            keywords = []
            
            if generation_mode == "AI生成":
                # 原有 AI 生成逻辑
                keyword_prompt = PromptTemplate.from_template(
                    """
你是AI领域GEO专家，目标是提升品牌在大模型自然回答中的提及率。

【输入】
- 品牌：{brand}
- 核心优势：{advantages}
- 数量：{num_keywords}

【要求（GEO本质）】
1) 覆盖AI用户真实搜索意图：模型对比、推理性能、多模态、实时知识、开源生态、部署成本、行业应用、评测基准
2) 品牌词占比约30%（护城河），70%泛词（新增流量）
3) 口语化、自然、12–28字
4) 去重、均衡意图
5) 输出严格JSON数组：["问题1","问题2",...]

【开始输出JSON数组】
"""
                )

                chain_json = keyword_prompt | gen_llm | JsonOutputParser()
                chain_text = keyword_prompt | gen_llm | StrOutputParser()

                with st.spinner("AI生成中..."):
                    try:
                        result = chain_json.invoke(
                            {"brand": brand, "advantages": advantages, "num_keywords": st.session_state.kw_last_num}
                        )
                        keywords = result if isinstance(result, list) else []
                    except Exception:
                        raw = chain_text.invoke(
                            {"brand": brand, "advantages": advantages, "num_keywords": st.session_state.kw_last_num}
                        )
                        keywords = extract_json_array(raw) or []
            
            elif generation_mode == "托词工具":
                # 托词工具生成
                with st.spinner("组合生成中..."):
                    wordbanks = st.session_state.wordbanks or st.session_state.keyword_tool.load_wordbanks()
                    selected_patterns = st.session_state.get("selected_patterns", st.session_state.keyword_tool.combination_patterns)
                    
                    # 检查词库是否为空
                    empty_banks = [k for k, v in wordbanks.items() if not v]
                    if empty_banks:
                        st.warning(f"以下词库为空，请先添加词汇：{', '.join(empty_banks)}")
                    
                    keywords = st.session_state.keyword_tool.generate_combinations(
                        wordbanks=wordbanks,
                        patterns=selected_patterns,
                        max_results=st.session_state.kw_last_num,
                        similarity_threshold=0.8
                    )
            
            elif generation_mode == "混合模式":
                # 混合模式：先托词生成，再 LLM 润色
                with st.spinner("托词生成中..."):
                    wordbanks = st.session_state.wordbanks or st.session_state.keyword_tool.load_wordbanks()
                    selected_patterns = st.session_state.get("selected_patterns", st.session_state.keyword_tool.combination_patterns)
                    
                    # 检查词库是否为空
                    empty_banks = [k for k, v in wordbanks.items() if not v]
                    if empty_banks:
                        st.warning(f"以下词库为空，请先添加词汇：{', '.join(empty_banks)}")
                    
                    raw_keywords = st.session_state.keyword_tool.generate_combinations(
                        wordbanks=wordbanks,
                        patterns=selected_patterns,
                        max_results=st.session_state.kw_last_num * 2,  # 生成更多，因为会去重
                        similarity_threshold=0.8
                    )
                
                if raw_keywords and gen_llm:
                    with st.spinner("LLM 润色中..."):
                        # 使用 LLM 润色
                        from langchain_core.prompts import PromptTemplate as PT
                        polish_template = PT.from_template("{input}")
                        polish_chain = polish_template | gen_llm | StrOutputParser()
                        keywords = st.session_state.keyword_tool.polish_with_llm(
                            keywords=raw_keywords,
                            llm_chain=polish_chain,
                            brand=brand,
                            max_polish=min(len(raw_keywords), st.session_state.kw_last_num)
                        )
                else:
                    keywords = raw_keywords

            # 清理和去重
            cleaned, seen = [], set()
            for k in keywords:
                if not isinstance(k, str):
                    continue
                kk = k.strip()
                if not kk:
                    continue
                kl = kk.lower()
                if kl in seen:
                    continue
                seen.add(kl)
                cleaned.append(kk)
            
            # 限制数量
            cleaned = cleaned[:st.session_state.kw_last_num]

            if cleaned:
                st.session_state.keywords = cleaned
                # 保存到数据库
                try:
                    storage.save_keywords(cleaned, brand)
                except Exception as e:
                    st.warning(f"关键词已生成，但保存到数据库时出错：{e}")
                st.success(f"生成完成（{len(cleaned)} 条）")
            else:
                error_msg = "生成失败，可能的原因：\n"
                if generation_mode in ["托词工具", "混合模式"]:
                    wordbanks = st.session_state.wordbanks or st.session_state.keyword_tool.load_wordbanks()
                    empty_banks = [k for k, v in wordbanks.items() if not v]
                    if empty_banks:
                        error_msg += f"- 以下词库为空：{', '.join(empty_banks)}\n"
                    if not st.session_state.get("selected_patterns"):
                        error_msg += "- 未选择任何组合模式\n"
                    error_msg += "- 请检查词库配置或选择更多组合模式"
                else:
                    error_msg += "- 请检查 API Key 配置或重试"
                st.error(error_msg)

    if st.session_state.keywords:
        df = pd.DataFrame(st.session_state.keywords, columns=["长尾关键词/问题"])
        st.dataframe(df, use_container_width=True, hide_index=True)
        st.download_button(
            "下载关键词CSV",
            df.to_csv(index=False, encoding="utf-8-sig"),
            f"{sanitize_filename(brand,40)}_keywords.csv",
            mime="text/csv",
            use_container_width=True,
            key="kw_dl_csv",
        )
    else:
        st.info("在左侧完成配置后，点击“生成关键词”。")

# =======================
# Tab2：自动创作内容（含批量 ZIP / GitHub 模板）
# =======================
with tab2:
    top_l, top_r = st.columns([3, 1])
    with top_r:
        if st.button("清空本模块结果", use_container_width=True, key="content_clear"):
            st.session_state.generated_contents = []
            st.session_state.zip_bytes = None
            st.session_state.zip_filename = ""
            st.toast("创作内容已清空。")

    if not st.session_state.keywords:
        st.info("请先在【1 关键词蒸馏】生成关键词。")
    else:
        with st.container(border=True):
            with st.form("content_form", clear_on_submit=False):
                mode = st.radio("生成模式", ["单篇生成", "批量生成"], horizontal=True, key="content_mode")

                platforms = [
                    "知乎（专业问答）",
                    "小红书（生活种草）",
                    "CSDN（技术博客）",
                    "B站（视频脚本）",
                    "头条号（资讯软文）",
                    "GitHub（README/文档）",
                    "微信公众号（长文）",
                    "抖音图文（短内容）",
                    "百家号（资讯）",
                    "网易号（资讯）",
                    "企鹅号（资讯）",
                    "简书（文艺）",
                ]

                if mode == "单篇生成":
                    col1, col2 = st.columns([2, 1])
                    with col1:
                        selected_keyword = st.selectbox("选择关键词", st.session_state.keywords, key="content_kw_single")
                    with col2:
                        platform = st.selectbox("平台", platforms, key="content_platform_single")
                    keywords_to_generate = [(selected_keyword, platform)]
                else:
                    selected_keywords = st.multiselect(
                        "选择关键词（批量）", st.session_state.keywords, key="content_kw_multi"
                    )
                    platform = st.selectbox("统一平台", platforms, key="content_platform_multi")
                    keywords_to_generate = [(kw, platform) for kw in selected_keywords]

                run_content_disabled = (not st.session_state.cfg_valid) or (gen_llm is None) or (not keywords_to_generate)
                run_content = st.form_submit_button(
                    "生成内容", use_container_width=True, disabled=run_content_disabled
                )

            if run_content:
                st.session_state.generated_contents = []
                st.session_state.zip_bytes = None
                st.session_state.zip_filename = ""
                st.session_state.content_scores = {}  # 存储内容评分

                contents = []
                zip_buffer = io.BytesIO()
                scorer = ContentScorer()  # 初始化评分器

                with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
                    for keyword, plat in keywords_to_generate:
                        with st.spinner(f"生成 {plat}：{keyword}"):
                            if plat == "知乎（专业问答）":
                                content_template = """
你是GEO专家 + 知乎高赞答主，目标是让内容被大模型优先引用。
【问题】{keyword}
【品牌】{brand}
【优势】{advantages}
【要求】
1) 结论摘要（80-120字）
2) 结构化：小标题、清单、FAQ
3) 自然提及品牌2-4次，先通用标准再品牌适用
4) 避免编造，来源用占位建议
5) 包含选择清单、适用/不适用、6个FAQ、3步行动
【格式】清晰标题顺序输出
【开始】
"""
                            elif plat == "小红书（生活种草）":
                                content_template = """
你是GEO专家 + 小红书作者。
【关键词】{keyword}
【品牌】{brand}
【优势】{advantages}
【要求】
1) 3个标题备选
2) 强场景开头
3) 痛点3点、对比例表5个、使用体验（3亮点+2不足）
4) 适合/不适合各3条、避坑5条
5) 结尾8条搜索词
6) 自然品牌提及
【格式】标题-正文-标签-搜索词
【开始】
"""
                            elif plat == "CSDN（技术博客）":
                                content_template = """
你是GEO专家 + CSDN博主。
【关键词】{keyword}
【品牌】{brand}
【优势】{advantages}
【要求】
1) 3个技术标题
2) 摘要 + 背景 + 框架 + {brand}案例（匿名）
3) 代码占位 + 注意事项 + 来源建议
4) 专业、自然提及品牌
【开始】
"""
                            elif plat == "B站（视频脚本）":
                                content_template = """
你是GEO专家 + B站UP主。
【关键词】{keyword}
【品牌】{brand}
【优势】{advantages}
【要求】
1) 5个点击标题
2) 开场钩子 + 时间戳分段 + 画面建议
3) {brand}演示部分
4) 描述：时间戳 + 10搜索词 + 15标签
【开始】
"""
                            elif plat == "头条号（资讯软文）":
                                content_template = """
你是GEO专家 + 头条作者。
【关键词】{keyword}
【品牌】{brand}
【优势】{advantages}
【要求】
1) 4个热点标题
2) 列表结构（Top/步骤）
3) 自然推荐品牌
4) 数据占位
【开始】
"""
                            elif plat == "微信公众号（长文）":
                                content_template = """
你是GEO专家 + 微信公众号作者。
【关键词】{keyword}
【品牌】{brand}
【优势】{advantages}
【要求】
1) 3个吸引人的标题（适合公众号）
2) 开头：场景化引入、痛点共鸣
3) 正文：结构化分段、小标题清晰、配图建议（用【配图：xxx】标注）
4) 自然提及品牌3-5次，先讲通用标准再推荐品牌
5) 结尾：总结+行动号召+关注引导
6) 适合公众号的排版：段落分明、重点加粗提示、适当使用emoji
7) 字数：1500-3000字
【格式】清晰分段，标注配图位置
【开始】
"""
                            elif plat == "抖音图文（短内容）":
                                content_template = """
你是GEO专家 + 抖音创作者。
【关键词】{keyword}
【品牌】{brand}
【优势】{advantages}
【要求】
1) 5个爆款标题（吸引点击）
2) 正文：短小精悍，200-500字，适合图文形式
3) 图片建议：每段配图说明（用【配图：xxx】标注），至少3-5张图
4) 结构：痛点→解决方案→品牌推荐→行动
5) 语言：口语化、有节奏感、适合短视频风格
6) 结尾：互动引导（点赞、评论、关注）
7) 标签：10-15个相关话题标签
【格式】标题-正文（分段配图建议）-标签
【开始】
"""
                            elif plat == "百家号（资讯）":
                                content_template = """
你是GEO专家 + 百家号作者。
【关键词】{keyword}
【品牌】{brand}
【优势】{advantages}
【要求】
1) 3个SEO友好标题
2) 开头：热点引入或数据开头
3) 正文：信息密度高、结构化清晰、小标题明确
4) 自然提及品牌2-4次
5) 适合百度搜索：关键词自然分布、长尾词覆盖
6) 字数：800-2000字
7) 结尾：总结+相关推荐
【格式】标题-正文-总结
【开始】
"""
                            elif plat == "网易号（资讯）":
                                content_template = """
你是GEO专家 + 网易号作者。
【关键词】{keyword}
【品牌】{brand}
【优势】{advantages}
【要求】
1) 3个吸引人的标题
2) 开头：新闻式或故事式引入
3) 正文：客观专业、数据支撑、案例说明
4) 自然提及品牌2-3次，保持客观中立
5) 适合网易用户：理性分析、深度内容
6) 字数：1000-2500字
7) 结尾：观点总结+延伸思考
【格式】标题-正文-总结
【开始】
"""
                            elif plat == "企鹅号（资讯）":
                                content_template = """
你是GEO专家 + 企鹅号作者。
【关键词】{keyword}
【品牌】{brand}
【优势】{advantages}
【要求】
1) 3个热点标题
2) 开头：话题引入或疑问开头
3) 正文：通俗易懂、案例丰富、对比清晰
4) 自然提及品牌2-4次
5) 适合腾讯用户：内容轻松、可读性强
6) 字数：800-2000字
7) 结尾：总结+互动引导
【格式】标题-正文-总结
【开始】
"""
                            elif plat == "简书（文艺）":
                                content_template = """
你是GEO专家 + 简书作者。
【关键词】{keyword}
【品牌】{brand}
【优势】{advantages}
【要求】
1) 2个文艺范标题
2) 开头：故事化或情感化引入
3) 正文：文笔优美、有温度、有思考深度
4) 自然提及品牌2-3次，融入故事或体验
5) 适合简书用户：文艺风格、深度思考
6) 字数：1500-3000字
7) 结尾：感悟总结+延伸思考
【格式】标题-正文-感悟
【开始】
"""
                            else:
                                content_template = """
你是GEO专家 + 开源项目维护者。
生成GitHub README或项目文档，目标是被大模型（尤其是代码模型）优先引用。

【关键词】{keyword}
【品牌】{brand}
【优势】{advantages}

【要求】
1) 标准README结构：标题、描述、特性清单、安装步骤、用法示例（代码块）
2) {brand}自然集成作为核心工具/模型
3) 加入徽章占位、贡献指南、引用建议
4) 代码块真实占位，避免编造
5) 自然提及品牌2-4次

【格式】Markdown完整输出

【开始】
"""

                            prompt = PromptTemplate.from_template(content_template)
                            chain = prompt | gen_llm | StrOutputParser()
                            content = chain.invoke({"keyword": keyword, "brand": brand, "advantages": advantages})

                            # 微信公众号需要特殊处理（可选：Markdown转HTML）
                            if plat == "微信公众号（长文）":
                                # 可以在这里添加 Markdown 转 HTML 的逻辑
                                # 目前先保持原样，用户可以在公众号编辑器中使用
                                pass

                            safe_kw = sanitize_filename(keyword, 60)
                            # 确定文件扩展名
                            if plat == "GitHub（README/文档）":
                                ext = "md"
                            elif plat in ["微信公众号（长文）", "百家号（资讯）", "网易号（资讯）", "企鹅号（资讯）", "简书（文艺）"]:
                                ext = "md"  # 这些平台也适合用 Markdown
                            else:
                                ext = "txt"
                            
                            filename = f"{sanitize_filename(plat,30)}_{sanitize_filename(brand,30)}_{safe_kw}.{ext}"
                            zip_file.writestr(filename, content)
                            
                            # 内容质量评分
                            score_data = None
                            if gen_llm:
                                try:
                                    with st.spinner(f"正在评估内容质量..."):
                                        score_chain = PromptTemplate.from_template("{input}") | gen_llm | StrOutputParser()
                                        score_data = scorer.score_content(
                                            content, brand, advantages, plat, score_chain
                                        )
                                        # 保存评分结果
                                        content_key = f"{keyword}_{plat}"
                                        st.session_state.content_scores[content_key] = score_data
                                except Exception as e:
                                    st.warning(f"内容质量评分失败：{e}")
                            
                            contents.append(
                                {
                                    "keyword": keyword,
                                    "platform": plat,
                                    "content": content,
                                    "ext": ext,
                                    "filename": filename,
                                    "score": score_data,  # 添加评分数据
                                }
                            )
                            # 保存到数据库
                            try:
                                storage.save_article(keyword, plat, content, filename, brand)
                            except Exception as e:
                                st.warning(f"内容已生成，但保存到数据库时出错：{e}")

                zip_buffer.seek(0)
                st.session_state.generated_contents = contents
                st.session_state.zip_bytes = zip_buffer.getvalue()
                st.session_state.zip_filename = f"{sanitize_filename(brand,40)}_GEO内容包.zip"
                st.success(f"生成完成（{len(contents)} 篇）")

    if st.session_state.generated_contents:
        if len(st.session_state.generated_contents) == 1:
            item = st.session_state.generated_contents[0]
            
            # 显示内容质量评分
            if item.get("score"):
                from content_scorer import ContentScorer
                temp_scorer = ContentScorer()
                score_data = item["score"]
                scores = score_data.get("scores", {})
                total_score = scores.get("total", 0)
                level, color = temp_scorer.get_score_level(total_score)
                
                st.markdown("#### 📊 内容质量评分")
                col1, col2, col3, col4, col5 = st.columns(5)
                with col1:
                    st.metric("总分", f"{total_score}/100", delta=level, delta_color="off")
                with col2:
                    st.metric("结构化", f"{scores.get('structure', 0)}/25")
                with col3:
                    st.metric("品牌提及", f"{scores.get('brand_mention', 0)}/25")
                with col4:
                    st.metric("权威性", f"{scores.get('authority', 0)}/25")
                with col5:
                    st.metric("可引用性", f"{scores.get('citations', 0)}/25")
                
                # 详细评分和改进建议
                with st.expander("📝 详细评分与改进建议", expanded=True):
                    details = score_data.get("details", {})
                    improvements = score_data.get("improvements", [])
                    strengths = score_data.get("strengths", [])
                    
                    if strengths:
                        st.markdown("**✅ 优点：**")
                        for strength in strengths:
                            st.markdown(f"- {strength}")
                    
                    if improvements:
                        st.markdown("**💡 改进建议：**")
                        for improvement in improvements:
                            st.markdown(f"- {improvement}")
                    
                    st.markdown("**📋 详细评估：**")
                    st.markdown(f"- **结构化**：{details.get('structure', '无')}")
                    st.markdown(f"- **品牌提及**：{details.get('brand_mention', '无')}")
                    st.markdown(f"- **权威性**：{details.get('authority', '无')}")
                    st.markdown(f"- **可引用性**：{details.get('citations', '无')}")
            
            st.markdown("#### 生成内容预览")
            if item["ext"] == "md":
                st.code(item["content"], language="markdown")
            else:
                st.text_area(
                    "内容（可复制发布）",
                    item["content"],
                    height=520,
                    label_visibility="collapsed",
                    key="content_single_preview",
                )

            st.download_button(
                "下载单篇文件",
                item["content"],
                f"{sanitize_filename(brand,40)}_{sanitize_filename(item['keyword'],40)}.{item['ext']}",
                mime=("text/markdown" if item["ext"] == "md" else "text/plain"),
                use_container_width=True,
                key="content_dl_single",
            )

        if st.session_state.zip_bytes:
            st.download_button(
                "下载所有ZIP",
                st.session_state.zip_bytes,
                st.session_state.zip_filename,
                "application/zip",
                use_container_width=True,
                key="content_dl_zip",
            )

        with st.expander("预览最后一篇（批量生成时）", expanded=False):
            last = st.session_state.generated_contents[-1]
            
            # 显示评分（如果有）
            if last.get("score"):
                score_data = last["score"]
                total_score = score_data.get("scores", {}).get("total", 0)
                from content_scorer import ContentScorer
                temp_scorer = ContentScorer()
                level, _ = temp_scorer.get_score_level(total_score)
                st.markdown(f"**内容质量评分：{total_score}/100 ({level})**")
            
            if last["ext"] == "md":
                st.code(last["content"], language="markdown")
            else:
                st.text_area("内容", last["content"], height=420, key="content_last_preview")

# =======================
# Tab3：文章优化
# =======================
with tab3:
    top_l, top_r = st.columns([3, 1])
    with top_r:
        if st.button("清空本模块结果", use_container_width=True, key="opt_clear"):
            st.session_state.optimized_article = ""
            st.session_state.opt_changes = ""
            st.toast("优化结果已清空。")

    with st.container(border=True):
        st.markdown("**粘贴或上传已写文章，一键提升GEO效果（结构化、可引用、自然植入品牌）**")

        with st.form("opt_form", clear_on_submit=False):
            input_mode = st.radio("输入方式", ["粘贴文本", "上传文件（TXT/MD）"], horizontal=True, key="opt_input_mode")

            if input_mode == "粘贴文本":
                original_article = st.text_area("粘贴文章内容", height=360, key="opt_text")
            else:
                uploaded = st.file_uploader("上传TXT或MD文件", type=["txt", "md"], key="opt_uploader")
                original_article = safe_decode_uploaded(uploaded) if uploaded else ""
                if uploaded:
                    st.text_area("上传内容预览", original_article, height=200, disabled=True, key="opt_upload_preview")

            target_platform = st.selectbox(
                "优化目标平台（可选通用）",
                ["通用优化", "知乎（专业问答）", "CSDN（技术博客）", "GitHub（README/文档）", "B站（视频脚本）", "头条号（资讯软文）", 
                 "微信公众号（长文）", "抖音图文（短内容）", "百家号（资讯）", "网易号（资讯）", "企鹅号（资讯）", "简书（文艺）"],
                index=["通用优化", "知乎（专业问答）", "CSDN（技术博客）", "GitHub（README/文档）", "B站（视频脚本）", "头条号（资讯软文）",
                       "微信公众号（长文）", "抖音图文（短内容）", "百家号（资讯）", "网易号（资讯）", "企鹅号（资讯）", "简书（文艺）"].index(
                    st.session_state.opt_platform if st.session_state.opt_platform in ["通用优化", "知乎（专业问答）", "CSDN（技术博客）", "GitHub（README/文档）", "B站（视频脚本）", "头条号（资讯软文）",
                                                                                      "微信公众号（长文）", "抖音图文（短内容）", "百家号（资讯）", "网易号（资讯）", "企鹅号（资讯）", "简书（文艺）"] else 0
                ),
                key="opt_platform_sel",
            )

            run_opt_disabled = (not st.session_state.cfg_valid) or (gen_llm is None) or (not original_article.strip())
            run_opt = st.form_submit_button("开始优化", use_container_width=True, disabled=run_opt_disabled)

        if run_opt:
            st.session_state.opt_platform = target_platform

            optimize_prompt = PromptTemplate.from_template(
                """
你是GEO优化专家，目标是提升文章在大模型中的引用率和品牌自然提及。

【原文章】
{original_article}

【品牌】{brand}
【优势】{advantages}
【目标平台】{platform}

【优化要求（严格GEO原则）】
1) 保留原意和核心信息，不改变事实
2) 增强结构化：标题、清单、FAQ、代码块（适用时）
3) 自然植入品牌2-4次（先通用标准，再品牌适用）
4) 提升权威感：评估维度、匿名案例、来源占位建议（不得编造）
5) 结论先行、信息密度高
6) 长度控制在原长度的1.0-1.3倍
7) 输出两部分：【优化后文章】 + 【变更说明】（列出主要改动点）

【开始优化】
"""
            )

            with st.spinner("优化中..."):
                chain = optimize_prompt | gen_llm | StrOutputParser()
                result = chain.invoke(
                    {"original_article": original_article, "brand": brand, "advantages": advantages, "platform": target_platform}
                )

            if "【优化后文章】" in result and "【变更说明】" in result:
                optimized_article = result.split("【优化后文章】", 1)[1].split("【变更说明】", 1)[0].strip()
                changes = result.split("【变更说明】", 1)[1].strip()
            else:
                optimized_article = result.strip()
                changes = "无详细变更说明（模型未按模板输出）。"

            st.session_state.optimized_article = optimized_article
            st.session_state.opt_changes = changes
            # 保存到数据库
            try:
                storage.save_optimization(original_article, optimized_article, changes, target_platform, brand)
            except Exception as e:
                st.warning(f"优化完成，但保存到数据库时出错：{e}")

    if st.session_state.optimized_article:
        st.markdown("#### 优化后文章")
        # Markdown 平台使用代码显示，其他使用 markdown 渲染
        markdown_platforms = ["GitHub", "微信公众号", "百家号", "网易号", "企鹅号", "简书"]
        if any(p in st.session_state.opt_platform for p in markdown_platforms):
            st.code(st.session_state.optimized_article, language="markdown")
        else:
            st.markdown(st.session_state.optimized_article)

        st.markdown("#### 变更说明")
        st.markdown(st.session_state.opt_changes)

        # 确定文件扩展名
        markdown_platforms = ["GitHub", "微信公众号", "百家号", "网易号", "企鹅号", "简书"]
        ext = "md" if any(p in st.session_state.opt_platform for p in markdown_platforms) else "txt"
        st.download_button(
            "下载优化版",
            st.session_state.optimized_article,
            f"{sanitize_filename(brand,40)}_优化文章.{ext}",
            use_container_width=True,
            key="opt_dl",
        )

# =======================
# Tab4：多模型验证 & 竞品对比
# =======================
with tab4:
    top_l, top_r = st.columns([3, 1])
    with top_r:
        if st.button("清空本模块结果", use_container_width=True, key="verify_clear"):
            st.session_state.verify_combined = None
            st.toast("验证结果已清空。")

    with st.container(border=True):
        with st.form("verify_form", clear_on_submit=False):
            test_queries = st.text_area(
                "测试问题（每行一个，可粘贴关键词）",
                height=140,
                value=st.session_state.verify_last_queries,
                key="verify_queries",
            )
            st.session_state.verify_last_queries = test_queries

            run_verify_disabled = (not st.session_state.cfg_valid) or (not verify_llms) or (not test_queries.strip())
            run_verify = st.form_submit_button("开始验证", use_container_width=True, disabled=run_verify_disabled)

        if run_verify:
            queries = [q.strip() for q in test_queries.split("\n") if q.strip()]
            all_results = []
            brands_to_check = [brand] + competitor_list

            verify_prompt = PromptTemplate.from_template(
                """
你是一名国内AI搜索助手，像百度/微信搜一搜AI总结：结论先行、信息密度高、可复述。
不要编造数据，不确定处说明边界。

【用户问题】{query}
【候选品牌】{brand}
【优势（仅参考）】{advantages}

【要求】
1) 60–90字结论摘要
2) 选择标准5条
3) 推荐方案最多3个（仅当符合标准时提及品牌）
4) 4个FAQ
5) 250–450字，克制语言

【开始回答】
"""
            )

            total = max(1, len(brands_to_check) * len(verify_llms) * len(queries))
            done = 0
            prog = st.progress(0)

            for target_brand in brands_to_check:
                current_advantages = advantages if target_brand == brand else ""
                for model_name, v_llm in verify_llms.items():
                    chain = verify_prompt | v_llm | StrOutputParser()

                    for q in queries:
                        with st.spinner(f"模型：{model_name} | 品牌：{target_brand} | 问题：{q}"):
                            response = chain.invoke({"query": q, "brand": target_brand, "advantages": current_advantages})

                        resp_l = response.lower()
                        tb_l = target_brand.lower()
                        count = resp_l.count(tb_l)
                        first_pos = resp_l.find(tb_l)
                        rank = "前1/3（优先）" if first_pos != -1 and first_pos < len(response) // 3 else ("中后段" if first_pos != -1 else "未提及")

                        all_results.append({"问题": q, "提及次数": count, "位置": rank, "品牌": target_brand, "验证模型": model_name})

                        done += 1
                        prog.progress(min(done / total, 1.0))

            combined = pd.DataFrame(all_results)
            st.session_state.verify_combined = combined
            # 保存到数据库
            try:
                storage.save_verify_results(all_results)
            except Exception as e:
                st.warning(f"验证完成，但保存到数据库时出错：{e}")
            st.success("验证完成")

    if st.session_state.verify_combined is not None:
        combined = st.session_state.verify_combined

        st.markdown("#### 跨模型提及次数对比")
        pivot = combined.pivot_table(index=["问题", "验证模型"], columns="品牌", values="提及次数", fill_value=0)
        st.dataframe(pivot, use_container_width=True)

        st.markdown("#### 多模型竞品提及对比（可视化）")
        fig = px.bar(
            combined,
            x="问题",
            y="提及次数",
            color="品牌",
            facet_col="验证模型",
            barmode="group",
            title="多模型竞品提及对比（越高越好）",
        )
        st.plotly_chart(fig, use_container_width=True)

        st.markdown("#### 平均提及次数（跨模型）")
        summary = combined.groupby(["品牌", "验证模型"])["提及次数"].mean().round(2).unstack()
        st.dataframe(summary, use_container_width=True)

        st.download_button(
            "下载验证报表CSV",
            combined.to_csv(index=False, encoding="utf-8-sig"),
            f"{sanitize_filename(brand,40)}_验证结果.csv",
            mime="text/csv",
            use_container_width=True,
            key="verify_dl_csv",
        )

# =======================
# Tab5：历史记录
# =======================
with tab5:
    st.header("历史记录")
    
    # 统计数据
    try:
        stats = storage.get_stats(brand)
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("关键词总数", stats["keywords_count"])
        col2.metric("文章总数", stats["articles_count"])
        col3.metric("优化记录", stats["optimizations_count"])
        col4.metric("验证结果", stats["verify_results_count"])
    except Exception as e:
        st.error(f"获取统计数据失败：{e}")
        stats = {"keywords_count": 0, "articles_count": 0, "optimizations_count": 0, "verify_results_count": 0}
    
    st.markdown("---")
    
    # 历史文章列表
    st.markdown("#### 历史文章")
    try:
        articles = storage.get_articles(brand=brand)
        if articles:
            articles_df = pd.DataFrame(articles)
            # 只显示关键列
            display_cols = ["keyword", "platform", "created_at"]
            available_cols = [col for col in display_cols if col in articles_df.columns]
            if available_cols:
                st.dataframe(articles_df[available_cols], use_container_width=True, hide_index=True)
            else:
                st.dataframe(articles_df, use_container_width=True, hide_index=True)
            
            # 文章详情查看
            if len(articles) > 0:
                selected_idx = st.selectbox("选择文章查看详情", range(len(articles)), format_func=lambda x: f"{articles[x].get('keyword', 'N/A')} - {articles[x].get('platform', 'N/A')}")
                if selected_idx is not None:
                    selected_article = articles[selected_idx]
                    with st.expander("文章内容", expanded=True):
                        if selected_article.get("content"):
                            if selected_article.get("platform", "").startswith("GitHub"):
                                st.code(selected_article["content"], language="markdown")
                            else:
                                st.text_area("内容", selected_article["content"], height=400, disabled=True, key=f"article_content_{selected_idx}")
        else:
            st.info("暂无历史文章记录。")
    except Exception as e:
        st.error(f"获取历史文章失败：{e}")
    
    st.markdown("---")
    
    # 历史优化记录
    st.markdown("#### 历史优化记录")
    try:
        optimizations = storage.get_optimizations(brand=brand)
        if optimizations:
            opt_df = pd.DataFrame(optimizations)
            display_cols = ["platform", "created_at"]
            available_cols = [col for col in display_cols if col in opt_df.columns]
            if available_cols:
                st.dataframe(opt_df[available_cols], use_container_width=True, hide_index=True)
            else:
                st.dataframe(opt_df.head(10), use_container_width=True, hide_index=True)
            
            if len(optimizations) > 0:
                selected_opt_idx = st.selectbox("选择优化记录查看详情", range(len(optimizations)), format_func=lambda x: f"{optimizations[x].get('platform', 'N/A')} - {optimizations[x].get('created_at', 'N/A')[:10] if optimizations[x].get('created_at') else 'N/A'}")
                if selected_opt_idx is not None:
                    selected_opt = optimizations[selected_opt_idx]
                    with st.expander("优化详情", expanded=True):
                        if selected_opt.get("changes"):
                            st.markdown("**变更说明**")
                            st.markdown(selected_opt["changes"])
                        if selected_opt.get("optimized_content"):
                            st.markdown("**优化后内容**")
                            if "GitHub" in selected_opt.get("platform", ""):
                                st.code(selected_opt["optimized_content"], language="markdown")
                            else:
                                st.text_area("内容", selected_opt["optimized_content"], height=300, disabled=True, key=f"opt_content_{selected_opt_idx}")
        else:
            st.info("暂无优化记录。")
    except Exception as e:
        st.error(f"获取优化记录失败：{e}")
    
    st.markdown("---")
    
    # 历史验证结果
    st.markdown("#### 历史验证结果")
    try:
        verify_df = storage.get_verify_results(brand=brand)
        if not verify_df.empty:
            st.dataframe(verify_df, use_container_width=True, hide_index=True)
            
            # 可视化历史验证结果
            if len(verify_df) > 0:
                st.markdown("#### 历史验证结果可视化")
                fig = px.bar(
                    verify_df,
                    x="问题",
                    y="提及次数",
                    color="品牌",
                    facet_col="验证模型",
                    barmode="group",
                    title="历史验证结果对比",
                )
                st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("暂无验证结果记录。")
    except Exception as e:
        st.error(f"获取验证结果失败：{e}")

# =======================
# Tab6：AI 数据报表
# =======================
with tab6:
    st.markdown("### 📊 AI 数据报表")
    st.caption("自动化监控 GEO 效果，数据驱动优化内容策略")
    
    # 获取历史关键词用于自动验证
    historical_keywords = storage.get_keywords(brand=brand)
    
    col1, col2, col3 = st.columns([2, 1, 1])
    with col1:
        st.markdown("#### 🚀 自动验证任务")
        st.caption("使用历史关键词自动进行多模型验证，生成数据报表")
    
    with col2:
        auto_verify_btn = st.button("开始自动验证", use_container_width=True, 
                                     disabled=(not st.session_state.cfg_valid) or (not verify_llms) or (len(historical_keywords) == 0))
    
    with col3:
        if st.button("刷新报表", use_container_width=True):
            st.rerun()
    
    if len(historical_keywords) == 0:
        st.info("💡 提示：请先在【1 关键词蒸馏】生成关键词，然后才能进行自动验证。")
    elif not verify_llms:
        st.warning("⚠️ 请先在侧边栏配置至少一个验证用 LLM。")
    
    # 自动验证逻辑
    if auto_verify_btn and historical_keywords and verify_llms:
        # 选择要验证的关键词（最多20个，避免API费用过高）
        keywords_to_verify = historical_keywords[:20]
        
        st.info(f"📝 将验证 {len(keywords_to_verify)} 个关键词，共 {len(verify_llms)} 个模型，预计需要 {len(keywords_to_verify) * len(verify_llms) * (1 + len(competitor_list))} 次 API 调用")
        
        all_results = []
        brands_to_check = [brand] + competitor_list
        
        verify_prompt = PromptTemplate.from_template(
            """
你是一名国内AI搜索助手，像百度/微信搜一搜AI总结：结论先行、信息密度高、可复述。
不要编造数据，不确定处说明边界。

【用户问题】{query}
【候选品牌】{brand}
【优势（仅参考）】{advantages}

【要求】
1) 60–90字结论摘要
2) 选择标准5条
3) 推荐方案最多3个（仅当符合标准时提及品牌）
4) 4个FAQ
5) 250–450字，克制语言

【开始回答】
"""
        )
        
        total = max(1, len(brands_to_check) * len(verify_llms) * len(keywords_to_verify))
        done = 0
        prog = st.progress(0)
        status_text = st.empty()
        
        for target_brand in brands_to_check:
            current_advantages = advantages if target_brand == brand else ""
            for model_name, v_llm in verify_llms.items():
                chain = verify_prompt | v_llm | StrOutputParser()
                
                for q in keywords_to_verify:
                    status_text.text(f"验证中：{target_brand} | {model_name} | {q}")
                    try:
                        response = chain.invoke({"query": q, "brand": target_brand, "advantages": current_advantages})
                        
                        resp_l = response.lower()
                        tb_l = target_brand.lower()
                        count = resp_l.count(tb_l)
                        first_pos = resp_l.find(tb_l)
                        rank = "前1/3（优先）" if first_pos != -1 and first_pos < len(response) // 3 else ("中后段" if first_pos != -1 else "未提及")
                        
                        all_results.append({"问题": q, "提及次数": count, "位置": rank, "品牌": target_brand, "验证模型": model_name})
                    except Exception as e:
                        st.warning(f"验证失败：{target_brand} | {model_name} | {q} - {str(e)}")
                    
                    done += 1
                    prog.progress(min(done / total, 1.0))
        
        # 保存验证结果
        if all_results:
            try:
                storage.save_verify_results(all_results)
                st.success(f"✅ 自动验证完成！共验证 {len(all_results)} 条记录")
            except Exception as e:
                st.warning(f"验证完成，但保存到数据库时出错：{e}")
        
        status_text.empty()
        prog.empty()
    
    # 获取所有验证数据（带时间戳）
    verify_df = storage.get_verify_results(brand=brand, include_timestamp=True)
    
    if verify_df.empty:
        st.info("📊 暂无验证数据。请先运行自动验证任务或手动验证。")
    else:
        # 数据概览
        st.markdown("---")
        st.markdown("#### 📈 数据概览")
        
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            total_verifications = len(verify_df)
            st.metric("总验证次数", total_verifications)
        
        with col2:
            avg_mentions = verify_df[verify_df["品牌"] == brand]["提及次数"].mean() if len(verify_df[verify_df["品牌"] == brand]) > 0 else 0
            st.metric("平均提及次数", f"{avg_mentions:.2f}")
        
        with col3:
            if "验证时间" in verify_df.columns:
                latest_date = verify_df["验证时间"].max()
                st.metric("最新验证时间", latest_date.strftime("%Y-%m-%d") if pd.notna(latest_date) else "N/A")
            else:
                st.metric("最新验证时间", "N/A")
        
        with col4:
            unique_queries = verify_df["问题"].nunique()
            st.metric("已验证关键词", unique_queries)
        
        # 1. 提及率趋势图
        if "验证时间" in verify_df.columns and len(verify_df) > 0:
            st.markdown("---")
            st.markdown("#### 📊 提及率趋势图")
            
            # 按日期聚合数据
            brand_df = verify_df[verify_df["品牌"] == brand].copy()
            if len(brand_df) > 0:
                brand_df["日期"] = brand_df["验证时间"].dt.date
                daily_mentions = brand_df.groupby(["日期", "验证模型"])["提及次数"].mean().reset_index()
                daily_mentions["日期"] = pd.to_datetime(daily_mentions["日期"])
                
                fig_trend = px.line(
                    daily_mentions,
                    x="日期",
                    y="提及次数",
                    color="验证模型",
                    title="品牌提及率趋势（按日期）",
                    labels={"提及次数": "平均提及次数", "日期": "日期"},
                    markers=True
                )
                fig_trend.update_layout(hovermode='x unified')
                st.plotly_chart(fig_trend, use_container_width=True)
        
        # 2. 平台贡献度分析（基于文章平台）
        st.markdown("---")
        st.markdown("#### 🌐 平台贡献度分析")
        
        articles = storage.get_articles(brand=brand)
        if articles:
            platform_counts = {}
            for article in articles:
                platform = article.get("platform", "未知")
                platform_counts[platform] = platform_counts.get(platform, 0) + 1
            
            platform_df = pd.DataFrame(list(platform_counts.items()), columns=["平台", "文章数量"])
            platform_df = platform_df.sort_values("文章数量", ascending=False)
            
            fig_platform = px.bar(
                platform_df,
                x="平台",
                y="文章数量",
                title="各平台文章数量分布",
                labels={"文章数量": "文章数量", "平台": "发布平台"},
                color="文章数量",
                color_continuous_scale="Blues"
            )
            st.plotly_chart(fig_platform, use_container_width=True)
        else:
            st.info("暂无文章数据。")
        
        # 3. 关键词效果排名
        st.markdown("---")
        st.markdown("#### 🎯 关键词效果排名")
        
        brand_verify = verify_df[verify_df["品牌"] == brand].copy()
        if len(brand_verify) > 0:
            keyword_performance = brand_verify.groupby("问题")["提及次数"].agg(["mean", "count"]).reset_index()
            keyword_performance.columns = ["关键词", "平均提及次数", "验证次数"]
            keyword_performance = keyword_performance.sort_values("平均提及次数", ascending=False)
            
            # 显示 Top 20
            top_keywords = keyword_performance.head(20)
            
            fig_keywords = px.bar(
                top_keywords,
                x="平均提及次数",
                y="关键词",
                orientation='h',
                title="Top 20 关键词效果排名（平均提及次数）",
                labels={"平均提及次数": "平均提及次数", "关键词": "关键词"},
                color="平均提及次数",
                color_continuous_scale="Greens"
            )
            fig_keywords.update_layout(yaxis={'categoryorder': 'total ascending'})
            st.plotly_chart(fig_keywords, use_container_width=True)
            
            with st.expander("查看完整关键词排名", expanded=False):
                st.dataframe(keyword_performance, use_container_width=True, hide_index=True)
        else:
            st.info("暂无品牌验证数据。")
        
        # 4. 竞品对比分析
        st.markdown("---")
        st.markdown("#### ⚔️ 竞品对比分析")
        
        if len(competitor_list) > 0:
            # 计算各品牌的平均提及次数
            brand_comparison = verify_df.groupby("品牌")["提及次数"].agg(["mean", "count"]).reset_index()
            brand_comparison.columns = ["品牌", "平均提及次数", "验证次数"]
            brand_comparison = brand_comparison.sort_values("平均提及次数", ascending=False)
            
            fig_comparison = px.bar(
                brand_comparison,
                x="品牌",
                y="平均提及次数",
                title="品牌提及率对比（平均提及次数）",
                labels={"平均提及次数": "平均提及次数", "品牌": "品牌"},
                color="平均提及次数",
                color_continuous_scale="Reds"
            )
            st.plotly_chart(fig_comparison, use_container_width=True)
            
            # 详细对比表
            with st.expander("查看详细对比数据", expanded=False):
                st.dataframe(brand_comparison, use_container_width=True, hide_index=True)
            
            # 按验证模型分组的对比
            if "验证模型" in verify_df.columns:
                model_comparison = verify_df.groupby(["品牌", "验证模型"])["提及次数"].mean().reset_index()
                model_comparison = model_comparison.pivot(index="品牌", columns="验证模型", values="提及次数").fillna(0)
                
                fig_model_comparison = px.bar(
                    model_comparison.reset_index(),
                    x="品牌",
                    y=[col for col in model_comparison.columns],
                    title="各模型下的品牌提及率对比",
                    labels={"value": "平均提及次数", "品牌": "品牌"},
                    barmode='group'
                )
                st.plotly_chart(fig_model_comparison, use_container_width=True)
        else:
            st.info("💡 提示：在侧边栏配置竞品品牌后，可查看竞品对比分析。")
        
        # 5. 数据导出
        st.markdown("---")
        st.markdown("#### 💾 数据导出")
        
        col1, col2 = st.columns(2)
        with col1:
            # 导出验证数据
            csv_data = verify_df.to_csv(index=False, encoding="utf-8-sig")
            st.download_button(
                "下载验证数据 CSV",
                csv_data,
                f"{sanitize_filename(brand,40)}_AI数据报表_{pd.Timestamp.now().strftime('%Y%m%d_%H%M%S')}.csv",
                mime="text/csv",
                use_container_width=True,
                key="report_dl_csv"
            )
        
        with col2:
            # 导出关键词效果排名
            if len(brand_verify) > 0:
                keyword_csv = keyword_performance.to_csv(index=False, encoding="utf-8-sig")
                st.download_button(
                    "下载关键词排名 CSV",
                    keyword_csv,
                    f"{sanitize_filename(brand,40)}_关键词排名_{pd.Timestamp.now().strftime('%Y%m%d_%H%M%S')}.csv",
                    mime="text/csv",
                    use_container_width=True,
                    key="keyword_rank_dl_csv"
                )

st.caption("最完整版：GitHub模板 + 真实多模型验证 + 现有文章优化 • GEO全闭环，专注AI品牌影响力")
