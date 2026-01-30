import streamlit as st


def ss_init(key, default):
    """
    统一的 session_state 初始化函数。

    - 仅当 key 不存在时才写入默认值
    - 避免在多个模块中重复实现
    """
    if key not in st.session_state:
        st.session_state[key] = default


def init_session_state():
    """
    初始化 GEO 应用中跨 Tab 使用的核心 session_state 字段。

    说明：
    - 这里只负责**跨 Tab 共享**或在多处使用的 key
    - 各 Tab 内部的临时/局部状态仍然由 Tab 自己按需调用 ss_init
    """
    # 配置相关
    # ss_init("cfg", {})  # 移除：由主程序 geo_tool.py 负责初始化，避免空字典覆盖默认配置
    ss_init("cfg_applied", False)
    ss_init("cfg_valid", False)
    ss_init("cfg_errors", [])

    # 关键词模块
    ss_init("keywords", [])
    ss_init("kw_last_num", 40)
    ss_init("kw_generation_mode", "AI生成")
    ss_init("wordbanks", None)

    # 内容创作模块
    ss_init("generated_contents", [])
    ss_init("zip_bytes", None)
    ss_init("zip_filename", "")
    ss_init("content_scores", {})
    ss_init("selected_content_idx", 0)

    # 文章优化模块
    ss_init("optimized_article", "")
    ss_init("opt_changes", "")
    ss_init("opt_platform", "通用优化")

    # 多模型验证
    ss_init("verify_combined", None)
    ss_init("verify_last_queries", "")

    # 其他跨模块使用的标志位
    ss_init("cancel_generation", False)

