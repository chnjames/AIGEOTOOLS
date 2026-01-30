import streamlit as st
import pandas as pd
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import JsonOutputParser, StrOutputParser
import os
from pathlib import Path
import zipfile
import io
import plotly.express as px
import plotly.graph_objects as go
import re
import json
import math
from typing import Optional
from modules.data_storage import DataStorage
from modules.keyword_tool import KeywordTool
from modules.content_scorer import ContentScorer
from modules.eeat_enhancer import EEATEnhancer
from modules.semantic_expander import SemanticExpander
from modules.fact_density_enhancer import FactDensityEnhancer
from modules.schema_generator import SchemaGenerator
from modules.topic_cluster import TopicCluster
from modules.multimodal_prompt import MultimodalPromptGenerator
from modules.roi_analyzer import ROIAnalyzer
from modules.workflow_automation import WorkflowManager, WorkflowStep
from modules.keyword_mining import KeywordMining
from modules.optimization_techniques import OptimizationTechniqueManager
from modules.content_metrics import ContentMetricsAnalyzer
from modules.technical_config_generator import TechnicalConfigGenerator
from modules.negative_monitor import NegativeMonitor
from modules.resource_recommender import ResourceRecommender
from modules.ui import tab_keywords, tab_autowrite
from modules.ui.state import ss_init, init_session_state
from modules.ui.theme import inject_global_theme

APP_TITLE = "GEO 智能内容优化平台"

# ------------------- 页面配置 & 极简美学 CSS（产品级精修，仍然克制） -------------------
st.set_page_config(page_title="GEO 智能内容优化平台", layout="wide", initial_sidebar_state="expanded")

inject_global_theme()
init_session_state()
st.title(APP_TITLE)
st.markdown("<style>button{border-radius:0px !important;}</style>", unsafe_allow_html=True)

st.caption("🚀 AI 驱动的品牌内容策略 · 让您的品牌在 AI 对话中脱颖而出")

# ------------------- 初始化数据存储（SQLite） -------------------
storage = DataStorage(storage_type="sqlite", db_path="geo_data.db")

