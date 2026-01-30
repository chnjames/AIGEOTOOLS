import streamlit as st


def inject_global_theme():
    """注入全局 CSS 主题，保持与原 geo_tool.py 中完全一致的视觉风格。"""
    st.markdown(
        """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600&family=Noto+Sans+SC:wght@400;500;600&display=swap');

::root {
  --bg: #FFFFFF;
  --panel: #F7FAFC;
  --text: #1A202C;
  --muted: #4A5568;
  --border: #E2E8F0;
  --primary: #2563EB;
  --shadow: 0 1px 2px rgba(16,24,40,.04), 0 6px 16px rgba(16,24,40,.06);
  --radius: 12px;
}

html, body, .stApp {
  font-family: "Inter", "Noto Sans SC", system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif !important;
  background: var(--bg) !important;
  color: var(--text) !important;
}

.block-container { padding-top: 1.6rem !important; padding-bottom: 3.5rem !important; }

/* Sidebar */
section[data-testid="stSidebar"] { background: var(--panel) !important; border-right: 1px solid var(--border) !important; }

/* 侧边栏分组卡片 */
section[data-testid="stSidebar"] .stForm,
section[data-testid="stSidebar"] div[data-testid="stVerticalBlockBorderWrapper"] {
  background: #FFFFFF !important;
  border-radius: 8px !important;
  padding: 1rem !important;
  margin-bottom: 1rem !important;
  border: 1px solid var(--border) !important;
  box-shadow: 0 1px 2px rgba(16,24,40,.02), 0 2px 8px rgba(16,24,40,.04) !important;
}

/* 标题层级 */
h1, h2, h3, h4, h5, h6 { font-family: "Inter", "Noto Sans SC", sans-serif !important; color: var(--text) !important; }
h1 { font-size: 2.15rem !important; font-weight: 600 !important; letter-spacing: -0.4px !important; margin-bottom: 1.0rem !important; }
h2 { font-size: 1.25rem !important; font-weight: 600 !important; color: var(--text) !important; margin: 1.8rem 0 0.75rem 0 !important; }

/* 按钮 - 保留圆角 */
button[kind="primary"],
div[data-testid="stButton"] button[kind="primary"],
div[data-testid="stFormSubmitButton"] button[kind="primary"] {
  # background-color: var(--primary) !important;
  # color: white !important;
  border-radius: var(--radius) !important;
  # border: none !important;
}

button[kind="secondary"],
div[data-testid="stButton"] button[kind="secondary"] {
  background: #FFFFFF !important;
  border: 1px solid var(--border) !important;
  # color: var(--text) !important;
  border-radius: var(--radius) !important;
}

button:focus, button:focus-visible {
  box-shadow: 0 0 0 3px rgba(37,99,235,0.12) !important;
  outline: none !important;
}

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
  box-shadow: 0 0 0 3px rgba(37,99,235,0.12) !important;
}

/* Tabs - 移除圆角和边框（核心修复） */
.stTabs [role="tab"] {
  border-radius: 0 !important;
  border: none !important;
  background: transparent !important;
  padding: 12px 16px !important;
  color: var(--muted) !important;
  font-weight: 500 !important;
  margin: 0 !important;
}

/* 防止 focus 框干扰 */
.stTabs [role="tab"]:focus,
.stTabs [role="tab"]:focus-visible {
  outline: none !important;
  box-shadow: none !important;
  border: none !important;
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

/* 卡片容器 */
div[data-testid="stVerticalBlockBorderWrapper"] {
  border-radius: var(--radius) !important;
  box-shadow: var(--shadow) !important;
  padding: 1.5rem !important;
  background: #FFFFFF !important;
  margin-bottom: 1rem !important;
  border: 1px solid var(--border) !important;
}

/* Metric/KPI 卡片 */
div[data-testid="stMetricContainer"] {
  min-height: 130px !important;
  padding: 1rem !important;
  border-radius: var(--radius) !important;
  background: #FFFFFF !important;
  border: 1px solid var(--border) !important;
  box-shadow: var(--shadow) !important;
}

div[data-testid="stMetricValue"] {
    min-height: 3rem !important;
    height: 3rem !important;
    display: flex !important;
    align-items: center !important;
    font-size: 1.5rem !important;
}

/* Expander */
.streamlit-expanderHeader {
  font-weight: 500 !important;
  color: var(--text) !important;
  padding: 0.75rem 0 !important;
}

/* 分隔线 */
hr {
  border: none;
  border-top: 1px solid var(--border) !important;
  margin: 1.5rem 0 !important;
}
</style>
""",
        unsafe_allow_html=True,
    )

    # 保留原有按钮圆角覆盖，避免视觉回退
    st.markdown(
        "<style>button{border-radius:0px !important;}</style>",
        unsafe_allow_html=True,
    )