# ------------------- 成本记录辅助函数 -------------------
def estimate_tokens(text: str) -> int:
    """估算文本的 token 数量：中文约 1.5 字符 = 1 token，英文约 4 字符 = 1 token"""
    if not text:
        return 0
    chinese_chars = sum(1 for char in text if '\u4e00' <= char <= '\u9fff')
    other_chars = len(text) - chinese_chars
    estimated_tokens = int(chinese_chars / 1.5 + other_chars / 4)
    return max(estimated_tokens, len(text) // 4)

def record_api_cost(operation_type: str, provider: str, model: str, input_text: str, output_text: str, keyword: Optional[str] = None, platform: Optional[str] = None, brand: Optional[str] = None):
    """记录 API 调用成本"""
    try:
        roi_analyzer = ROIAnalyzer()
        input_tokens = estimate_tokens(input_text)
        output_tokens = estimate_tokens(output_text)
        total_tokens = input_tokens + output_tokens
        cost_usd, cost_cny = roi_analyzer.calculate_cost(provider, model, input_tokens, output_tokens)
        storage.save_api_call(operation_type=operation_type, provider=provider, model=model, input_tokens=input_tokens, output_tokens=output_tokens, total_tokens=total_tokens, cost_usd=cost_usd, cost_cny=cost_cny, keyword=keyword, platform=platform, brand=brand)
    except Exception:
        pass

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

1. **关键词蒸馏** - AI 生成、托词工具、语义扩展、话题集群、关键词挖掘（行业热点、竞争度、趋势预测）
2. **结构化创作** - 20个平台模板，自动生成符合 GEO 原则的专业内容（E-E-A-T、事实密度、结构化）
3. **内容优化** - E-E-A-T 强化、事实密度增强、结构化优化、JSON-LD Schema 生成
4. **多模型验证** - 7个 AI 平台验证品牌提及率，负面监控，竞品对比分析
5. **数据驱动优化** - ROI 分析、内容质量指标、提及率趋势、平台贡献度、关键词效果排名
6. **平台同步** - GitHub API 发布、12个平台一键复制，自动化内容分发

---

### 🌐 覆盖平台

**内容发布平台（20个）**：
知乎、小红书、CSDN、B站、头条号、GitHub、微信公众号、抖音、百家号、网易号、企鹅号、简书、新浪博客、新浪新闻、搜狐号、QQ空间、邦阅网、一点号、东方财富、原创力文档

**AI 验证平台（7个）**：
DeepSeek、OpenAI、通义千问、Groq、Moonshot、豆包（字节跳动）、文心一言（百度）

**平台同步**：
- GitHub API 发布（1个）
- 一键复制平台（12个）：知乎、CSDN、B站、头条号、微信公众号、百家号、网易号、企鹅号、简书、新浪博客、搜狐号、一点号

---

### ⭐ 核心 GEO 功能

**内容质量优化**：
- ✅ **E-E-A-T 评估与强化**：专业性、经验性、权威性、可信度（0-100分）
- ✅ **事实密度增强**：数据信息、案例信息、标准信息、对比信息（0-100分）
- ✅ **内容质量评分**：结构化、品牌提及、权威性、可引用性（0-100分）
- ✅ **结构化数据**：JSON-LD Schema.org（5种类型）

**智能分析**：
- ✅ **语义扩展**：从单一关键词扩展到10-100个关联词
- ✅ **话题集群**：语义聚类、话题命名、内容规划建议
- ✅ **关键词挖掘**：行业热点、竞争度分析、趋势预测、价值矩阵
- ✅ **多模态提示**：配图描述生成、视频脚本生成

**数据驱动**：
- ✅ **ROI 分析**：成本概览、趋势分析、分布统计、优化建议
- ✅ **内容指标**：Trust Density、Citation Share、Authority Score、Engagement Potential
- ✅ **负面监控**：负面查询生成、情感检测、风险等级、澄清模板

**自动化**：
- ✅ **工作流自动化**：自定义工作流、批量处理、执行历史
- ✅ **技术配置**：robots.txt、sitemap.xml 自动生成

---

### 📊 预期效果

- ✅ **品牌提及率提升**：在 AI 回答中的出现频率显著增加（多模型验证）
- ✅ **搜索排名优化**：内容被大模型优先引用，间接提升 SEO
- ✅ **品牌权威性**：多平台、多角度内容建立专业形象（E-E-A-T 强化）
- ✅ **竞品优势**：通过数据对比，发现并强化差异化优势
- ✅ **ROI 最大化**：数据驱动的关键词策略，成本优化建议
- ✅ **内容质量保证**：自动评分和改进建议，确保符合 GEO 最佳实践
""")

def load_default_cfg():
    """
    从项目根目录的 config.json 读取默认配置，如果不存在则使用内置默认值。
    这样可以在项目中维护密钥和品牌配置，而不依赖系统环境变量。
    """
    base_cfg = {
        "gen_provider": "DeepSeek",
        "gen_api_key": "",
        "verify_providers": ["DeepSeek"],
        "verify_keys": {
            "DeepSeek": ""
        },
        "brand": "汇信云AI软件",
        "advantages": "AI赋能外贸ERP、打造外贸智能新引擎、AI驱动型ERP、赋能外贸全流程管理、全链路价值闭环",
        "competitors": "南北软件\n睿贝软件\n孚盟软件\n小满软件",
        "temperature": 0.7,
    }

    config_path = Path(__file__).with_name("config.json")
    if config_path.exists():
        try:
            with config_path.open("r", encoding="utf-8") as f:
                file_cfg = json.load(f)
            if isinstance(file_cfg, dict):
                base_cfg.update(file_cfg)
        except Exception:
            # 配置文件格式错误时回退到内置默认值，避免整个应用崩溃
            pass
    return base_cfg


def save_cfg_to_file(cfg: dict) -> None:
    """
    将当前生效的配置写入本地 config.json（已在 .gitignore 中，不会提交到仓库）。
    只同步我们负责的几个键，其它自定义字段保持不变。
    """
    config_path = Path(__file__).with_name("config.json")
    try:
        data = {}
        if config_path.exists():
            try:
                with config_path.open("r", encoding="utf-8") as f:
                    loaded = json.load(f)
                if isinstance(loaded, dict):
                    data.update(loaded)
            except Exception:
                # 如果原文件不可解析，丢弃旧内容，重新写入受管配置
                data = {}
        for key in ["gen_provider", "gen_api_key", "verify_providers", "verify_keys", "tongyi_wanxiang_api_key", "brand", "advantages", "competitors", "temperature"]:
            if key in cfg:
                data[key] = cfg[key]
        with config_path.open("w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception:
        # 持久化失败不应阻断页面使用，只做提示
        try:
            st.warning("⚠️ 无法将配置写入本地 config.json，但当前会话已生效。请检查文件权限。")
        except Exception:
            # 在非 Streamlit 环境下忽略 UI 提示错误
            pass


ss_init("cfg", load_default_cfg())
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
ss_init("multimodal_descriptions", {})  # 多模态描述（配图描述、视频脚本等）
ss_init("image_descriptions", [])  # 图片描述列表
ss_init("detail_tab_active", "🎨 增强工具")  # 保存当前激活的详情Tab

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
    st.header("⚙️ 全局配置")
    
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
            # 检查是否有待应用的版本更新
            if "_pending_brand_update" in st.session_state:
                brand_value = st.session_state.pop("_pending_brand_update")
                # 使用一个递增的计数器来强制更新widget（通过改变key）
                widget_counter = st.session_state.get("_widget_update_counter", 0) + 1
                st.session_state["_widget_update_counter"] = widget_counter
                # 使用带计数器的key来创建新的widget实例
                brand_key = f"sb_brand_{widget_counter}"
                brand = st.text_input("主品牌名称", value=brand_value, key=brand_key)
                # 同步到主key，以便后续使用
                st.session_state["sb_brand"] = brand
            else:
                brand = st.text_input("主品牌名称", value=st.session_state.cfg.get("brand", "汇信云AI软件"), key="sb_brand")
            
            # 检查是否有待应用的优势更新
            if "_pending_advantages_update" in st.session_state:
                advantages_value = st.session_state.pop("_pending_advantages_update")
                # 使用一个递增的计数器来强制更新widget（通过改变key）
                widget_counter = st.session_state.get("_widget_update_counter", 0)
                # 使用带计数器的key来创建新的widget实例
                advantages_key = f"sb_advantages_{widget_counter}"
                advantages = st.text_area(
                    "核心优势/卖点（AI专属）",
                    value=advantages_value,
                    height=140,
                    key=advantages_key,
                )
                # 同步到主key，以便后续使用
                st.session_state["sb_advantages"] = advantages
            else:
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
            st.markdown("### 🖼️ 通义万相（图片生成）")
            tongyi_wanxiang_api_key = st.text_input(
                "通义万相 API Key（可选，用于图片生成）",
                type="password",
                value=st.session_state.cfg.get("tongyi_wanxiang_api_key", ""),
                key="sb_tongyi_wanxiang_api_key",
                help="阿里云 DashScope API Key，用于生成文章配图。免费额度每天 100-300 张。",
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
        # 优先从主 key 读取值（如果使用了临时 key 更新，值已同步到主 key）
        brand_value = st.session_state.get("sb_brand", brand)
        advantages_value = st.session_state.get("sb_advantages", advantages)

        st.session_state.cfg = {
            "gen_provider": gen_provider,
            "gen_api_key": gen_api_key,
            "verify_providers": verify_providers,
            "verify_keys": verify_keys,
            "tongyi_wanxiang_api_key": tongyi_wanxiang_api_key,
            "brand": brand_value,
            "advantages": advantages_value,
            "competitors": competitors,
            "temperature": temperature,
        }

        ok, errs = validate_cfg(st.session_state.cfg)
        st.session_state.cfg_valid = ok
        st.session_state.cfg_errors = errs

        if ok:
            # 仅在配置合法时才写入本地配置文件，并标记为已应用
            save_cfg_to_file(st.session_state.cfg)
            st.session_state.cfg_applied = True
        else:
            st.session_state.cfg_applied = False

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
        st.session_state.config_optimization_result = None
        st.session_state.config_hash = None
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
tab1, tab2, tab3, tab4, tab5, tab6, tab7, tab8, tab9, tab10 = st.tabs([
    "🎯 关键词蒸馏", 
    "✍️ 自动创作", 
    "🔧 文章优化",
    "✅ 多模型验证",
    "📚 历史记录",
    "📊 AI 数据报表",
    "⚙️ 工作流自动化",
    "📦 GEO 资源库",
    "🔄 平台同步",
    "🛠️ 配置优化助手"
])

# =======================
# Tab1：关键词蒸馏
# =======================
with tab1:
    tab_keywords.render_tab_keywords(
        storage,
        ss_init,
        gen_llm,
        brand,
        advantages
    )


# =======================
# Tab2：自动创作内容（含批量 ZIP / GitHub 模板）
# =======================
with tab2:
    tab_autowrite.render_tab_autowrite(
        storage,
        ss_init,
        gen_llm,
        brand,
        advantages,
        cfg,
        record_api_cost,
        model_defaults
    )


# =======================
# Tab3：文章优化
# =======================
with tab3:
    header_col1, header_col2 = st.columns([4, 1])
    with header_col1:
        st.markdown("**🔧 文章优化**")
        st.caption("优化已有文章，生成结构化数据和技术配置，提升 GEO 效果")
    with header_col2:
        st.markdown("")  # 空行用于与左侧标题对齐
        if st.button("清空本模块结果", use_container_width=True, key="opt_clear"):
            st.session_state.optimized_article = ""
            st.session_state.opt_changes = ""
            st.toast("优化结果已清空。")

    # === 文章优化功能（主流程） ===
    st.markdown("---")
    st.markdown("**✏️ 文章内容优化**")

    with st.container(border=True):
        st.markdown("粘贴或上传已写文章，一键提升 GEO 效果（结构化、可引用、自然植入品牌）")

        with st.form("opt_form", clear_on_submit=False):
            input_mode = st.radio(
                "输入方式",
                ["粘贴文本", "上传文件（TXT/MD）"],
                horizontal=True,
                key="opt_input_mode",
            )

            if input_mode == "粘贴文本":
                original_article = st.text_area(
                    "粘贴文章内容", height=360, key="opt_text"
                )
            else:
                uploaded = st.file_uploader(
                    "上传 TXT 或 MD 文件",
                    type=["txt", "md"],
                    key="opt_uploader",
                )
                original_article = ""
                if uploaded:
                    try:
                        original_article = safe_decode_uploaded(uploaded) or ""
                    except Exception as e:
                        st.error(f"上传文件解析失败：{e}")
                        original_article = ""

                    if original_article:
                        st.text_area(
                            "上传内容预览",
                            original_article,
                            height=200,
                            disabled=True,
                            key="opt_upload_preview",
                        )

            target_platform = st.selectbox(
                "目标平台（影响文风，可选）",
                [
                    "通用优化",
                    "知乎（专业问答）",
                    "CSDN（技术博客）",
                    "GitHub（README/文档）",
                    "B站（视频脚本）",
                    "头条号（资讯软文）",
                    "微信公众号（长文）",
                    "抖音图文（短内容）",
                    "百家号（资讯）",
                    "网易号（资讯）",
                    "企鹅号（资讯）",
                    "简书（文艺）",
                ],
                index=[
                    "通用优化",
                    "知乎（专业问答）",
                    "CSDN（技术博客）",
                    "GitHub（README/文档）",
                    "B站（视频脚本）",
                    "头条号（资讯软文）",
                    "微信公众号（长文）",
                    "抖音图文（短内容）",
                    "百家号（资讯）",
                    "网易号（资讯）",
                    "企鹅号（资讯）",
                    "简书（文艺）",
                ].index(
                    st.session_state.opt_platform
                    if st.session_state.opt_platform
                    in [
                        "通用优化",
                        "知乎（专业问答）",
                        "CSDN（技术博客）",
                        "GitHub（README/文档）",
                        "B站（视频脚本）",
                        "头条号（资讯软文）",
                        "微信公众号（长文）",
                        "抖音图文（短内容）",
                        "百家号（资讯）",
                        "网易号（资讯）",
                        "企鹅号（资讯）",
                        "简书（文艺）",
                    ]
                    else 0
                ),
                key="opt_platform_sel",
            )

            # 高级优化技巧选择器（可选）
            with st.expander("🎨 高级优化技巧（可选）", expanded=False):
                opt_technique_manager = OptimizationTechniqueManager()
                opt_all_techniques = opt_technique_manager.list_techniques()
                opt_technique_options = [
                    f"{tech['icon']} {tech['name']}" for tech in opt_all_techniques
                ]

                opt_selected_technique_names = st.multiselect(
                    "选择要应用的优化技巧（可多选）",
                    options=opt_technique_options,
                    default=[],
                    key="opt_techniques",
                    help="可选，提高 GEO 效果。技巧会动态调整文章优化策略。",
                )

                # 显示选择的技巧描述
                if opt_selected_technique_names:
                    st.caption("已选择：" + "、".join(opt_selected_technique_names))
                    with st.expander("查看技巧说明", expanded=False):
                        for tech_name in opt_selected_technique_names:
                            tech_icon_name = (
                                tech_name.split(" ", 1)[1]
                                if " " in tech_name
                                else tech_name
                            )
                            for tech in opt_all_techniques:
                                if tech["name"] == tech_icon_name:
                                    st.markdown(f"**{tech['icon']} {tech['name']}**")
                                    st.caption(tech["description"])
                                    break

            run_opt_disabled = (
                (not st.session_state.cfg_valid)
                or (gen_llm is None)
                or (not original_article.strip())
            )
            run_opt = st.form_submit_button(
                "开始优化", use_container_width=True, disabled=run_opt_disabled
            )

            if run_opt_disabled:
                if not original_article.strip():
                    st.caption("请先在上方粘贴文章内容，或上传 TXT/MD 文件。")
                elif not st.session_state.cfg_valid or gen_llm is None:
                    st.caption("当前未检测到可用的生成模型，请先在【全局设置】中完成模型/API 配置。")

        if run_opt:
            st.session_state.opt_platform = target_platform

            optimize_prompt_template = """
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

【输出格式要求】
请严格按照以下结构输出一次，不要在前后添加其他说明或重复输出：
【优化后文章】
（在此输出完整优化后的文章）
【变更说明】
（在此列出主要变更点，使用条目形式）

【E-E-A-T 强化要求】
- 专业性：增强专业术语使用，展示专业知识深度
- 经验性：添加实际使用经验表述（如"实际应用中"、"使用中发现"），至少1处经验性表述
- 权威性：添加来源占位（数据来源、案例来源、标准来源），至少2处来源占位
- 可信度：明确标注不确定信息，避免编造数据，使用占位建议

【开始优化】
"""

            # 根据选择的优化技巧增强 Prompt
            if opt_selected_technique_names:
                opt_technique_manager = OptimizationTechniqueManager()
                opt_technique_ids = opt_technique_manager.get_technique_ids_by_names(
                    [
                        name.split(" ", 1)[1] if " " in name else name
                        for name in opt_selected_technique_names
                    ]
                )
                optimize_prompt_template = opt_technique_manager.enhance_prompt(
                    optimize_prompt_template, opt_technique_ids
                )

            # 对超长文章给出提醒，避免模型上下文溢出
            if len(original_article) > 8000:
                st.warning(
                    "当前文章长度较长（超过 8000 字符），可能导致大模型上下文溢出或响应失败。"
                    " 建议适当拆分文章后分别优化。"
                )

            optimize_prompt = PromptTemplate.from_template(optimize_prompt_template)

            try:
                with st.spinner("优化中..."):
                    chain = optimize_prompt | gen_llm | StrOutputParser()

                    # 准备输入文本用于成本估算
                    input_text = optimize_prompt.template.format(
                        original_article=original_article[
                            :500
                        ],  # 只取前500字符用于估算
                        brand=brand,
                        advantages=advantages,
                        platform=target_platform,
                    )
                    result = chain.invoke(
                        {
                            "original_article": original_article,
                            "brand": brand,
                            "advantages": advantages,
                            "platform": target_platform,
                        }
                    )

                    # 记录成本
                    if gen_llm:
                        try:
                            model_name = (
                                getattr(gen_llm, "model_name", None)
                                or getattr(gen_llm, "model", None)
                                or model_defaults(cfg["gen_provider"])
                            )
                            provider = cfg["gen_provider"]
                            record_api_cost(
                                operation_type="优化",
                                provider=provider,
                                model=model_name,
                                input_text=original_article[
                                    :1000
                                ],  # 使用实际输入文本的前1000字符
                                output_text=result,
                                platform=target_platform,
                                brand=brand,
                            )
                        except Exception:
                            # 记录成本失败不影响主流程
                            pass

                if "【优化后文章】" in result and "【变更说明】" in result:
                    optimized_article = (
                        result.split("【优化后文章】", 1)[1]
                        .split("【变更说明】", 1)[0]
                        .strip()
                    )
                    changes = result.split("【变更说明】", 1)[1].strip()
                else:
                    optimized_article = result.strip()
                    changes = "无详细变更说明（模型未按模板输出）。"

                st.session_state.optimized_article = optimized_article
                st.session_state.opt_changes = changes
                # 保存到数据库
                try:
                    storage.save_optimization(
                        original_article,
                        optimized_article,
                        changes,
                        target_platform,
                        brand,
                    )
                except Exception as e:
                    st.warning(f"优化完成，但保存到数据库时出错：{e}")
            except Exception as e:
                st.error(f"文章优化失败：{e}")

    # === 优化结果 & 质量评估 ===
    if st.session_state.optimized_article:
        st.markdown("---")
        st.markdown("#### 📝 优化结果")

        # 结果 Tabs：优化后文章 / 变更说明
        result_tab1, result_tab2 = st.tabs(["📝 优化后文章", "🧾 变更说明"])
        with result_tab1:
            markdown_platforms = ["GitHub", "微信公众号", "百家号", "网易号", "企鹅号", "简书"]
            if any(p in st.session_state.opt_platform for p in markdown_platforms):
                st.code(st.session_state.optimized_article, language="markdown")
            else:
                st.markdown(st.session_state.optimized_article)

            # 确定文件扩展名
            ext = (
                "md"
                if any(p in st.session_state.opt_platform for p in markdown_platforms)
                else "txt"
            )
            st.download_button(
                "下载优化版",
                st.session_state.optimized_article,
                f"{sanitize_filename(brand,40)}_优化文章.{ext}",
                use_container_width=True,
                key="opt_dl",
            )

        with result_tab2:
            st.markdown("#### 变更说明")
            st.markdown(st.session_state.opt_changes)

        # 提供简单的版本回退能力
        if (
            st.session_state.get("optimized_article_backup")
            and st.session_state.optimized_article_backup
            != st.session_state.optimized_article
        ):
            if st.button("恢复至强化前版本", key="opt_restore_backup"):
                st.session_state.optimized_article = (
                    st.session_state.optimized_article_backup
                )
                st.toast("已恢复至强化前版本。")

        st.markdown(
            "可选步骤：对优化后的文章进行质量评估与再强化（会调用额外模型）。"
        )

        # E-E-A-T 评估和强化区域
        st.markdown("#### 🎯 E-E-A-T 强化 + 来源占位")
        st.caption("评估和强化内容的专业性、经验性、权威性、可信度")

        eeat_col1, eeat_col2 = st.columns(2)

        with eeat_col1:
            assess_eeat_btn = st.button(
                "📊 评估 E-E-A-T",
                use_container_width=True,
                disabled=(not st.session_state.cfg_valid) or (gen_llm is None),
            )

        with eeat_col2:
            enhance_eeat_btn = st.button(
                "✨ 强化 E-E-A-T",
                use_container_width=True,
                disabled=(not st.session_state.cfg_valid) or (gen_llm is None),
            )
            st.caption("强化会覆盖当前优化结果，建议先下载备份。")

        # 初始化 E-E-A-T 相关状态
        ss_init("eeat_assessment", None)
        ss_init("eeat_enhanced_content", "")
        ss_init("eeat_source_placeholders", [])
        ss_init("optimized_article_backup", "")

        # E-E-A-T 评估
        if assess_eeat_btn and gen_llm:
            eeat_enhancer = EEATEnhancer()
            with st.spinner("正在评估 E-E-A-T..."):
                try:
                    score_chain = (
                        PromptTemplate.from_template("{input}")
                        | gen_llm
                        | StrOutputParser()
                    )
                    assessment = eeat_enhancer.assess_eeat(
                        st.session_state.optimized_article,
                        brand,
                        advantages,
                        st.session_state.opt_platform,
                        score_chain,
                    )
                    st.session_state.eeat_assessment = assessment
                except Exception as e:
                    st.error(f"E-E-A-T 评估失败：{e}")

        # E-E-A-T 强化（带备份与安全校验）
        if enhance_eeat_btn and gen_llm:
            eeat_enhancer = EEATEnhancer()
            st.session_state.optimized_article_backup = (
                st.session_state.optimized_article
            )
            with st.spinner("正在强化 E-E-A-T..."):
                try:
                    enhance_chain = (
                        PromptTemplate.from_template("{input}")
                        | gen_llm
                        | StrOutputParser()
                    )
                    enhanced = eeat_enhancer.enhance_eeat(
                        st.session_state.optimized_article,
                        brand,
                        advantages,
                        st.session_state.opt_platform,
                        enhance_chain,
                    )
                    new_content = enhanced.get("enhanced_content", "") or ""
                    if not new_content.strip() or len(new_content.strip()) < 100:
                        st.error(
                            "E-E-A-T 强化失败：模型返回内容异常，已保留强化前版本。"
                        )
                    else:
                        st.session_state.eeat_enhanced_content = new_content
                        st.session_state.eeat_source_placeholders = enhanced.get(
                            "source_placeholders", []
                        )
                        st.session_state.optimized_article = new_content
                        st.success(
                            f"✅ E-E-A-T 强化完成！已添加 {len(st.session_state.eeat_source_placeholders)} 个来源占位"
                        )
                except Exception as e:
                    st.error(f"E-E-A-T 强化失败：{e}")

        # 显示 E-E-A-T 评估结果
        if st.session_state.eeat_assessment:
            assessment = st.session_state.eeat_assessment
            scores = assessment.get("eeat_scores", {})
            total_score = scores.get("total", 0)
            eeat_enhancer = EEATEnhancer()
            level, color = eeat_enhancer.get_eeat_level(total_score)

            st.markdown("##### 📊 E-E-A-T 评估结果")
            col1, col2, col3, col4, col5 = st.columns(5)
            with col1:
                st.metric("总分", f"{total_score}/100", delta=level, delta_color="off")
            with col2:
                st.metric("专业性", f"{scores.get('expertise', 0)}/25")
            with col3:
                st.metric("经验性", f"{scores.get('experience', 0)}/25")
            with col4:
                st.metric("权威性", f"{scores.get('authoritativeness', 0)}/25")
            with col5:
                st.metric("可信度", f"{scores.get('trustworthiness', 0)}/25")

            # 详细评估和改进建议
            with st.container(border=True):
                st.markdown("##### 📝 详细评估与改进建议")
                details = assessment.get("details", {})
                improvements = assessment.get("improvements", [])
                source_suggestions = assessment.get("source_suggestions", [])

                st.markdown("**详细评估：**")
                st.markdown(f"- **专业性**：{details.get('expertise', '无')}")
                st.markdown(f"- **经验性**：{details.get('experience', '无')}")
                st.markdown(f"- **权威性**：{details.get('authoritativeness', '无')}")
                st.markdown(f"- **可信度**：{details.get('trustworthiness', '无')}")

                if improvements:
                    st.markdown("**💡 改进建议：**")
                    for improvement in improvements:
                        st.markdown(f"- {improvement}")

                if source_suggestions:
                    st.markdown("**📚 来源占位建议：**")
                    for suggestion in source_suggestions:
                        st.markdown(f"- {suggestion}")

                # 来源占位检查
                placeholders = assessment.get("source_placeholders", {})
                if placeholders:
                    st.markdown("**✅ 已检测到的来源占位：**")
                    if placeholders.get("data_sources"):
                        st.markdown(
                            f"- 数据来源：{len(placeholders['data_sources'])} 处"
                        )
                    if placeholders.get("case_sources"):
                        st.markdown(
                            f"- 案例来源：{len(placeholders['case_sources'])} 处"
                        )
                    if placeholders.get("standard_sources"):
                        st.markdown(
                            f"- 标准来源：{len(placeholders['standard_sources'])} 处"
                        )
                    if placeholders.get("expert_opinions"):
                        st.markdown(
                            f"- 专家观点：{len(placeholders['expert_opinions'])} 处"
                        )

        # 显示 E-E-A-T 强化后的来源占位清单
        if st.session_state.eeat_source_placeholders:
            with st.container(border=True):
                st.markdown("##### 📚 来源占位清单")
                for placeholder in st.session_state.eeat_source_placeholders:
                    st.markdown(f"- {placeholder}")

        # 事实密度 + 结构化块评估和强化
        st.markdown("---")
        st.markdown("#### 📊 事实密度 + 结构化块")
        st.caption("评估和强化内容的事实信息密度和结构化程度")

        fact_col1, fact_col2 = st.columns(2)

        with fact_col1:
            assess_opt_fact = st.button(
                "📊 评估事实密度",
                use_container_width=True,
                disabled=(not st.session_state.cfg_valid) or (gen_llm is None),
            )

        with fact_col2:
            enhance_opt_fact = st.button(
                "✨ 强化事实密度",
                use_container_width=True,
                disabled=(not st.session_state.cfg_valid) or (gen_llm is None),
            )
            st.caption("强化会覆盖当前优化结果，建议先下载备份。")

        # 初始化事实密度状态
        ss_init("opt_fact_assessment", None)
        ss_init("opt_fact_enhanced", "")
        ss_init("opt_fact_details", [])

        # 事实密度评估
        if assess_opt_fact and gen_llm:
            fact_enhancer = FactDensityEnhancer()
            with st.spinner("正在评估事实密度和结构化块..."):
                try:
                    score_chain = (
                        PromptTemplate.from_template("{input}")
                        | gen_llm
                        | StrOutputParser()
                    )
                    assessment = fact_enhancer.assess_fact_density(
                        st.session_state.optimized_article,
                        brand,
                        advantages,
                        st.session_state.opt_platform,
                        score_chain,
                    )
                    st.session_state.opt_fact_assessment = assessment
                except Exception as e:
                    st.error(f"事实密度评估失败：{e}")

        # 事实密度强化（带备份与安全校验）
        if enhance_opt_fact and gen_llm:
            fact_enhancer = FactDensityEnhancer()
            st.session_state.optimized_article_backup = (
                st.session_state.optimized_article
            )
            with st.spinner("正在强化事实密度和结构化块..."):
                try:
                    enhance_chain = (
                        PromptTemplate.from_template("{input}")
                        | gen_llm
                        | StrOutputParser()
                    )
                    enhanced = fact_enhancer.enhance_fact_density(
                        st.session_state.optimized_article,
                        brand,
                        advantages,
                        st.session_state.opt_platform,
                        enhance_chain,
                    )
                    new_content = enhanced.get("enhanced_content", "") or ""
                    if not new_content.strip() or len(new_content.strip()) < 100:
                        st.error(
                            "事实密度强化失败：模型返回内容异常，已保留强化前版本。"
                        )
                    else:
                        st.session_state.opt_fact_enhanced = new_content
                        st.session_state.opt_fact_details = enhanced.get(
                            "enhancement_details", []
                        )
                        st.session_state.optimized_article = new_content
                        st.success(
                            f"✅ 事实密度强化完成！已添加 {len(st.session_state.opt_fact_details)} 处事实信息和结构化块"
                        )
                except Exception as e:
                    st.error(f"事实密度强化失败：{e}")

        # 显示事实密度评估结果
        if st.session_state.opt_fact_assessment:
            assessment = st.session_state.opt_fact_assessment
            scores = assessment.get("scores", {})
            total_score = scores.get("total", 0)
            fact_enhancer = FactDensityEnhancer()
            level, color = fact_enhancer.get_score_level(total_score)

            st.markdown("##### 📊 事实密度 + 结构化评估结果")
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("总分", f"{total_score}/100", delta=level, delta_color="off")
            with col2:
                st.metric("事实密度", f"{scores.get('fact_density', 0)}/50")
            with col3:
                st.metric("结构化", f"{scores.get('structure', 0)}/50")

            # 使用 tabs 组织分析结果
            fact_analysis = assessment.get("fact_analysis", {})
            structure_analysis = assessment.get("structure_analysis", {})
            has_details = bool(st.session_state.get("opt_fact_details"))

            # 构建可用的 tabs
            tab_labels = []
            if fact_analysis:
                tab_labels.append("📈 事实密度")
            if structure_analysis:
                tab_labels.append("🏗️ 结构化块")
            if has_details:
                tab_labels.append("📝 强化详情")

            if tab_labels:
                analysis_tabs = st.tabs(tab_labels)
                tab_idx = 0

                # 事实密度分析
                if fact_analysis:
                    with analysis_tabs[tab_idx]:
                        with st.container(border=True):
                            col1, col2, col3, col4, col5, col6 = st.columns(6)
                            with col1:
                                st.metric("数据", fact_analysis.get("data_count", 0))
                            with col2:
                                st.metric("案例", fact_analysis.get("case_count", 0))
                            with col3:
                                st.metric("标准", fact_analysis.get("standard_count", 0))
                            with col4:
                                st.metric(
                                    "对比", fact_analysis.get("comparison_count", 0)
                                )
                            with col5:
                                st.metric("时间", fact_analysis.get("time_count", 0))
                            with col6:
                                st.metric("来源", fact_analysis.get("source_count", 0))

                            missing_facts = fact_analysis.get("missing_facts", [])
                            if missing_facts:
                                st.markdown("**缺失的事实类型：**")
                                for fact in missing_facts:
                                    st.markdown(f"- {fact}")
                    tab_idx += 1

                # 结构化分析
                if structure_analysis:
                    with analysis_tabs[tab_idx]:
                        with st.container(border=True):
                            col1, col2, col3, col4 = st.columns(4)
                            with col1:
                                st.markdown(
                                    f"**标题层级**：{'✅' if structure_analysis.get('has_title') else '❌'}"
                                )
                                st.markdown(
                                    f"**结论摘要**：{'✅' if structure_analysis.get('has_summary') else '❌'}"
                                )
                            with col2:
                                st.markdown(
                                    f"**清单列表**：{'✅' if structure_analysis.get('has_list') else '❌'}"
                                )
                                st.markdown(
                                    f"**FAQ部分**：{'✅' if structure_analysis.get('has_faq') else '❌'}"
                                )
                            with col3:
                                st.markdown(
                                    f"**代码块**：{'✅' if structure_analysis.get('has_code') else '❌'}"
                                )
                                st.markdown(
                                    f"**对比表格**：{'✅' if structure_analysis.get('has_table') else '❌'}"
                                )
                            with col4:
                                st.markdown(
                                    f"**步骤说明**：{'✅' if structure_analysis.get('has_steps') else '❌'}"
                                )
                                st.markdown(
                                    f"**总结部分**：{'✅' if structure_analysis.get('has_conclusion') else '❌'}"
                                )

                            missing_blocks = structure_analysis.get("missing_blocks", [])
                            if missing_blocks:
                                st.markdown("**缺失的结构化块：**")
                                for block in missing_blocks:
                                    st.markdown(f"- {block}")
                    tab_idx += 1

                # 强化详情
                if has_details:
                    with analysis_tabs[tab_idx]:
                        with st.container(border=True):
                            for detail in st.session_state.opt_fact_details:
                                st.markdown(f"- {detail}")

    # === 高级：结构化 Schema & 技术配置（折叠区） ===
    with st.expander(
        "高级：结构化 Schema & 技术 SEO 配置（可选）", expanded=False
    ):
        # 结构化数据生成
        st.markdown("**📋 结构化数据生成**")
        st.caption(
            "生成符合 Schema.org 规范的 JSON-LD 代码，提升品牌在 AI 模型中的实体识别和权威性"
        )

        with st.container(border=True):
            schema_col1, schema_col2 = st.columns([2, 1])

            with schema_col1:
                schema_type = st.selectbox(
                    "Schema 类型",
                    [
                        "Organization（组织/公司）",
                        "SoftwareApplication（软件应用）",
                        "Product（产品）",
                        "Service（服务）",
                        "组合（Organization + SoftwareApplication）",
                    ],
                    index=1,
                    key="schema_type_sel",
                    help="选择适合您品牌的 Schema 类型",
                )

            with schema_col2:
                generate_schema_btn = st.button(
                    "🚀 生成 JSON-LD",
                    use_container_width=True,
                    key="generate_schema_btn",
                )

            # 初始化 JSON-LD 相关状态
            ss_init("generated_json_ld", None)
            ss_init("generated_html_script", None)

            # 生成 JSON-LD（带基础信息校验）
            if generate_schema_btn:
                if not brand or not advantages or len(brand.strip()) < 2:
                    st.warning(
                        "请先在基础信息中填写品牌名称和优势，再生成 Schema。"
                    )
                else:
                    try:
                        schema_gen = SchemaGenerator()

                        if schema_type == "Organization（组织/公司）":
                            schema_dict = schema_gen.generate_organization_schema(
                                brand_name=brand,
                                description=advantages,
                                url="",  # 用户可以在生成后手动添加
                                logo="",
                                founding_date="",
                            )
                        elif schema_type == "SoftwareApplication（软件应用）":
                            schema_dict = schema_gen.generate_software_application_schema(
                                brand_name=brand,
                                application_name=brand,
                                description=advantages,
                                url="",
                                application_category="BusinessApplication",
                                operating_system="Web",
                            )
                        elif schema_type == "Product（产品）":
                            schema_dict = schema_gen.generate_product_schema(
                                brand_name=brand,
                                product_name=brand,
                                description=advantages,
                                url="",
                            )
                        elif schema_type == "Service（服务）":
                            schema_dict = schema_gen.generate_service_schema(
                                brand_name=brand,
                                service_name=brand,
                                description=advantages,
                                url="",
                            )
                        else:  # 组合
                            schema_dict = schema_gen.generate_combined_schema(
                                brand_name=brand,
                                advantages=advantages,
                                schema_types=[
                                    "Organization",
                                    "SoftwareApplication",
                                ],
                            )

                        # 格式化输出
                        json_ld_code = schema_gen.format_json_ld(schema_dict)
                        html_script = schema_gen.generate_html_script_tag(
                            schema_dict
                        )

                        st.session_state.generated_json_ld = json_ld_code
                        st.session_state.generated_html_script = html_script

                        st.success("✅ JSON-LD Schema 生成成功！")
                    except Exception as e:
                        st.error(f"JSON-LD 生成失败：{e}")

            # 显示生成的 JSON-LD
            if st.session_state.generated_json_ld:
                st.markdown("##### 📄 JSON-LD 代码")
                st.code(st.session_state.generated_json_ld, language="json")

                st.markdown("##### 📄 HTML Script 标签（可直接嵌入网页）")
                st.code(st.session_state.generated_html_script, language="html")

                # 下载按钮
                col1, col2 = st.columns(2)
                with col1:
                    st.download_button(
                        "下载 JSON-LD",
                        st.session_state.generated_json_ld,
                        f"{sanitize_filename(brand,40)}_schema.json",
                        mime="application/json",
                        use_container_width=True,
                        key="schema_dl_json",
                    )
                with col2:
                    st.download_button(
                        "下载 HTML Script",
                        st.session_state.generated_html_script,
                        f"{sanitize_filename(brand,40)}_schema.html",
                        mime="text/html",
                        use_container_width=True,
                        key="schema_dl_html",
                    )

                st.info(
                    "💡 **使用说明**：将 HTML Script 标签复制到您的官网 `<head>` 部分，或将 JSON-LD 代码添加到 GitHub README 中。"
                )

        # 技术配置生成
        st.markdown("---")
        st.markdown("**⚙️ 技术配置生成**")
        st.caption("生成 robots.txt、sitemap.xml 等技术配置文件，提升内容收录效果（提升 20-30%）")

        with st.container(border=True):
            config_tab1, config_tab2 = st.tabs(["🤖 robots.txt", "🗺️ sitemap.xml"])

            # robots.txt 生成
            with config_tab1:
                st.markdown("##### 🤖 robots.txt 生成")
                st.caption("控制搜索引擎爬虫的访问权限，提升内容收录效果")

                robots_col1, robots_col2 = st.columns([2, 1])

                with robots_col1:
                    robots_base_url = st.text_input(
                        "网站基础 URL",
                        value="",
                        key="robots_base_url",
                        placeholder="https://example.com",
                        help="您的网站基础 URL（如 https://example.com）",
                    )

                with robots_col2:
                    generate_robots_btn = st.button(
                        "🚀 生成 robots.txt",
                        use_container_width=True,
                        key="generate_robots_btn",
                    )

                # 允许/禁止路径配置
                robots_config_col1, robots_config_col2 = st.columns(2)

                with robots_config_col1:
                    allow_paths_input = st.text_area(
                        "允许爬取的路径（每行一个）",
                        value="/\n/blog\n/docs",
                        key="robots_allow_paths",
                        help="每行一个路径，如 /、/blog、/docs",
                        height=100,
                    )

                with robots_config_col2:
                    disallow_paths_input = st.text_area(
                        "禁止爬取的路径（每行一个）",
                        value="/admin\n/private\n/api",
                        key="robots_disallow_paths",
                        help="每行一个路径，如 /admin、/private、/api",
                        height=100,
                    )

                # 初始化状态
                ss_init("generated_robots_txt", None)

                # 生成 robots.txt（带 URL 校验）
                if generate_robots_btn:
                    if not robots_base_url.strip():
                        st.error("请填写网站基础 URL（如 https://example.com）。")
                    else:
                        if not robots_base_url.startswith("http"):
                            st.warning(
                                "建议使用完整 URL（含 http/https），避免 robots.txt 中出现无效链接。"
                            )
                        try:
                            config_gen = TechnicalConfigGenerator()

                            # 解析允许路径
                            allow_paths = (
                                [
                                    p.strip()
                                    for p in allow_paths_input.split("\n")
                                    if p.strip()
                                ]
                                if allow_paths_input
                                else None
                            )

                            # 解析禁止路径
                            disallow_paths = (
                                [
                                    p.strip()
                                    for p in disallow_paths_input.split("\n")
                                    if p.strip()
                                ]
                                if disallow_paths_input
                                else None
                            )

                            robots_txt = config_gen.generate_robots_txt(
                                base_url=robots_base_url,
                                allow_paths=allow_paths,
                                disallow_paths=disallow_paths,
                                sitemap_url="",  # 自动生成
                                user_agent="*",
                                crawl_delay=None,
                            )

                            st.session_state.generated_robots_txt = robots_txt
                            st.success("✅ robots.txt 生成成功！")
                        except Exception as e:
                            st.error(f"robots.txt 生成失败：{e}")

                # 显示生成的 robots.txt
                if st.session_state.generated_robots_txt:
                    st.markdown("##### 📄 robots.txt 内容")
                    st.code(st.session_state.generated_robots_txt, language="text")

                    st.download_button(
                        "下载 robots.txt",
                        st.session_state.generated_robots_txt,
                        "robots.txt",
                        mime="text/plain",
                        use_container_width=True,
                        key="robots_dl",
                    )

                    st.info(
                        "💡 **使用说明**：将 robots.txt 文件上传到您网站的根目录（如 https://example.com/robots.txt）"
                    )

            # sitemap.xml 生成
            with config_tab2:
                st.markdown("##### 🗺️ sitemap.xml 生成")
                st.caption("帮助搜索引擎发现和索引您的所有页面，提升内容收录效果")

                sitemap_col1, sitemap_col2 = st.columns([2, 1])

                with sitemap_col1:
                    sitemap_base_url = st.text_input(
                        "网站基础 URL",
                        value="",
                        key="sitemap_base_url",
                        placeholder="https://example.com",
                        help="您的网站基础 URL（如 https://example.com）",
                    )

                with sitemap_col2:
                    generate_sitemap_btn = st.button(
                        "🚀 生成 sitemap.xml",
                        use_container_width=True,
                        key="generate_sitemap_btn",
                    )

                # 选择数据源
                sitemap_source = st.radio(
                    "数据源",
                    ["基于关键词生成", "基于历史文章生成"],
                    key="sitemap_source",
                    horizontal=True,
                )

                # 初始化状态
                ss_init("generated_sitemap_xml", None)

                # 生成 sitemap.xml（带 URL 校验）
                if generate_sitemap_btn:
                    if not sitemap_base_url.strip():
                        st.error("请填写网站基础 URL（如 https://example.com）。")
                    else:
                        if not sitemap_base_url.startswith("http"):
                            st.warning(
                                "建议使用完整 URL（含 http/https），避免 sitemap.xml 中出现无效链接。"
                            )
                        try:
                            config_gen = TechnicalConfigGenerator()

                            if sitemap_source == "基于关键词生成":
                                # 基于关键词生成
                                keywords_for_sitemap = (
                                    st.session_state.keywords
                                    if st.session_state.keywords
                                    else []
                                )

                                if not keywords_for_sitemap:
                                    st.warning(
                                        "⚠️ 请先在【1 关键词蒸馏】生成关键词，或选择【基于历史文章生成】"
                                    )
                                else:
                                    sitemap_xml = (
                                        config_gen.generate_sitemap_xml(
                                            base_url=sitemap_base_url,
                                            keywords=keywords_for_sitemap,
                                            lastmod=None,  # 使用当前日期
                                            changefreq="weekly",
                                            priority=0.8,
                                        )
                                    )
                                    st.session_state.generated_sitemap_xml = (
                                        sitemap_xml
                                    )
                                    st.success(
                                        f"✅ sitemap.xml 生成成功！包含 {len(keywords_for_sitemap)} 个 URL"
                                    )
                            else:
                                # 基于历史文章生成
                                try:
                                    articles = storage.get_articles(brand=brand)

                                    if not articles:
                                        st.warning(
                                            "⚠️ 暂无历史文章，请先生成内容，或选择【基于关键词生成】"
                                        )
                                    else:
                                        sitemap_xml = (
                                            config_gen.generate_sitemap_from_articles(
                                                base_url=sitemap_base_url,
                                                articles=articles,
                                                lastmod=None,
                                                changefreq="weekly",
                                                priority=0.8,
                                            )
                                        )
                                        st.session_state.generated_sitemap_xml = (
                                            sitemap_xml
                                        )
                                        st.success(
                                            f"✅ sitemap.xml 生成成功！包含 {len(articles)} 个 URL"
                                        )
                                except Exception as e:
                                    st.error(f"获取历史文章失败：{e}")

                        except Exception as e:
                            st.error(f"sitemap.xml 生成失败：{e}")

                # 显示生成的 sitemap.xml
                if st.session_state.generated_sitemap_xml:
                    st.markdown("##### 📄 sitemap.xml 内容")
                    st.code(st.session_state.generated_sitemap_xml, language="xml")

                    st.download_button(
                        "下载 sitemap.xml",
                        st.session_state.generated_sitemap_xml,
                        "sitemap.xml",
                        mime="application/xml",
                        use_container_width=True,
                        key="sitemap_dl",
                    )

                    st.info(
                        "💡 **使用说明**：将 sitemap.xml 文件上传到您网站的根目录（如 https://example.com/sitemap.xml），并在 Google Search Console 中提交"
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

    # 负面防护监控开关
    st.markdown("#### 🛡️ 负面防护监控")
    st.caption("自动生成负面查询，监控品牌在负面查询中的提及情况，生成澄清模板")
    
    with st.container(border=True):
        negative_monitor_enabled = st.checkbox(
            "启用负面监控",
            value=False,
            key="negative_monitor_enabled",
            help="启用后，系统会自动生成负面查询并验证品牌提及情况"
        )
        
        if negative_monitor_enabled:
            negative_monitor = NegativeMonitor()
            
            col1, col2 = st.columns([2, 1])
            with col1:
                negative_query_count = st.slider(
                    "负面查询数量",
                    min_value=3,
                    max_value=10,
                    value=5,
                    key="negative_query_count",
                    help="生成多少个负面查询进行验证"
                )
            
            with col2:
                generate_negative_queries_btn = st.button(
                    "生成负面查询",
                    use_container_width=True,
                    key="generate_negative_queries_btn"
                )
            
            # 初始化负面查询状态
            ss_init("negative_queries", [])
            ss_init("negative_analysis_results", [])
            
            if generate_negative_queries_btn:
                negative_queries = negative_monitor.generate_negative_queries(brand, negative_query_count)
                st.session_state.negative_queries = negative_queries
                st.success(f"✅ 已生成 {len(negative_queries)} 个负面查询")
            
            # 显示生成的负面查询
            if st.session_state.negative_queries:
                st.markdown("##### 📋 生成的负面查询")
                negative_queries_text = "\n".join(st.session_state.negative_queries)
                st.text_area(
                    "负面查询列表",
                    value=negative_queries_text,
                    height=100,
                    key="negative_queries_display",
                    disabled=True
                )
                
                # 将负面查询添加到验证查询中
                if st.button("添加到验证查询", key="add_negative_to_verify"):
                    current_queries = st.session_state.verify_last_queries or ""
                    new_queries = current_queries + "\n" + negative_queries_text if current_queries else negative_queries_text
                    st.session_state.verify_last_queries = new_queries
                    st.success("✅ 负面查询已添加到验证查询中")
                    st.rerun()
    
    st.markdown("---")
    
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
        
        # 获取负面监控开关状态
        negative_monitor_enabled = st.session_state.get("negative_monitor_enabled", False)

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
                            # 准备输入文本用于成本估算
                            input_text = verify_prompt.template.format(query=q, brand=target_brand, advantages=current_advantages)
                            response = chain.invoke({"query": q, "brand": target_brand, "advantages": current_advantages})
                            
                            # 记录成本
                            if v_llm:
                                try:
                                    # model_name 是 verify_llms 字典的 key，就是 provider 名称
                                    provider = model_name
                                    model_name_for_cost = getattr(v_llm, 'model_name', None) or getattr(v_llm, 'model', None) or model_defaults(provider)
                                    record_api_cost(
                                        operation_type="验证",
                                        provider=provider,
                                        model=model_name_for_cost,
                                        input_text=input_text,
                                        output_text=response,
                                        keyword=q,
                                        brand=target_brand
                                    )
                                except Exception:
                                    pass  # 静默失败，不影响主流程

                        resp_l = response.lower()
                        tb_l = target_brand.lower()
                        count = resp_l.count(tb_l)
                        first_pos = resp_l.find(tb_l)
                        rank = "前1/3（优先）" if first_pos != -1 and first_pos < len(response) // 3 else ("中后段" if first_pos != -1 else "未提及")

                        all_results.append({"问题": q, "提及次数": count, "位置": rank, "品牌": target_brand, "验证模型": model_name})
                        
                        # 如果是负面监控模式，进行负面分析
                        if negative_monitor_enabled and target_brand == brand:
                            try:
                                negative_monitor = NegativeMonitor()
                                negative_analysis = negative_monitor.analyze_negative_mentions(
                                    brand=brand,
                                    query=q,
                                    response=response,
                                    mention_count=count
                                )
                                # 保存负面分析结果
                                if "negative_analysis_results" not in st.session_state:
                                    st.session_state.negative_analysis_results = []
                                st.session_state.negative_analysis_results.append(negative_analysis)
                            except Exception as e:
                                pass  # 静默失败，不影响主流程

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
        
        # 负面监控分析结果
        if negative_monitor_enabled and st.session_state.negative_analysis_results:
            st.markdown("---")
            st.markdown("#### 🛡️ 负面监控分析结果")
            
            negative_results = st.session_state.negative_analysis_results
            negative_df = pd.DataFrame(negative_results)
            
            # 风险等级统计
            risk_col1, risk_col2, risk_col3 = st.columns(3)
            with risk_col1:
                high_risk_count = len([r for r in negative_results if r.get("risk_level") == "高"])
                st.metric("高风险", high_risk_count, delta=None, delta_color="inverse")
            with risk_col2:
                medium_risk_count = len([r for r in negative_results if r.get("risk_level") == "中"])
                st.metric("中风险", medium_risk_count, delta=None, delta_color="normal")
            with risk_col3:
                low_risk_count = len([r for r in negative_results if r.get("risk_level") == "低"])
                st.metric("低风险", low_risk_count, delta=None, delta_color="normal")
            
            # 显示详细分析结果
            st.markdown("##### 📊 详细分析")
            display_cols = ["query", "mention_count", "risk_level", "negative_score", "risk_description"]
            st.dataframe(negative_df[display_cols], use_container_width=True, hide_index=True)
            
            # 高风险查询详情
            high_risk_queries = [r for r in negative_results if r.get("risk_level") == "高"]
            if high_risk_queries:
                st.markdown("##### ⚠️ 高风险查询详情")
                for result in high_risk_queries:
                    with st.expander(f"🔴 {result.get('query')} - 高风险", expanded=False):
                        st.markdown(f"**查询**：{result.get('query')}")
                        st.markdown(f"**提及次数**：{result.get('mention_count')}")
                        st.markdown(f"**负面得分**：{result.get('negative_score')}")
                        st.markdown(f"**风险说明**：{result.get('risk_description')}")
                        if result.get('negative_keywords'):
                            st.markdown(f"**负面关键词**：{', '.join(result.get('negative_keywords'))}")
                        
                        # 生成澄清模板
                        if st.button(f"生成澄清模板", key=f"clarify_{result.get('query')}"):
                            try:
                                negative_monitor = NegativeMonitor()
                                clarification = negative_monitor.generate_clarification_template(
                                    brand=brand,
                                    negative_query=result.get('query'),
                                    advantages=advantages
                                )
                                st.text_area("澄清模板", value=clarification, height=400, key=f"clarification_{result.get('query')}")
                                
                                st.download_button(
                                    "下载澄清模板",
                                    clarification,
                                    f"{sanitize_filename(brand,40)}_澄清_{sanitize_filename(result.get('query'),20)}.md",
                                    mime="text/markdown",
                                    use_container_width=True,
                                    key=f"dl_clarify_{result.get('query')}"
                                )
                            except Exception as e:
                                st.error(f"生成澄清模板失败：{e}")
            
            # 下载负面分析报告
            negative_csv = negative_df.to_csv(index=False, encoding="utf-8-sig")
            st.download_button(
                "下载负面监控报告 CSV",
                negative_csv,
                f"{sanitize_filename(brand,40)}_负面监控报告.csv",
                mime="text/csv",
                use_container_width=True,
                key="negative_dl_csv"
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
                        # 准备输入文本用于成本估算
                        input_text = verify_prompt.template.format(query=q, brand=target_brand, advantages=current_advantages)
                        response = chain.invoke({"query": q, "brand": target_brand, "advantages": current_advantages})
                        
                        # 记录成本
                        if v_llm:
                            try:
                                # model_name 是 verify_llms 字典的 key，就是 provider 名称
                                provider = model_name
                                model_name_for_cost = getattr(v_llm, 'model_name', None) or getattr(v_llm, 'model', None) or model_defaults(provider)
                                record_api_cost(
                                    operation_type="验证",
                                    provider=provider,
                                    model=model_name_for_cost,
                                    input_text=input_text,
                                    output_text=response,
                                    keyword=q,
                                    brand=target_brand
                                )
                            except Exception:
                                pass  # 静默失败，不影响主流程
                        
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
        
        # 话题集群分析模块
        st.markdown("---")
        st.markdown("#### 🎯 话题集群分析")
        st.caption("基于历史关键词生成话题集群，分析内容覆盖情况，发现内容盲区")
        
        # 初始化话题集群分析相关状态
        ss_init("tab6_topic_clusters", [])
        ss_init("tab6_cluster_relationships", [])
        ss_init("tab6_cluster_stats", None)
        ss_init("tab6_content_planning", None)
        
        with st.container(border=True):
            tab6_cluster_col1, tab6_cluster_col2 = st.columns([2, 1])
            
            with tab6_cluster_col1:
                tab6_cluster_count = st.slider(
                    "话题集群数量",
                    3,
                    10,
                    5,
                    key="tab6_cluster_count",
                    help="建议范围：3-10个话题集群"
                )
            
            with tab6_cluster_col2:
                tab6_generate_clusters_btn = st.button(
                    "🚀 生成话题集群分析",
                    use_container_width=True,
                    disabled=(not st.session_state.cfg_valid) or (gen_llm is None) or (len(historical_keywords) == 0),
                    key="tab6_generate_clusters_btn"
                )
        
        # 执行话题聚类分析
        if tab6_generate_clusters_btn and gen_llm and historical_keywords:
            topic_cluster = TopicCluster()
            with st.spinner(f"正在分析话题集群（目标：{tab6_cluster_count} 个）..."):
                try:
                    cluster_chain = PromptTemplate.from_template("{input}") | gen_llm | StrOutputParser()
                    cluster_result = topic_cluster.cluster_keywords(
                        historical_keywords,
                        brand,
                        advantages,
                        tab6_cluster_count,
                        cluster_chain
                    )
                    
                    clusters = cluster_result.get("clusters", [])
                    relationships = cluster_result.get("relationships", [])
                    cluster_stats = cluster_result.get("cluster_stats", {})
                    
                    st.session_state.tab6_topic_clusters = clusters
                    st.session_state.tab6_cluster_relationships = relationships
                    st.session_state.tab6_cluster_stats = cluster_stats
                    
                    if clusters:
                        st.success(f"✅ 话题集群分析完成！共生成 {len(clusters)} 个话题集群")
                        
                        # 分析覆盖情况
                        coverage = topic_cluster.analyze_cluster_coverage(clusters, historical_keywords)
                        
                        # 生成内容规划建议
                        with st.spinner("正在生成内容规划建议..."):
                            try:
                                planning_result = topic_cluster.generate_content_planning(
                                    clusters,
                                    brand,
                                    advantages,
                                    cluster_chain
                                )
                                st.session_state.tab6_content_planning = planning_result
                            except Exception as e:
                                st.warning(f"内容规划生成失败：{e}")
                    else:
                        st.warning("⚠️ 未生成话题集群，请检查输入或重试")
                except Exception as e:
                    st.error(f"话题集群分析失败：{e}")
        
        # 显示话题集群分析结果
        if st.session_state.tab6_topic_clusters:
            clusters = st.session_state.tab6_topic_clusters
            relationships = st.session_state.tab6_cluster_relationships
            cluster_stats = st.session_state.tab6_cluster_stats
            
            # 显示统计信息
            if cluster_stats:
                st.markdown("##### 📊 话题集群统计")
                col1, col2, col3, col4 = st.columns(4)
                with col1:
                    st.metric("话题总数", cluster_stats.get("total_clusters", 0))
                with col2:
                    st.metric("关键词总数", cluster_stats.get("total_keywords", 0))
                with col3:
                    st.metric("平均关键词/话题", f"{cluster_stats.get('avg_keywords_per_cluster', 0):.1f}")
                with col4:
                    st.metric("最大话题关键词数", cluster_stats.get("max_keywords", 0))
            
            # 话题分布可视化
            if clusters:
                st.markdown("##### 📈 话题分布图")
                cluster_names = [c.get("name", "N/A") for c in clusters]
                cluster_counts = [c.get("keyword_count", 0) for c in clusters]
                
                cluster_dist_df = pd.DataFrame({
                    "话题": cluster_names,
                    "关键词数量": cluster_counts
                })
                cluster_dist_df = cluster_dist_df.sort_values("关键词数量", ascending=False)
                
                fig_cluster_dist = px.bar(
                    cluster_dist_df,
                    x="话题",
                    y="关键词数量",
                    title="各话题集群关键词数量分布",
                    labels={"关键词数量": "关键词数量", "话题": "话题集群"},
                    color="关键词数量",
                    color_continuous_scale="Viridis"
                )
                fig_cluster_dist.update_xaxes(tickangle=-45)
                st.plotly_chart(fig_cluster_dist, use_container_width=True)
            
            # 显示话题集群列表
            st.markdown("##### 📋 话题集群详情")
            for cluster in clusters:
                with st.expander(f"**{cluster.get('name', 'N/A')}** - {cluster.get('keyword_count', 0)} 个关键词 | 优先级：{cluster.get('priority', '中')}", expanded=False):
                    st.markdown(f"**描述**：{cluster.get('description', '无描述')}")
                    keywords_list = cluster.get('keywords', [])
                    if keywords_list:
                        st.markdown(f"**关键词**：{', '.join(keywords_list[:15])}{' ...' if len(keywords_list) > 15 else ''}")
                        st.caption(f"共 {len(keywords_list)} 个关键词")
            
            # 显示话题关联关系
            if relationships:
                st.markdown("##### 🔗 话题关联关系")
                rel_df = pd.DataFrame(relationships)
                st.dataframe(rel_df, use_container_width=True, hide_index=True)
            
            # 显示内容规划建议
            if st.session_state.tab6_content_planning:
                planning = st.session_state.tab6_content_planning
                st.markdown("##### 💡 内容规划建议")
                
                # 内容盲区分析
                content_gaps = planning.get("content_gaps", [])
                if content_gaps:
                    st.markdown("**📌 内容盲区分析**")
                    gaps_df = pd.DataFrame(content_gaps)
                    st.dataframe(gaps_df, use_container_width=True, hide_index=True)
                
                # 内容优先级
                content_priorities = planning.get("content_priorities", [])
                if content_priorities:
                    st.markdown("**🎯 内容优先级**")
                    priority_df = pd.DataFrame(content_priorities)
                    priority_df = priority_df.sort_values("priority", key=lambda x: x.map({"高": 3, "中": 2, "低": 1}), ascending=False)
                    st.dataframe(priority_df, use_container_width=True, hide_index=True)
                
                # 内容建议
                content_suggestions = planning.get("content_suggestions", [])
                if content_suggestions:
                    with st.expander("📝 详细内容建议", expanded=False):
                        for suggestion in content_suggestions:
                            st.markdown(f"**{suggestion.get('cluster_name', 'N/A')}**")
                            st.markdown(f"- **内容类型**：{', '.join(suggestion.get('content_types', []))}")
                            st.markdown(f"- **发布平台**：{', '.join(suggestion.get('platforms', []))}")
                            st.markdown(f"- **关键词策略**：{suggestion.get('keyword_strategy', 'N/A')}")
                            ideas = suggestion.get('content_ideas', [])
                            if ideas:
                                st.markdown(f"- **内容创意**：{', '.join(ideas[:3])}")
                            st.markdown("---")
        
        # ROI 分析与成本优化模块
        st.markdown("---")
        st.markdown("#### 💰 ROI 分析与成本优化")
        st.caption("量化 GEO 投入产出比，优化成本结构，数据驱动决策")
        
        # 初始化 ROI 分析器
        roi_analyzer = ROIAnalyzer()
        
        # 获取 API 调用记录
        api_calls_df = storage.get_api_calls(brand=brand)
        
        if api_calls_df.empty:
            st.info("📊 暂无 API 调用记录。开始使用工具后，成本数据将自动记录。")
        else:
            # 成本分析
            cost_analysis = roi_analyzer.analyze_costs(api_calls_df, verify_df)
            
            # 成本概览
            st.markdown("##### 📊 成本概览")
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("总成本(CNY)", f"¥{cost_analysis['total_cost_cny']:.2f}")
            with col2:
                st.metric("总成本(USD)", f"${cost_analysis['total_cost_usd']:.2f}")
            with col3:
                st.metric("总Token数", f"{cost_analysis['total_tokens']:,}")
            with col4:
                st.metric("API调用次数", cost_analysis['total_calls'])
            
            # 成本趋势图
            if cost_analysis.get('daily_costs'):
                st.markdown("##### 📈 成本趋势")
                daily_df = pd.DataFrame(cost_analysis['daily_costs'])
                daily_df['date'] = pd.to_datetime(daily_df['date'])
                
                fig_cost_trend = px.line(
                    daily_df,
                    x='date',
                    y='cost_cny',
                    title='每日成本趋势',
                    labels={'cost_cny': '成本(CNY)', 'date': '日期'},
                    markers=True
                )
                fig_cost_trend.update_layout(hovermode='x unified')
                st.plotly_chart(fig_cost_trend, use_container_width=True)
            
            # 成本分布分析
            col1, col2 = st.columns(2)
            
            with col1:
                st.markdown("##### 💼 按提供商统计")
                cost_by_provider = cost_analysis.get('cost_by_provider', {})
                if cost_by_provider:
                    provider_df = pd.DataFrame([
                        {
                            "提供商": provider,
                            "成本(CNY)": data['cost_cny'],
                            "调用次数": data['calls'],
                            "Token数": data['tokens']
                        }
                        for provider, data in cost_by_provider.items()
                    ])
                    provider_df = provider_df.sort_values("成本(CNY)", ascending=False)
                    
                    fig_provider = px.pie(
                        provider_df,
                        values="成本(CNY)",
                        names="提供商",
                        title="成本分布（按提供商）"
                    )
                    st.plotly_chart(fig_provider, use_container_width=True)
                else:
                    st.info("暂无提供商数据")
            
            with col2:
                st.markdown("##### 🔧 按操作类型统计")
                cost_by_operation = cost_analysis.get('cost_by_operation', {})
                if cost_by_operation:
                    operation_df = pd.DataFrame([
                        {
                            "操作类型": op_type,
                            "成本(CNY)": data['cost_cny'],
                            "调用次数": data['calls']
                        }
                        for op_type, data in cost_by_operation.items()
                    ])
                    operation_df = operation_df.sort_values("成本(CNY)", ascending=False)
                    
                    fig_operation = px.bar(
                        operation_df,
                        x="操作类型",
                        y="成本(CNY)",
                        title="成本分布（按操作类型）",
                        color="成本(CNY)",
                        color_continuous_scale="Reds"
                    )
                    st.plotly_chart(fig_operation, use_container_width=True)
                else:
                    st.info("暂无操作类型数据")
            
            # ROI 分析
            roi_analysis = cost_analysis.get('roi_analysis', {})
            if roi_analysis and roi_analysis.get('total_cost', 0) > 0:
                st.markdown("##### 📈 ROI 分析")
                roi_col1, roi_col2, roi_col3, roi_col4 = st.columns(4)
                with roi_col1:
                    st.metric("总投入成本", f"¥{roi_analysis.get('total_cost', 0):.2f}")
                with roi_col2:
                    st.metric("总提及次数", roi_analysis.get('total_mentions', 0))
                with roi_col3:
                    st.metric("估算价值", f"¥{roi_analysis.get('estimated_value', 0):.2f}")
                with roi_col4:
                    roi_ratio = roi_analysis.get('roi_ratio', 0)
                    st.metric("ROI", f"{roi_ratio:.1f}%", delta=f"¥{roi_analysis.get('roi_value', 0):.2f}")
                
                # 关键词 ROI 排名
                keyword_roi = roi_analysis.get('keyword_roi', {})
                if keyword_roi:
                    st.markdown("##### 🎯 关键词 ROI 排名")
                    keyword_roi_df = pd.DataFrame([
                        {
                            "关键词": kw,
                            "成本(CNY)": data['cost'],
                            "提及次数": data['mentions'],
                            "估算价值(CNY)": data['value'],
                            "ROI(%)": data['roi']
                        }
                        for kw, data in keyword_roi.items()
                    ])
                    keyword_roi_df = keyword_roi_df.sort_values("ROI(%)", ascending=False)
                    
                    # 显示 Top 10
                    top_roi = keyword_roi_df.head(10)
                    st.dataframe(top_roi, use_container_width=True, hide_index=True)
                    
                    with st.expander("查看完整关键词 ROI 排名", expanded=False):
                        st.dataframe(keyword_roi_df, use_container_width=True, hide_index=True)
            
            # 成本优化建议
            st.markdown("##### 💡 成本优化建议")
            suggestions = roi_analyzer.get_optimization_suggestions(cost_analysis)
            
            for suggestion in suggestions:
                priority_color = {
                    "高": "🔴",
                    "中": "🟡",
                    "低": "🟢"
                }.get(suggestion.get('priority', '低'), '⚪')
                
                with st.container(border=True):
                    st.markdown(f"**{priority_color} {suggestion.get('title', 'N/A')}**")
                    st.markdown(suggestion.get('description', ''))
                    
                    if 'savings_estimate' in suggestion:
                        st.info(f"💵 预计可节省：¥{suggestion['savings_estimate']:.2f}")
                    
                    if 'keywords' in suggestion:
                        st.markdown(f"**相关关键词**：{', '.join(suggestion['keywords'])}")
            
            # 未来成本预测
            st.markdown("##### 🔮 未来成本预测")
            future_cost = roi_analyzer.estimate_future_cost(api_calls_df, days=30)
            
            pred_col1, pred_col2, pred_col3 = st.columns(3)
            with pred_col1:
                st.metric("预计日均成本", f"¥{future_cost.get('estimated_daily_cost_cny', 0):.2f}")
            with pred_col2:
                st.metric("预计30天总成本", f"¥{future_cost.get('estimated_total_cost_cny', 0):.2f}")
            with pred_col3:
                confidence = future_cost.get('confidence', '低')
                confidence_icon = {"高": "🟢", "中": "🟡", "低": "🔴"}.get(confidence, "⚪")
                st.metric("预测置信度", f"{confidence_icon} {confidence}")
            
            if future_cost.get('data_points', 0) < 3:
                st.warning("⚠️ 数据点较少，预测准确性较低。建议积累更多数据后再查看预测。")
            
            # 导出成本数据
            st.markdown("##### 📥 导出数据")
            export_col1, export_col2 = st.columns(2)
            with export_col1:
                if not api_calls_df.empty:
                    api_calls_csv = api_calls_df.to_csv(index=False, encoding="utf-8-sig")
                    st.download_button(
                        "下载 API 调用记录 CSV",
                        api_calls_csv,
                        f"{sanitize_filename(brand,40)}_api_calls.csv",
                        "text/csv",
                        use_container_width=True,
                        key="export_api_calls"
                    )
            with export_col2:
                # 生成成本报告
                cost_report = f"""
# GEO 成本分析报告

## 成本概览
- 总成本(CNY): ¥{cost_analysis['total_cost_cny']:.2f}
- 总成本(USD): ${cost_analysis['total_cost_usd']:.2f}
- 总Token数: {cost_analysis['total_tokens']:,}
- API调用次数: {cost_analysis['total_calls']}

## ROI 分析
"""
                if roi_analysis:
                    cost_report += f"""
- 总投入成本: ¥{roi_analysis.get('total_cost', 0):.2f}
- 总提及次数: {roi_analysis.get('total_mentions', 0)}
- 估算价值: ¥{roi_analysis.get('estimated_value', 0):.2f}
- ROI: {roi_analysis.get('roi_ratio', 0):.1f}%
"""
                cost_report += f"""
## 优化建议
"""
                for suggestion in suggestions:
                    cost_report += f"""
- [{suggestion.get('priority', '低')}] {suggestion.get('title', 'N/A')}
  {suggestion.get('description', '')}
"""
                
                st.download_button(
                    "下载成本分析报告",
                    cost_report,
                    f"{sanitize_filename(brand,40)}_cost_report.md",
                    "text/markdown",
                    use_container_width=True,
                    key="export_cost_report"
                )
        
        # 3. 内容质量指标分析
        st.markdown("---")
        st.markdown("#### 📈 内容质量指标分析")
        st.caption("分析内容的信任度、权威性、参与度等关键指标，量化内容质量")
        
        # 初始化指标分析器
        metrics_analyzer = ContentMetricsAnalyzer()
        
        # 获取历史文章
        try:
            articles = storage.get_articles(brand=brand)
            
            if articles and len(articles) > 0:
                # 分析所有文章
                with st.spinner("正在分析内容质量指标..."):
                    metrics_results = metrics_analyzer.analyze_batch(articles, brand)
                    summary = metrics_analyzer.get_metrics_summary(metrics_results)
                
                # 显示指标概览
                st.markdown("##### 📊 指标概览")
                metric_col1, metric_col2, metric_col3, metric_col4 = st.columns(4)
                
                with metric_col1:
                    st.metric(
                        "平均 Trust Density",
                        f"{summary['avg_trust_density']:.2f}",
                        help="每100字信任信号数（来源占位、数据、案例等）"
                    )
                
                with metric_col2:
                    st.metric(
                        "平均 Citation Share",
                        f"{summary['avg_citation_share']:.2f}%",
                        help="品牌引用比例（品牌提及次数 / 总提及次数）"
                    )
                
                with metric_col3:
                    st.metric(
                        "平均 Authority Score",
                        f"{summary['avg_authority_score']:.2f}",
                        help="权威性得分（基于来源占位数量，0-100）"
                    )
                
                with metric_col4:
                    st.metric(
                        "平均 Engagement Potential",
                        f"{summary['avg_engagement_potential']:.2f}",
                        help="参与度潜力（基于结构化程度，0-100）"
                    )
                
                # 详细指标分析
                st.markdown("##### 📋 详细指标分析")
                
                # 创建指标数据框
                metrics_df = pd.DataFrame([
                    {
                        "关键词": r.get('keyword', ''),
                        "平台": r.get('platform', ''),
                        "Trust Density": r.get('trust_density', 0),
                        "Citation Share (%)": r.get('citation_share', 0),
                        "Authority Score": r.get('authority_score', 0),
                        "Engagement Potential": r.get('engagement_potential', 0),
                        "信任信号数": r.get('trust_signals', 0),
                        "来源占位": r.get('citations', 0),
                        "品牌提及": r.get('brand_mentions', 0),
                    }
                    for r in metrics_results
                ])
                
                if not metrics_df.empty:
                    # 显示指标表格
                    st.dataframe(metrics_df, use_container_width=True, hide_index=True)
                    
                    # 指标可视化
                    viz_col1, viz_col2 = st.columns(2)
                    
                    with viz_col1:
                        # Trust Density 分布
                        fig_trust = px.histogram(
                            metrics_df,
                            x="Trust Density",
                            nbins=20,
                            title="Trust Density 分布",
                            labels={"Trust Density": "Trust Density", "count": "文章数量"},
                            color_discrete_sequence=["#2563EB"]
                        )
                        st.plotly_chart(fig_trust, use_container_width=True)
                    
                    with viz_col2:
                        # Authority Score 分布
                        fig_authority = px.histogram(
                            metrics_df,
                            x="Authority Score",
                            nbins=20,
                            title="Authority Score 分布",
                            labels={"Authority Score": "Authority Score", "count": "文章数量"},
                            color_discrete_sequence=["#10B981"]
                        )
                        st.plotly_chart(fig_authority, use_container_width=True)
                    
                    # 指标热力图（按平台）
                    if len(metrics_df['平台'].unique()) > 1:
                        st.markdown("##### 🔥 平台指标热力图")
                        platform_metrics = metrics_df.groupby('平台').agg({
                            'Trust Density': 'mean',
                            'Citation Share (%)': 'mean',
                            'Authority Score': 'mean',
                            'Engagement Potential': 'mean',
                        }).round(2)
                        
                        fig_heatmap = px.imshow(
                            platform_metrics.T,
                            labels=dict(x="平台", y="指标", color="得分"),
                            title="各平台平均指标热力图",
                            color_continuous_scale="RdYlGn",
                            aspect="auto"
                        )
                        st.plotly_chart(fig_heatmap, use_container_width=True)
                    
                    # 指标相关性分析
                    st.markdown("##### 🔗 指标相关性分析")
                    correlation_cols = ['Trust Density', 'Citation Share (%)', 'Authority Score', 'Engagement Potential']
                    corr_df = metrics_df[correlation_cols].corr()
                    
                    fig_corr = px.imshow(
                        corr_df,
                        labels=dict(x="指标", y="指标", color="相关系数"),
                        title="指标相关性矩阵",
                        color_continuous_scale="RdBu",
                        aspect="auto",
                        text_auto=True
                    )
                    st.plotly_chart(fig_corr, use_container_width=True)
                    
                    # Top 内容排名
                    st.markdown("##### 🏆 Top 内容排名")
                    top_col1, top_col2, top_col3, top_col4 = st.columns(4)
                    
                    with top_col1:
                        top_trust = metrics_df.nlargest(5, 'Trust Density')[['关键词', '平台', 'Trust Density']]
                        st.markdown("**Top 5 Trust Density**")
                        st.dataframe(top_trust, use_container_width=True, hide_index=True)
                    
                    with top_col2:
                        top_citation = metrics_df.nlargest(5, 'Citation Share (%)')[['关键词', '平台', 'Citation Share (%)']]
                        st.markdown("**Top 5 Citation Share**")
                        st.dataframe(top_citation, use_container_width=True, hide_index=True)
                    
                    with top_col3:
                        top_authority = metrics_df.nlargest(5, 'Authority Score')[['关键词', '平台', 'Authority Score']]
                        st.markdown("**Top 5 Authority Score**")
                        st.dataframe(top_authority, use_container_width=True, hide_index=True)
                    
                    with top_col4:
                        top_engagement = metrics_df.nlargest(5, 'Engagement Potential')[['关键词', '平台', 'Engagement Potential']]
                        st.markdown("**Top 5 Engagement Potential**")
                        st.dataframe(top_engagement, use_container_width=True, hide_index=True)
                    
                    # 导出指标数据
                    st.markdown("##### 📥 导出指标数据")
                    metrics_csv = metrics_df.to_csv(index=False, encoding="utf-8-sig")
                    st.download_button(
                        "下载指标数据 CSV",
                        metrics_csv,
                        f"{sanitize_filename(brand,40)}_内容质量指标_{pd.Timestamp.now().strftime('%Y%m%d_%H%M%S')}.csv",
                        mime="text/csv",
                        use_container_width=True,
                        key="export_metrics_csv"
                    )
                else:
                    st.info("暂无指标数据。")
            else:
                st.info("💡 提示：请先在【2 自动创作】生成内容，然后才能查看内容质量指标。")
        except Exception as e:
            st.error(f"获取内容质量指标失败：{e}")
        
        # 4. 关键词效果排名
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
        
        # 5. 负面防护监控报告
        st.markdown("---")
        st.markdown("#### 🛡️ 负面防护监控报告")
        st.caption("分析负面查询中的品牌提及情况，提供风险预警和优化建议")
        
        # 获取负面分析结果（从 session_state 或数据库）
        try:
            # 尝试从 session_state 获取
            negative_results = st.session_state.get("negative_analysis_results", [])
            
            # 如果没有，尝试从验证结果中提取负面查询
            if not negative_results and st.session_state.verify_combined is not None:
                verify_df = st.session_state.verify_combined
                # 检查是否有负面查询
                negative_monitor = NegativeMonitor()
                negative_queries_pattern = "|".join([q.replace(brand, "{brand}") for q in negative_monitor.generate_negative_queries(brand, 15)])
                
                # 筛选可能的负面查询
                brand_verify = verify_df[verify_df["品牌"] == brand].copy()
                if len(brand_verify) > 0:
                    # 检查问题是否包含负面关键词
                    negative_keywords = negative_monitor.negative_keywords
                    negative_verify = brand_verify[
                        brand_verify["问题"].str.contains("|".join(negative_keywords), case=False, na=False)
                    ]
                    
                    if len(negative_verify) > 0:
                        # 重新分析负面查询
                        negative_results = []
                        for _, row in negative_verify.iterrows():
                            # 这里需要重新获取响应内容，但为了简化，我们使用现有数据
                            # 实际应用中，应该从数据库获取完整的响应内容
                            try:
                                analysis = negative_monitor.analyze_negative_mentions(
                                    brand=brand,
                                    query=row["问题"],
                                    response="",  # 如果没有保存响应，使用空字符串
                                    mention_count=row["提及次数"]
                                )
                                negative_results.append(analysis)
                            except:
                                pass
            
            if negative_results:
                negative_monitor = NegativeMonitor()
                report = negative_monitor.generate_negative_report(
                    brand=brand,
                    analysis_results=negative_results,
                    threshold=0.3
                )
                
                # 显示报告概览
                st.markdown("##### 📊 报告概览")
                report_col1, report_col2, report_col3, report_col4 = st.columns(4)
                
                with report_col1:
                    st.metric("总查询数", report.get("total_queries", 0))
                
                with report_col2:
                    st.metric("高风险", report.get("high_risk_count", 0), delta=None, delta_color="inverse")
                
                with report_col3:
                    st.metric("平均提及次数", report.get("average_mention_count", 0.0))
                
                with report_col4:
                    st.metric("平均负面得分", report.get("average_negative_score", 0.0))
                
                # 预警信息
                alerts = report.get("alerts", [])
                if alerts:
                    st.markdown("##### ⚠️ 预警信息")
                    for alert in alerts:
                        alert_level = alert.get("level", "中")
                        alert_color = {"高": "🔴", "中": "🟡", "低": "🟢"}.get(alert_level, "⚪")
                        st.warning(f"{alert_color} {alert.get('message', '')}")
                
                # 优化建议
                recommendations = report.get("recommendations", [])
                if recommendations:
                    st.markdown("##### 💡 优化建议")
                    for i, rec in enumerate(recommendations, 1):
                        st.markdown(f"{i}. {rec}")
                
                # 高风险查询列表
                high_risk_queries = report.get("high_risk_queries", [])
                if high_risk_queries:
                    st.markdown("##### 🔴 高风险查询列表")
                    st.write(", ".join(high_risk_queries))
                
                # 中风险查询列表
                medium_risk_queries = report.get("medium_risk_queries", [])
                if medium_risk_queries:
                    st.markdown("##### 🟡 中风险查询列表")
                    st.write(", ".join(medium_risk_queries))
                
                # 下载报告
                import json
                report_json = json.dumps(report, ensure_ascii=False, indent=2)
                st.download_button(
                    "下载负面监控报告 JSON",
                    report_json,
                    f"{sanitize_filename(brand,40)}_负面监控报告_{pd.Timestamp.now().strftime('%Y%m%d_%H%M%S')}.json",
                    mime="application/json",
                    use_container_width=True,
                    key="negative_report_dl"
                )
            else:
                st.info("💡 提示：暂无负面监控数据。请在【4 多模型验证】中启用负面监控功能，生成负面查询并验证。")
        except Exception as e:
            st.error(f"生成负面监控报告失败：{e}")
        
        # 6. 数据导出
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

# =======================
# Tab7：工作流自动化
# =======================
with tab7:
    st.markdown("### 🔄 智能工作流自动化")
    st.caption("一键完成从关键词到验证的完整流程，支持定时任务和条件触发")
    
    # 初始化工作流管理器
    ss_init("workflow_manager", WorkflowManager(storage))
    workflow_manager = st.session_state.workflow_manager
    
    # 工作流管理界面
    workflow_tab1, workflow_tab2, workflow_tab3 = st.tabs(["📋 工作流列表", "➕ 创建工作流", "📊 执行历史"])
    
    with workflow_tab1:
        st.markdown("#### 工作流列表")
        
        # 获取所有工作流
        workflows = workflow_manager.list_workflows()
        
        if workflows:
            for workflow in workflows:
                with st.container(border=True):
                    col1, col2, col3, col4 = st.columns([3, 1, 1, 1])
                    
                    with col1:
                        st.markdown(f"**{workflow['name']}**")
                        st.caption(f"创建时间: {workflow.get('created_at', 'N/A')[:10] if workflow.get('created_at') else 'N/A'}")
                        st.caption(f"步骤数: {len(workflow.get('steps', []))}")
                    
                    with col2:
                        enabled = workflow.get('enabled', True)
                        status_text = "✅ 启用" if enabled else "⏸️ 禁用"
                        if st.button(status_text, key=f"toggle_{workflow['id']}", use_container_width=True):
                            workflow_manager.update_workflow(workflow['id'], {"enabled": not enabled})
                            st.rerun()
                    
                    with col3:
                        if st.button("▶️ 执行", key=f"run_{workflow['id']}", use_container_width=True):
                            # 创建回调函数
                            def generate_keywords_callback(num_keywords, generation_mode, brand, advantages):
                                """关键词生成回调函数"""
                                if not gen_llm:
                                    raise ValueError("生成 LLM 未配置")
                                
                                if generation_mode == "AI生成":
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
                                    
                                    try:
                                        result = chain_json.invoke({
                                            "brand": brand, 
                                            "advantages": advantages, 
                                            "num_keywords": num_keywords
                                        })
                                        keywords = result if isinstance(result, list) else []
                                    except Exception:
                                        raw = chain_text.invoke({
                                            "brand": brand, 
                                            "advantages": advantages, 
                                            "num_keywords": num_keywords
                                        })
                                        keywords = extract_json_array(raw) or []
                                    
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
                                    
                                    return cleaned[:num_keywords]
                                else:
                                    # 托词工具和混合模式需要词库，暂时返回空列表
                                    return []
                            
                            def generate_content_callback(keyword, platform, brand, advantages):
                                """内容生成回调函数"""
                                if not gen_llm:
                                    raise ValueError("生成 LLM 未配置")
                                
                                # 获取平台模板（简化版，只支持主要平台）
                                platform_templates = {
                                    "知乎（专业问答）": """
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
""",
                                    "小红书（生活种草）": """
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
""",
                                }
                                
                                template = platform_templates.get(platform, platform_templates["知乎（专业问答）"])
                                prompt = PromptTemplate.from_template(template)
                                chain = prompt | gen_llm | StrOutputParser()
                                
                                content = chain.invoke({
                                    "keyword": keyword, 
                                    "brand": brand, 
                                    "advantages": advantages
                                })
                                
                                return content
                            
                            def verify_keywords_callback(keywords, verify_models, brand, advantages):
                                """验证回调函数"""
                                if not verify_llms:
                                    raise ValueError("验证 LLM 未配置")
                                
                                results = []
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
                                
                                for keyword in keywords:
                                    for model_name in verify_models:
                                        if model_name not in verify_llms:
                                            continue
                                        
                                        llm = verify_llms[model_name]
                                        chain = verify_prompt | llm | StrOutputParser()
                                        
                                        try:
                                            response = chain.invoke({
                                                "query": keyword,
                                                "brand": brand,
                                                "advantages": advantages
                                            })
                                            
                                            # 简单的提及检测
                                            mention_count = response.lower().count(brand.lower())
                                            mention_position = "开头" if brand.lower() in response.lower()[:100] else "中间" if mention_count > 0 else "未提及"
                                            
                                            results.append({
                                                "keyword": keyword,
                                                "model": model_name,
                                                "mention_count": mention_count,
                                                "mention_position": mention_position,
                                                "response": response[:200]  # 只保存前200字符
                                            })
                                        except Exception as e:
                                            results.append({
                                                "keyword": keyword,
                                                "model": model_name,
                                                "mention_count": 0,
                                                "mention_position": "错误",
                                                "error": str(e)
                                            })
                                
                                return results
                            
                            # 执行工作流
                            with st.spinner("执行工作流中..."):
                                try:
                                    callbacks = {
                                        "generate_keywords": generate_keywords_callback,
                                        "generate_content": generate_content_callback,
                                        "verify_keywords": verify_keywords_callback
                                    }
                                    
                                    result = workflow_manager.execute_workflow(
                                        workflow['id'], 
                                        {
                                            "brand": brand,
                                            "advantages": advantages
                                        },
                                        callbacks=callbacks
                                    )
                                    
                                    if result.get("status") == "success":
                                        st.success("工作流执行成功！")
                                        # 显示执行结果摘要
                                        if result.get("results"):
                                            with st.expander("查看执行结果", expanded=False):
                                                st.json(result.get("results", {}))
                                    else:
                                        st.error(f"工作流执行失败: {result.get('error', '未知错误')}")
                                except Exception as e:
                                    st.error(f"执行失败: {str(e)}")
                                    import traceback
                                    st.code(traceback.format_exc())
                    
                    with col4:
                        if st.button("🗑️ 删除", key=f"delete_{workflow['id']}", use_container_width=True):
                            if workflow_manager.delete_workflow(workflow['id']):
                                st.success("工作流已删除")
                                st.rerun()
                            else:
                                st.error("删除失败")
                    
                    # 显示工作流详情
                    with st.expander("查看详情", expanded=False):
                        st.json(workflow)
        else:
            st.info("暂无工作流，请在'创建工作流'标签页创建新工作流。")
    
    with workflow_tab2:
        st.markdown("#### 创建工作流")
        
        # 工作流模板选择
        st.markdown("##### 📚 从模板创建")
        templates = workflow_manager.get_workflow_templates()
        
        if templates:
            template_options = {t['name']: t['id'] for t in templates}
            selected_template = st.selectbox("选择模板", ["自定义"] + list(template_options.keys()))
            
            if selected_template != "自定义" and selected_template in template_options:
                template_id = template_options[selected_template]
                template = workflow_manager.storage.get_workflow_template(template_id)
                
                if template:
                    st.info(f"模板描述: {template.get('description', '无描述')}")
                    if st.button("使用此模板", key="use_template"):
                        workflow_name = st.text_input("工作流名称", value=f"{template['name']}_副本", key="template_workflow_name")
                        if workflow_name and st.button("创建", key="create_from_template"):
                            try:
                                workflow_id = workflow_manager.create_workflow_from_template(template_id, workflow_name)
                                st.success(f"工作流已创建: {workflow_id}")
                                st.rerun()
                            except Exception as e:
                                st.error(f"创建失败: {str(e)}")
        
        st.markdown("---")
        st.markdown("##### ✏️ 自定义工作流")
        
        workflow_name = st.text_input("工作流名称", key="new_workflow_name")
        
        # 工作流步骤配置
        st.markdown("**工作流步骤**")
        
        ss_init("workflow_steps", [])
        
        # 添加步骤
        col1, col2 = st.columns([3, 1])
        with col1:
            step_type = st.selectbox(
                "步骤类型",
                ["关键词生成", "内容创作", "内容优化", "验证", "条件检查"],
                key="new_step_type"
            )
        with col2:
            if st.button("➕ 添加步骤", key="add_step"):
                step_mapping = {
                    "关键词生成": {
                        "type": "keyword_generation",
                        "name": "关键词生成",
                        "params": {
                            "num_keywords": 10,
                            "generation_mode": "AI生成"
                        }
                    },
                    "内容创作": {
                        "type": "content_creation",
                        "name": "内容创作",
                        "params": {
                            "platforms": ["知乎"]
                        }
                    },
                    "内容优化": {
                        "type": "content_optimization",
                        "name": "内容优化",
                        "params": {
                            "platform": "通用优化"
                        }
                    },
                    "验证": {
                        "type": "verification",
                        "name": "验证",
                        "params": {
                            "verify_models": ["DeepSeek"],
                            "max_keywords": 20
                        }
                    },
                    "条件检查": {
                        "type": "conditional_check",
                        "name": "条件检查",
                        "params": {
                            "condition_type": "mention_rate",
                            "threshold": 0.5,
                            "action": "skip"
                        }
                    }
                }
                
                step = step_mapping.get(step_type)
                if step:
                    st.session_state.workflow_steps.append(step)
                    st.rerun()
        
        # 显示已添加的步骤
        if st.session_state.workflow_steps:
            st.markdown("**已添加的步骤**")
            for i, step in enumerate(st.session_state.workflow_steps):
                col1, col2 = st.columns([4, 1])
                with col1:
                    st.write(f"{i+1}. {step.get('name', '未命名步骤')}")
                with col2:
                    if st.button("删除", key=f"remove_step_{i}"):
                        st.session_state.workflow_steps.pop(i)
                        st.rerun()
        
        # 创建按钮
        if workflow_name and st.session_state.workflow_steps:
            if st.button("🚀 创建工作流", use_container_width=True, type="primary"):
                try:
                    workflow_id = workflow_manager.create_workflow(
                        name=workflow_name,
                        steps=st.session_state.workflow_steps
                    )
                    st.success(f"工作流创建成功！ID: {workflow_id}")
                    st.session_state.workflow_steps = []
                    st.rerun()
                except Exception as e:
                    st.error(f"创建失败: {str(e)}")
        elif not workflow_name:
            st.warning("请输入工作流名称")
        elif not st.session_state.workflow_steps:
            st.warning("请至少添加一个步骤")
    
    with workflow_tab3:
        st.markdown("#### 执行历史")
        
        # 获取执行记录
        executions = workflow_manager.storage.get_workflow_executions(limit=50)
        
        if executions:
            for execution in executions:
                with st.container(border=True):
                    workflow_id = execution.get("workflow_id")
                    workflow = workflow_manager.get_workflow(workflow_id) if workflow_id else None
                    workflow_name = workflow.get("name", workflow_id) if workflow else workflow_id
                    
                    col1, col2, col3 = st.columns([3, 1, 1])
                    
                    with col1:
                        st.markdown(f"**{workflow_name}**")
                        status = execution.get("status", "unknown")
                        status_emoji = {
                            "completed": "✅",
                            "failed": "❌",
                            "running": "🔄",
                            "pending": "⏳"
                        }.get(status, "❓")
                        st.caption(f"{status_emoji} {status} | 开始时间: {execution.get('started_at', 'N/A')[:19] if execution.get('started_at') else 'N/A'}")
                    
                    with col2:
                        if execution.get("error"):
                            st.error("有错误")
                        else:
                            st.success("正常")
                    
                    with col3:
                        if st.button("查看详情", key=f"view_exec_{execution.get('id')}"):
                            st.json(execution)
        else:
            st.info("暂无执行记录")

# =======================
# Tab8：GEO 资源库
# =======================
with tab8:
    st.markdown("### 📚 GEO 资源库")
    st.caption("发现 GEO 相关工具、代理、论文和社区资源，增强工具生态")
    
    resource_recommender = ResourceRecommender()
    
    # 资源统计概览
    summary = resource_recommender.get_resource_summary()
    stat_col1, stat_col2, stat_col3, stat_col4, stat_col5 = st.columns(5)
    with stat_col1:
        st.metric("总资源数", summary['total'])
    with stat_col2:
        st.metric("代理服务", summary['agents'])
    with stat_col3:
        st.metric("工具推荐", summary['tools'])
    with stat_col4:
        st.metric("论文/指南", summary['papers'])
    with stat_col5:
        st.metric("社区资源", summary['communities'])
    
    st.markdown("---")
    
    # 搜索功能
    search_col1, search_col2 = st.columns([3, 1])
    with search_col1:
        search_query = st.text_input(
            "🔍 搜索资源", 
            key="resource_search", 
            placeholder="输入关键词搜索代理、工具、论文、社区...",
            help="支持搜索资源名称、描述、功能特性等"
        )
    with search_col2:
        clear_search = st.button("清除搜索", use_container_width=True, key="clear_resource_search")
        if clear_search:
            st.session_state.resource_search = ""
            st.rerun()
    
    # 资源分类标签
    resource_tab1, resource_tab2, resource_tab3, resource_tab4 = st.tabs(["🤖 GEO 代理", "🛠️ 工具推荐", "📄 论文/指南", "👥 社区资源"])
    
    # GEO 代理
    with resource_tab1:
        st.markdown("#### 🤖 GEO 代理服务")
        st.caption("专业的 GEO 代理服务，提供高质量的内容生成和优化")
        
        if search_query:
            agents = resource_recommender.search_resources(search_query, "agents")
            if agents:
                st.info(f"🔍 找到 {len(agents)} 个匹配的代理服务")
        else:
            agents = resource_recommender.get_agents()
        
        if agents:
            for i, agent in enumerate(agents, 1):
                with st.container(border=True):
                    col1, col2 = st.columns([3, 1])
                    with col1:
                        st.markdown(f"##### {i}. {agent['name']} {agent.get('rating', '')}")
                    with col2:
                        if agent.get('url'):
                            st.markdown(f"[🔗 访问]({agent['url']})")
                    
                    st.markdown(f"**{agent['description']}**")
                    st.markdown(f"**分类**：{agent.get('category', 'N/A')}")
                    
                    if agent.get('features'):
                        st.markdown("**功能特性**：")
                        features_text = " | ".join([f"✓ {f}" for f in agent['features']])
                        st.markdown(features_text)
                    
                    if agent.get('url'):
                        st.markdown(f"**链接**：{agent['url']}")
        else:
            st.info("💡 暂无匹配的代理资源。尝试使用其他关键词搜索。")
    
    # 工具推荐
    with resource_tab2:
        st.markdown("#### 🛠️ 工具推荐")
        st.caption("GEO 相关的工具和服务，帮助优化内容效果")
        
        if search_query:
            tools = resource_recommender.search_resources(search_query, "tools")
            if tools:
                st.info(f"🔍 找到 {len(tools)} 个匹配的工具")
        else:
            tools = resource_recommender.get_tools()
        
        if tools:
            # 按分类分组显示
            categories = {}
            for tool in tools:
                cat = tool.get('category', '其他')
                if cat not in categories:
                    categories[cat] = []
                categories[cat].append(tool)
            
            for category, category_tools in categories.items():
                st.markdown(f"##### 📁 {category}")
                for i, tool in enumerate(category_tools, 1):
                    with st.container(border=True):
                        col1, col2 = st.columns([3, 1])
                        with col1:
                            st.markdown(f"**{tool['name']}** {tool.get('rating', '')}")
                        with col2:
                            if tool.get('url'):
                                st.markdown(f"[🔗 访问]({tool['url']})")
                        
                        st.markdown(f"*{tool['description']}*")
                        
                        if tool.get('features'):
                            st.markdown("**功能**：")
                            features_text = " | ".join([f"✓ {f}" for f in tool['features']])
                            st.markdown(features_text)
                        
                        if tool.get('url'):
                            st.markdown(f"**链接**：{tool['url']}")
        else:
            st.info("💡 暂无匹配的工具资源。尝试使用其他关键词搜索。")
    
    # 论文/指南
    with resource_tab3:
        st.markdown("#### 📄 论文/指南")
        st.caption("GEO 相关的论文、指南、文档，深入学习 GEO 策略")
        
        if search_query:
            papers = resource_recommender.search_resources(search_query, "papers")
            if papers:
                st.info(f"🔍 找到 {len(papers)} 个匹配的论文/指南")
        else:
            papers = resource_recommender.get_papers()
        
        if papers:
            # 按重要性排序
            importance_order = {"高": 3, "中": 2, "低": 1}
            papers_sorted = sorted(papers, key=lambda x: importance_order.get(x.get('importance', '低'), 1), reverse=True)
            
            # 按重要性分组显示
            high_importance = [p for p in papers_sorted if p.get('importance') == '高']
            medium_importance = [p for p in papers_sorted if p.get('importance') == '中']
            low_importance = [p for p in papers_sorted if p.get('importance') == '低']
            
            if high_importance:
                st.markdown("##### 🔥 高重要性（必读）")
                for paper in high_importance:
                    with st.container(border=True):
                        st.markdown(f"**🔥 {paper['title']}**")
                        st.markdown(f"*{paper['description']}*")
                        st.markdown(f"**分类**：{paper.get('category', 'N/A')} | **日期**：{paper.get('date', 'N/A')}")
                        if paper.get('url'):
                            st.markdown(f"🔗 [{paper['url']}]({paper['url']})")
            
            if medium_importance:
                st.markdown("##### ⭐ 中重要性（推荐阅读）")
                for paper in medium_importance:
                    with st.container(border=True):
                        st.markdown(f"**⭐ {paper['title']}**")
                        st.markdown(f"*{paper['description']}*")
                        st.markdown(f"**分类**：{paper.get('category', 'N/A')} | **日期**：{paper.get('date', 'N/A')}")
                        if paper.get('url'):
                            st.markdown(f"🔗 [{paper['url']}]({paper['url']})")
            
            if low_importance:
                st.markdown("##### 📌 低重要性（参考阅读）")
                for paper in low_importance:
                    with st.container(border=True):
                        st.markdown(f"**📌 {paper['title']}**")
                        st.markdown(f"*{paper['description']}*")
                        st.markdown(f"**分类**：{paper.get('category', 'N/A')} | **日期**：{paper.get('date', 'N/A')}")
                        if paper.get('url'):
                            st.markdown(f"🔗 [{paper['url']}]({paper['url']})")
        else:
            st.info("💡 暂无匹配的论文/指南资源。尝试使用其他关键词搜索。")
    
    # 社区资源
    with resource_tab4:
        st.markdown("#### 👥 社区资源")
        st.caption("GEO 相关的社区和论坛，与其他用户交流经验")
        
        if search_query:
            communities = resource_recommender.search_resources(search_query, "communities")
            if communities:
                st.info(f"🔍 找到 {len(communities)} 个匹配的社区")
        else:
            communities = resource_recommender.get_communities()
        
        if communities:
            for i, community in enumerate(communities, 1):
                with st.container(border=True):
                    col1, col2 = st.columns([3, 1])
                    with col1:
                        st.markdown(f"##### {i}. {community['name']} {community.get('rating', '')}")
                    with col2:
                        if community.get('url'):
                            st.markdown(f"[🔗 访问]({community['url']})")
                    
                    st.markdown(f"*{community['description']}*")
                    st.markdown(f"**分类**：{community.get('category', 'N/A')}")
                    
                    if community.get('url'):
                        st.markdown(f"**链接**：{community['url']}")
        else:
            st.info("💡 暂无匹配的社区资源。尝试使用其他关键词搜索。")
    
    # 搜索结果显示（跨分类）
    if search_query:
        all_results = resource_recommender.search_resources(search_query)
        if all_results:
            st.markdown("---")
            st.markdown("#### 🔍 搜索结果汇总")
            st.info(f"共找到 {len(all_results)} 个匹配资源（跨所有分类）")
            
            # 按类型分组显示
            results_by_type = {}
            for result in all_results:
                res_type = result.get('type', 'unknown')
                if res_type not in results_by_type:
                    results_by_type[res_type] = []
                results_by_type[res_type].append(result)
            
            type_names = {
                'agent': '🤖 代理服务',
                'tool': '🛠️ 工具',
                'paper': '📄 论文/指南',
                'community': '👥 社区'
            }
            
            for res_type, results in results_by_type.items():
                if results:
                    st.markdown(f"##### {type_names.get(res_type, res_type)} ({len(results)} 个)")
                    for result in results:
                        with st.container(border=True):
                            name_key = 'name' if 'name' in result else 'title'
                            st.markdown(f"**{result.get(name_key, 'N/A')}**")
                            st.caption(result.get('description', ''))
                            if result.get('url'):
                                st.markdown(f"🔗 [{result['url']}]({result['url']})")

# =======================
# Tab9：平台同步
# =======================
with tab9:
    st.markdown("### 📤 平台文章同步")
    st.caption("将生成的文章自动发布到各平台，支持API发布和一键复制")
    
    # 获取品牌信息
    brand = st.session_state.get("brand", "")
    if not brand:
        st.info("请先在侧边栏设置品牌信息")
    else:
        # 平台账号配置
        st.markdown("---")
        st.markdown("#### 🔐 平台账号配置")
        
        platform_config_tabs = st.tabs(["GitHub", "其他平台（开发中）"])
        
        with platform_config_tabs[0]:
            st.markdown("##### GitHub 配置")
            st.caption("配置GitHub账号信息，用于自动发布文章到GitHub仓库")
            
            # 检查是否已有配置
            existing_config = storage.get_platform_account("GitHub", brand)
            
            github_api_key = st.text_input(
                "GitHub Personal Access Token",
                value=existing_config.get('api_key', '') if existing_config else '',
                type="password",
                help="在 https://github.com/settings/tokens 创建Token，需要 repo 权限",
                key="github_api_key"
            )
            
            github_repo_owner = st.text_input(
                "仓库所有者（用户名）",
                value=existing_config.get('config', {}).get('repo_owner', '') if existing_config else '',
                help="GitHub用户名或组织名",
                key="github_repo_owner"
            )
            
            github_repo_name = st.text_input(
                "仓库名称",
                value=existing_config.get('config', {}).get('repo_name', '') if existing_config else '',
                help="要发布到的仓库名称",
                key="github_repo_name"
            )
            
            col1, col2 = st.columns([1, 4])
            with col1:
                if st.button("💾 保存配置", type="primary", use_container_width=True):
                    if github_api_key and github_repo_owner and github_repo_name:
                        try:
                            # 验证账号
                            from platform_sync.github_publisher import GitHubPublisher
                            publisher = GitHubPublisher(github_api_key, github_repo_owner, github_repo_name)
                            if publisher.validate_account():
                                storage.save_platform_account(
                                    platform="GitHub",
                                    account_config={
                                        'account_type': 'api',
                                        'api_key': github_api_key,
                                        'config': {
                                            'repo_owner': github_repo_owner,
                                            'repo_name': github_repo_name
                                        }
                                    },
                                    brand=brand
                                )
                                st.success("✅ GitHub配置已保存并验证成功！")
                            else:
                                st.error("❌ GitHub Token验证失败，请检查Token是否正确")
                        except Exception as e:
                            st.error(f"❌ 配置保存失败: {str(e)}")
                    else:
                        st.error("请填写完整信息")
            
            with col2:
                if existing_config:
                    st.info("✅ 已配置GitHub账号")
        
        # 发布功能
        st.markdown("---")
        st.markdown("#### 📝 发布文章")
        
        # 选择文章
        articles = storage.get_articles(brand=brand)
        if articles:
            # 文章选择
            article_options = {}
            for article in articles:
                display_name = f"{article.get('keyword', 'N/A')} - {article.get('platform', 'N/A')}"
                article_options[display_name] = article.get('id')
            
            if article_options:
                selected_article_key = st.selectbox(
                    "选择要发布的文章",
                    list(article_options.keys()),
                    key="publish_article_select"
                )
                selected_article_id = article_options[selected_article_key]
                
                # 选择平台
                # 定义平台列表
                api_platforms = ["GitHub"]
                copy_platforms = [
                    "头条号（资讯软文）", "小红书（生活种草）", "抖音图文（短内容）", "简书（文艺）",
                    "QQ空间（社交）", "新浪博客（博客）", "新浪新闻（资讯）", "搜狐号（资讯）",
                    "一点号（资讯）", "东方财富（财经）", "邦阅网（外贸）", "原创力文档（文档）"
                ]
                all_publish_platforms = api_platforms + copy_platforms
                
                publish_platform = st.selectbox(
                    "选择发布平台",
                    all_publish_platforms,
                    key="publish_platform_select"
                )
                
                if publish_platform == "GitHub":
                    # 检查配置
                    account_config = storage.get_platform_account("GitHub", brand)
                    if not account_config:
                        st.warning("⚠️ 请先配置GitHub账号")
                    else:
                        # 获取文章
                        article = next((a for a in articles if a.get('id') == selected_article_id), None)
                        if article:
                            # 显示文章预览
                            with st.expander("📄 文章预览", expanded=False):
                                st.markdown(f"**关键词**: {article.get('keyword', 'N/A')}")
                                st.markdown(f"**平台**: {article.get('platform', 'N/A')}")
                                st.markdown(f"**内容长度**: {len(article.get('content', ''))} 字符")
                                st.markdown("---")
                                st.text_area("内容", article.get('content', ''), height=200, disabled=True)
                            
                            # 发布选项
                            file_path = st.text_input(
                                "文件路径（可选）",
                                value=f"content/{article.get('keyword', 'article').replace(' ', '_')[:50]}.md",
                                help="GitHub仓库中的文件路径，留空使用默认路径",
                                key="github_file_path"
                            )
                            
                            if st.button("🚀 发布到GitHub", type="primary", use_container_width=True):
                                try:
                                    from platform_sync.github_publisher import GitHubPublisher
                                    publisher = GitHubPublisher(
                                        api_key=account_config['api_key'],
                                        repo_owner=account_config['config']['repo_owner'],
                                        repo_name=account_config['config']['repo_name']
                                    )
                                    
                                    with st.spinner("正在发布到GitHub..."):
                                        result = publisher.publish(
                                            content=article.get('content', ''),
                                            title=article.get('keyword', 'Untitled'),
                                            file_path=file_path if file_path else None
                                        )
                                    
                                    # 保存发布记录
                                    storage.save_publish_record(
                                        article_id=selected_article_id,
                                        platform="GitHub",
                                        publish_method="api",
                                        publish_status="success" if result['success'] else "failed",
                                        publish_url=result.get('publish_url', ''),
                                        publish_id=result.get('publish_id', ''),
                                        error_message=result.get('error', '')
                                    )
                                    
                                    # 显示结果
                                    if result['success']:
                                        st.success(f"✅ 发布成功！")
                                        st.markdown(f"**发布链接**: [{result['publish_url']}]({result['publish_url']})")
                                        st.balloons()
                                    else:
                                        st.error(f"❌ 发布失败: {result.get('error', '未知错误')}")
                                except Exception as e:
                                    st.error(f"❌ 发布过程出错: {str(e)}")
                                    storage.save_publish_record(
                                        article_id=selected_article_id,
                                        platform="GitHub",
                                        publish_method="api",
                                        publish_status="failed",
                                        error_message=str(e)
                                    )
                else:
                    # 一键复制平台
                    article = next((a for a in articles if a.get('id') == selected_article_id), None)
                    if article:
                        from platform_sync.copy_manager import CopyManager
                        copy_manager = CopyManager()
                        
                        # 格式化内容
                        formatted_content = copy_manager.format_for_platform(
                            platform=publish_platform,
                            content=article.get('content', ''),
                            title=article.get('keyword', 'Untitled'),
                            keyword=article.get('keyword', ''),
                            brand=brand
                        )
                        
                        # 显示格式化后的内容
                        with st.expander("📄 格式化后的内容（已复制到剪贴板）", expanded=True):
                            st.text_area(
                                "内容",
                                formatted_content,
                                height=300,
                                key="formatted_content_display"
                            )
                        
                        # 发布指南
                        guide = copy_manager.generate_publish_guide(publish_platform)
                        with st.expander("📋 发布指南", expanded=True):
                            st.markdown(guide)
                        
                        # 复制按钮
                        col1, col2 = st.columns([1, 1])
                        with col1:
                            if st.button("📋 复制到剪贴板", type="primary", use_container_width=True):
                                if copy_manager.copy_to_clipboard(formatted_content):
                                    st.success("✅ 内容已复制到剪贴板！")
                                    st.info("💡 请按照上方发布指南，将内容粘贴到对应平台发布")
                                    
                                    # 保存发布记录（标记为已复制）
                                    storage.save_publish_record(
                                        article_id=selected_article_id,
                                        platform=publish_platform,
                                        publish_method="copy",
                                        publish_status="copied",
                                        error_message=""
                                    )
                                else:
                                    st.error("❌ 复制失败，请手动复制内容")
                        
                        with col2:
                            if st.button("📥 下载内容", use_container_width=True):
                                # 生成下载文件
                                safe_title = article.get('keyword', 'article').replace(' ', '_')[:50]
                                filename = f"{publish_platform.replace('（', '_').replace('）', '')}_{safe_title}.txt"
                                st.download_button(
                                    label="⬇️ 下载",
                                    data=formatted_content,
                                    file_name=filename,
                                    mime="text/plain",
                                    key="download_formatted_content"
                                )
        else:
            st.info("📝 请先在【2 自动创作】中生成文章")
        
        # 发布记录
        st.markdown("---")
        st.markdown("#### 📊 发布记录")
        
        publish_records = storage.get_publish_records(brand=brand)
        if publish_records:
            # 统计信息
            total_records = len(publish_records)
            success_records = len([r for r in publish_records if r.get('publish_status') == 'success'])
            copied_records = len([r for r in publish_records if r.get('publish_status') == 'copied'])
            failed_records = len([r for r in publish_records if r.get('publish_status') == 'failed'])
            
            stat_col1, stat_col2, stat_col3, stat_col4 = st.columns(4)
            with stat_col1:
                st.metric("总发布数", total_records)
            with stat_col2:
                st.metric("API成功", success_records, delta=f"{success_records/total_records*100:.1f}%" if total_records > 0 else "0%")
            with stat_col3:
                st.metric("已复制", copied_records, delta=f"{copied_records/total_records*100:.1f}%" if total_records > 0 else "0%")
            with stat_col4:
                st.metric("失败", failed_records)
            
            # 记录列表
            st.markdown("##### 最近发布记录")
            records_df = pd.DataFrame(publish_records[:20])  # 显示最近20条
            if not records_df.empty:
                # 格式化显示
                display_df = records_df[['platform', 'publish_method', 'publish_status', 'publish_url', 'published_at', 'created_at']].copy()
                display_df.columns = ['平台', '发布方式', '状态', '链接', '发布时间', '创建时间']
                display_df['状态'] = display_df['状态'].map({
                    'success': '✅ 成功',
                    'failed': '❌ 失败',
                    'pending': '⏳ 待发布',
                    'copied': '📋 已复制'
                })
                display_df['发布方式'] = display_df['发布方式'].map({
                    'api': 'API',
                    'copy': '一键复制'
                })
                
                st.dataframe(display_df, use_container_width=True, hide_index=True)
        else:
            st.info("暂无发布记录")

# =======================
# Tab10：配置优化助手
# =======================
with tab10:
    # 配置优化助手（与其他Tab保持一致的标题格式）
    st.markdown("### 🎯 配置优化助手")
    st.caption("分析品牌名和优势是否 GEO 友好，提供优化建议。优化后可一键应用到全局配置。")
    
    # 初始化优化结果存储
    if "config_optimization_result" not in st.session_state:
        st.session_state.config_optimization_result = None
    
    # 初始化配置hash（用于检测配置变化）
    if "config_hash" not in st.session_state:
        st.session_state.config_hash = None
    
    # 计算当前配置的hash（使用cfg中的最新值）
    import hashlib
    brand_for_hash = cfg.get("brand", "").strip() or brand or ""
    advantages_for_hash = cfg.get("advantages", "").strip() or advantages or ""
    current_config_str = f"{brand_for_hash}|{advantages_for_hash}|{cfg.get('competitors', '')}"
    current_config_hash = hashlib.md5(current_config_str.encode()).hexdigest()
    
    # 如果配置变化了，清除旧的优化结果
    # 但如果是因为应用版本导致的配置变化，保留优化结果
    if st.session_state.config_hash != current_config_hash:
        # 检查是否是应用版本导致的配置变化
        if not st.session_state.get("_applying_version", False):
            st.session_state.config_optimization_result = None
        st.session_state.config_hash = current_config_hash
        # 清除应用版本标志
        st.session_state["_applying_version"] = False
    
    # 检查配置是否有效
    if not st.session_state.cfg_valid:
        st.warning("⚠️ 请先在侧边栏完成配置并点击'应用配置'")
        st.info("配置优化助手需要有效的配置才能进行分析。")
    else:
        # 显示当前配置
        with st.expander("📋 当前配置", expanded=False):
            col1, col2 = st.columns(2)
            with col1:
                brand_display = cfg.get("brand", "") or brand or "未设置"
                st.markdown(f"**品牌名**：{brand_display}")
            with col2:
                st.markdown(f"**竞品数量**：{len(competitor_list)}个")
            advantages_display = cfg.get("advantages", "") or advantages or "未设置"
            st.markdown(f"**核心优势**：{advantages_display}")
            if competitor_list:
                st.markdown(f"**竞品列表**：{', '.join(competitor_list[:5])}{'...' if len(competitor_list) > 5 else ''}")
        
        # 分析按钮
        col1, col2 = st.columns([1, 3])
        with col1:
            analyze_btn = st.button("🔍 分析配置优化", type="primary", use_container_width=True, key="tab10_optimize_config")
        
        with col2:
            if st.session_state.config_optimization_result:
                st.success("✅ 已有优化结果，可直接查看下方建议")
        
        # 执行分析
        if analyze_btn:
            with st.spinner("正在分析配置，优化建议生成中..."):
                try:
                    from modules.config_optimizer import ConfigOptimizer
                    
                    optimizer = ConfigOptimizer()
                    
                    # 从配置中获取品牌名、优势描述和竞品列表（确保使用最新配置）
                    brand_for_optimizer = cfg.get("brand", "").strip() or brand or ""
                    advantages_for_optimizer = cfg.get("advantages", "").strip() or advantages or ""
                    competitors_str = cfg.get("competitors", "")
                    competitor_list_for_optimizer = [c.strip() for c in competitors_str.split("\n") if c.strip()]
                    
                    # 验证必要配置
                    if not brand_for_optimizer:
                        st.error("❌ 品牌名不能为空，请在侧边栏配置主品牌名称")
                        st.stop()
                    
                    if not advantages_for_optimizer:
                        st.warning("⚠️ 优势描述为空，建议在侧边栏配置核心优势/卖点")
                    
                    # 临时构建LLM用于分析（使用当前配置）
                    temp_llm = build_llm(
                        cfg["gen_provider"],
                        cfg["gen_api_key"],
                        model_defaults(cfg["gen_provider"]),
                        float(cfg.get("temperature", 0.7))
                    )
                    
                    result = optimizer.optimize_config(
                        brand=brand_for_optimizer,
                        advantages=advantages_for_optimizer,
                        competitors=competitor_list_for_optimizer,
                        llm_chain=temp_llm
                    )
                    st.session_state.config_optimization_result = result
                    st.session_state.config_hash = current_config_hash
                    st.success("✅ 配置分析完成！")
                    st.rerun()
                except Exception as e:
                    st.error(f"❌ 配置优化分析失败：{e}")
                    import traceback
                    with st.expander("查看错误详情"):
                        st.code(traceback.format_exc())
                    st.session_state.config_optimization_result = None
        
        # 显示优化结果
        if st.session_state.config_optimization_result:
            result = st.session_state.config_optimization_result
            if result.get("success", False):
                st.markdown("---")
                st.markdown("#### 📊 优化分析结果")
                
                # 评估总结
                if result.get("summary"):
                    st.markdown("**📝 评估总结**")
                    st.info(result["summary"])
                
                # 优化建议
                if result.get("suggestions"):
                    st.markdown("**💡 优化建议**")
                    suggestions = result["suggestions"]
                    
                    if suggestions.get("brand", {}).get("problem"):
                        st.markdown("**🔸 品牌名问题**：")
                        # 直接使用st.markdown渲染，CSS会限制标题大小
                        problem_text = suggestions["brand"]["problem"]
                        st.markdown(problem_text)
                        if suggestions["brand"].get("suggestion"):
                            st.markdown("**✅ 建议**：")
                            suggestion_text = suggestions["brand"]["suggestion"]
                            st.markdown(suggestion_text)
                    
                    if suggestions.get("advantages", {}).get("problem"):
                        st.markdown("**🔸 优势描述问题**：")
                        problem_text = suggestions["advantages"]["problem"]
                        st.markdown(problem_text)
                        if suggestions["advantages"].get("suggestion"):
                            st.markdown("**✅ 建议**：")
                            suggestion_text = suggestions["advantages"]["suggestion"]
                            st.markdown(suggestion_text)
                
                # 推荐版本
                recommended_versions = result.get("recommended_versions", [])
                if recommended_versions:
                    st.markdown("**🎯 推荐版本**")
                    st.caption("选择最适合的版本，点击「应用版本」按钮即可更新配置")
                    
                    # 检查是否有有效的推荐版本
                    valid_versions = [v for v in recommended_versions if v.get("brand") or v.get("advantages")]
                    if not valid_versions:
                        st.warning("⚠️ 推荐版本数据为空，可能是解析失败。请查看完整报告或重新分析。")
                        if result.get("raw_result"):
                            with st.expander("查看原始输出中的推荐版本部分"):
                                raw = result["raw_result"]
                                if "【推荐版本】" in raw:
                                    raw_versions = raw.split("【推荐版本】")[1].split("【")[0]
                                    st.code(raw_versions)
                    
                    for i, version in enumerate(recommended_versions[:3], 1):
                        version_name_map = {
                            1: "保守优化",
                            2: "平衡优化",
                            3: "激进优化"
                        }
                        version_name = version_name_map.get(i, f"版本{i}")
                        
                        with st.expander(f"版本{i}：{version_name}", expanded=False):  # 默认不展开，用户自行选择
                            # 检查版本数据是否有效
                            has_brand = bool(version.get("brand", "").strip())
                            has_advantages = bool(version.get("advantages", "").strip())
                            has_reason = bool(version.get("reason", "").strip())
                            
                            if not has_brand and not has_advantages:
                                st.warning("⚠️ 该版本数据不完整，请查看完整报告或重新分析")
                                if result.get("raw_result"):
                                    with st.expander("查看原始输出中的该版本"):
                                        # 尝试从原始输出中提取
                                        raw = result["raw_result"]
                                        if f"版本{i}" in raw:
                                            version_raw = raw.split(f"版本{i}")[1]
                                            if i < 3:
                                                next_version = f"版本{i+1}"
                                                if next_version in version_raw:
                                                    version_raw = version_raw.split(next_version)[0]
                                            st.code(version_raw[:500])  # 显示前500字符
                            else:
                                col1, col2 = st.columns([2, 1])
                                with col1:
                                    if has_brand:
                                        st.markdown(f"**品牌名**：`{version['brand']}`")
                                    else:
                                        st.warning("⚠️ 品牌名为空")
                                    
                                    if has_advantages:
                                        st.markdown(f"**优势描述**：{version['advantages']}")
                                    else:
                                        st.warning("⚠️ 优势描述为空")
                                    
                                    if has_reason:
                                        st.caption(f"💭 理由：{version['reason']}")
                                    else:
                                        st.caption("💭 理由：未提供")
                                
                                with col2:
                                    # 应用按钮
                                    apply_disabled = not (has_brand and has_advantages)
                                    if st.button(
                                        f"✅ 应用版本{i}", 
                                        key=f"tab10_apply_version_{i}", 
                                        use_container_width=True, 
                                        type="primary",
                                        disabled=apply_disabled
                                    ):
                                        if has_brand and has_advantages:
                                            # 设置标志，表示正在应用版本（防止优化结果被清除）
                                            st.session_state["_applying_version"] = True
                                            # 更新配置
                                            st.session_state.cfg["brand"] = version["brand"]
                                            st.session_state.cfg["advantages"] = version["advantages"]
                                            # 设置标志，表示需要更新侧边栏输入框
                                            st.session_state["_pending_brand_update"] = version["brand"]
                                            st.session_state["_pending_advantages_update"] = version["advantages"]
                                            st.session_state.cfg_applied = False  # 需要重新应用配置
                                            st.success(f"✅ 已应用版本{i}，侧边栏已更新，请点击'应用配置'以生效")
                                            st.info("💡 配置更新后，建议重新运行关键词蒸馏和内容创作，以获得最佳效果")
                                            st.rerun()
                                    if apply_disabled:
                                        st.caption("⚠️ 数据不完整，无法应用")
                
                # 预期效果
                if result.get("expected_effects"):
                    st.markdown("**📈 预期效果**")
                    effects = result["expected_effects"]
                    # 使用文本而不是 metric，避免内容被截断
                    if effects.get("mention_rate"):
                        st.markdown(f"- 提及率提升预期：{effects['mention_rate']}")
                    if effects.get("geo_friendliness"):
                        st.markdown(f"- GEO友好度提升：{effects['geo_friendliness']}")
                
                # 完整报告
                if result.get("raw_result"):
                    with st.expander("📄 查看完整分析报告", expanded=False):
                        st.markdown(result["raw_result"])
                        
                        # 如果推荐版本为空或解析失败，显示原始输出中的推荐版本部分
                        recommended_versions = result.get("recommended_versions", [])
                        if not recommended_versions or all(
                            not v.get("brand") and not v.get("advantages") 
                            for v in recommended_versions
                        ):
                            st.warning("⚠️ 推荐版本解析失败，以下是原始输出中的推荐版本部分，请检查格式：")
                            raw = result["raw_result"]
                            if "【推荐版本】" in raw:
                                raw_versions = raw.split("【推荐版本】")[1].split("【")[0]
                                st.code(raw_versions, language="text")
                                st.info("💡 如果原始输出中包含推荐版本但解析失败，请检查格式是否符合要求")
                
                # 调试信息（可选）
                if st.checkbox("🔍 显示调试信息", key="tab10_debug"):
                    st.markdown("#### 调试信息")
                    debug_info = {
                        "推荐版本数量": len(result.get("recommended_versions", [])),
                        "版本详情": result.get("recommended_versions", []),
                        "配置hash": st.session_state.config_hash,
                        "解析错误": result.get("parse_errors", [])
                    }
                    st.json(debug_info)
                    
                    # 显示原始输出的关键部分
                    if result.get("raw_result"):
                        raw = result["raw_result"]
                        if "【推荐版本】" in raw:
                            st.markdown("**原始输出中的推荐版本部分：**")
                            raw_versions = raw.split("【推荐版本】")[1].split("【")[0]
                            st.code(raw_versions[:1000], language="text")  # 显示前1000字符
            else:
                st.error(f"❌ 分析失败：{result.get('error', '未知错误')}")
                if result.get("raw_result"):
                    with st.expander("查看原始输出"):
                        st.code(result["raw_result"])
        else:
            st.info("💡 点击上方「分析配置优化」按钮开始分析，系统会根据当前配置生成优化建议。")
            st.caption("提示：当您修改品牌名、优势描述或竞品列表后，系统会自动清除旧结果，需要重新分析。")

st.caption("最完整版：GitHub模板 + 真实多模型验证 + 现有文章优化 • GEO全闭环，专注AI品牌影响力")
