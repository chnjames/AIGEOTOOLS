# Tab2：✍️ 自动创作（含批量 ZIP / GitHub 模板）
# 从 geo_tool.py 迁移，通过 render_tab_autowrite() 供主入口调用。

import io
import json
import re
import time
import zipfile
from datetime import datetime

import streamlit as st
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import PromptTemplate

from modules.content_scorer import ContentScorer
from modules.eeat_enhancer import EEATEnhancer
from modules.fact_density_enhancer import FactDensityEnhancer
from modules.multimodal_prompt import MultimodalPromptGenerator
from modules.optimization_techniques import OptimizationTechniqueManager
from modules.schema_generator import SchemaGenerator


INVALID_FS_CHARS = r'<>:"/\\|?*\n\r\t'


def sanitize_filename(name: str, max_len: int = 80) -> str:
    """Copy of utility from geo_tool, kept local to avoid circular imports."""
    if not name:
        return "untitled"
    name = name.strip()
    name = re.sub(rf"[{re.escape(INVALID_FS_CHARS)}]", "_", name)
    name = re.sub(r"_+", "_", name).strip("_")
    return name[:max_len] if len(name) > max_len else name


def render_tab_autowrite(
    storage,
    ss_init,
    gen_llm,
    brand: str,
    advantages: str,
    cfg: dict,
    record_api_cost,
    model_defaults,
) -> None:
    """
    渲染 Tab2：自动创作内容（含批量 ZIP / GitHub 模板）。

    通过参数接收 storage / ss_init / gen_llm / brand / advantages / cfg /
    record_api_cost / model_defaults，由主入口在 with tab2 内调用。
    """
    # 标题和清空按钮放在同一行，布局更紧凑
    header_col1, header_col2 = st.columns([4, 1])
    with header_col1:
        st.markdown("**✍️ 内容生成**")
        st.caption("基于关键词自动生成符合 GEO 原则的专业内容，支持单篇和批量生成")
    with header_col2:
        st.markdown("")
        if st.button("清空本模块结果", use_container_width=True, key="content_clear"):
            st.session_state.generated_contents = []
            st.session_state.zip_bytes = None
            st.session_state.zip_filename = ""
            st.session_state.content_scores = {}
            st.session_state.selected_content_idx = 0
            st.toast("创作内容已清空。")

    if not st.session_state.keywords:
        st.info("💡 请先在【🎯 关键词蒸馏】生成关键词。")
    else:
        # === 区域1：快速生成区 ===
        with st.container(border=True):
            with st.form("content_form", clear_on_submit=False):
                mode = st.radio(
                    "生成模式",
                    ["单篇生成", "批量生成"],
                    horizontal=True,
                    key="content_mode",
                    help="单篇生成：一次生成一篇内容；批量生成：一次生成多篇内容"
                )

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
                    "新浪博客（博客）",
                    "新浪新闻（资讯）",
                    "搜狐号（资讯）",
                    "QQ空间（社交）",
                    "邦阅网（外贸）",
                    "一点号（资讯）",
                    "东方财富（财经）",
                    "原创力文档（文档）",
                ]

                keywords_to_generate = []
                if mode == "单篇生成":
                    col1, col2 = st.columns([2, 1])
                    with col1:
                        selected_keyword = st.selectbox(
                            "选择关键词",
                            st.session_state.keywords,
                            key="content_kw_single"
                        )
                        if not selected_keyword:
                            st.warning("⚠️ 请先选择关键词")
                    with col2:
                        platform = st.selectbox(
                            "平台",
                            platforms,
                            key="content_platform_single"
                        )
                    if selected_keyword:
                        keywords_to_generate = [(selected_keyword, platform)]
                else:
                    col1, col2 = st.columns([3, 1])
                    with col1:
                        selected_keywords = st.multiselect(
                            "选择关键词（可多选）",
                            st.session_state.keywords,
                            key="content_kw_multi",
                            help="可同时选择多个关键词进行批量生成"
                        )
                    with col2:
                        platform = st.selectbox(
                            "统一平台",
                            platforms,
                            key="content_platform_multi"
                        )
                    keywords_to_generate = [(kw, platform) for kw in selected_keywords]

                with st.expander("🎨 高级优化技巧（可选）", expanded=False):
                    technique_manager = OptimizationTechniqueManager()
                    all_techniques = technique_manager.list_techniques()
                    technique_options = [f"{tech['icon']} {tech['name']}" for tech in all_techniques]

                    selected_technique_names = st.multiselect(
                        "选择优化技巧",
                        options=technique_options,
                        default=[],
                        key="content_techniques",
                        help="选择要应用的优化技巧，可多选。技巧会动态调整内容生成策略。"
                    )

                    if selected_technique_names:
                        st.caption("已选择：" + "、".join(selected_technique_names))
                        with st.expander("查看技巧说明", expanded=False):
                            for tech_name in selected_technique_names:
                                tech_icon_name = tech_name.split(" ", 1)[1] if " " in tech_name else tech_name
                                for tech in all_techniques:
                                    if tech['name'] == tech_icon_name:
                                        st.markdown(f"**{tech['icon']} {tech['name']}**")
                                        st.caption(tech['description'])
                                        break

                run_content_disabled = (not st.session_state.cfg_valid) or (gen_llm is None) or (not keywords_to_generate)
                run_content = st.form_submit_button(
                    "🚀 生成内容",
                    use_container_width=True,
                    disabled=run_content_disabled,
                    type="primary"
                )

        if run_content:
            selected_technique_names = st.session_state.get("content_techniques", [])
            if not keywords_to_generate or len(keywords_to_generate) == 0:
                st.warning("⚠️ 请至少选择一个关键词进行生成")
                st.stop()

            if not brand or not brand.strip():
                st.error("❌ 品牌名称不能为空，请在侧边栏配置品牌信息")
                st.stop()

            if not advantages or not advantages.strip():
                st.error("❌ 核心优势不能为空，请在侧边栏配置核心优势")
                st.stop()
            st.session_state.generated_contents = []
            st.session_state.zip_bytes = None
            st.session_state.zip_filename = ""
            st.session_state.content_scores = {}
            st.session_state.selected_content_idx = 0

            contents = []
            zip_buffer = io.BytesIO()

            total_items = len(keywords_to_generate)
            if total_items == 0:
                st.warning("⚠️ 没有可生成的内容")
                st.stop()

            progress_bar = st.progress(0)
            ss_init("cancel_generation", False)

            status_col, cancel_col = st.columns([4, 1])
            status_text = status_col.empty()
            with cancel_col:
                if st.button("❌ 取消生成", key="cancel_gen_btn", use_container_width=True):
                    st.session_state.cancel_generation = True
                    st.warning("⚠️ 生成已取消")
                    st.stop()

            scorer = ContentScorer()
            schema_gen = None

            try:
                with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
                    for idx, (keyword, plat) in enumerate(keywords_to_generate):
                        if st.session_state.get("cancel_generation", False):
                            st.warning("⚠️ 生成已取消")
                            break

                        progress = (idx + 1) / total_items
                        progress_bar.progress(progress)
                        status_text.text(f"正在生成 {idx + 1}/{total_items}: {keyword} - {plat}")

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
【E-E-A-T 强化要求】
- 专业性：使用专业术语，展示深度知识
- 经验性：包含实际使用经验或案例（用"实际测试"、"使用中发现"等表述）
- 权威性：添加来源占位（如"根据XX行业报告"、"参考XX标准"），至少2处数据来源占位
- 可信度：明确标注不确定信息（如"据公开资料"、"建议参考"），避免编造具体数据
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
【E-E-A-T 强化要求】
- 专业性：使用准确的技术术语，展示技术深度
- 经验性：包含实际开发或使用经验（如"实际测试中"、"开发实践表明"）
- 权威性：引用技术标准或文档占位（如"参考XX技术规范"、"按照XX框架标准"），至少1处标准来源占位
- 可信度：代码示例用占位符，明确标注"示例代码"、"仅供参考"
【开始】
"""
                            elif plat == "B站（视频脚本）":
                                content_template = """
你是GEO专家 + B站UP主。
【关键词】{keyword}
【品牌】{brand}
【优势】{advantages}
【要求】
1) 5个点击标题（吸引人、适合视频）
2) 开场钩子：前3秒抓住注意力
3) 时间戳分段：每个段落标注时间（如"00:30-02:00"）
4) 画面建议：每个段落描述画面内容（用【画面：xxx】标注）
5) {brand}演示部分：详细说明如何使用品牌产品/服务
6) 结尾：总结+互动引导（点赞、投币、关注）
7) 描述：时间戳 + 10搜索词 + 15标签
8) 字数：800-2000字（适合视频脚本长度）
【格式】标题-开场-分段（时间戳+画面建议）-演示-结尾-描述
【开始】
"""
                            elif plat == "头条号（资讯软文）":
                                content_template = """
你是GEO专家 + 头条作者。
【关键词】{keyword}
【品牌】{brand}
【优势】{advantages}
【要求】
1) 4个热点标题（吸引点击、符合头条风格）
2) 开头：热点引入或疑问开头
3) 正文：列表结构（Top/步骤）、信息密度高、可读性强
4) 自然提及品牌2-4次，先讲通用标准再推荐品牌
5) 数据占位：用"据XX数据"、"参考XX报告"等占位
6) 适合头条用户：内容轻松、可读性强
7) 字数：800-2000字
8) 结尾：总结+互动引导
【格式】标题-正文（列表结构）-总结
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
【E-E-A-T 强化要求】
- 专业性：使用专业术语，展示深度知识
- 经验性：包含实际使用经验或案例（用"实际测试"、"使用中发现"等表述）
- 权威性：添加来源占位（如"根据XX行业报告"、"参考XX标准"），至少2处数据来源占位
- 可信度：明确标注不确定信息（如"据公开资料"、"建议参考"），避免编造具体数据
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
【E-E-A-T 强化要求】
- 专业性：使用专业术语，展示专业知识
- 经验性：包含实际应用经验或案例（用"实际应用中"、"使用中发现"等表述）
- 权威性：添加来源占位（如"根据XX行业报告"、"参考XX数据"），至少2处数据来源占位
- 可信度：明确标注不确定信息，避免编造具体数据，使用占位建议
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
【E-E-A-T 强化要求】
- 专业性：使用专业术语，展示深度分析能力
- 经验性：包含实际应用经验或案例（用"实际应用中"、"使用中发现"等表述）
- 权威性：添加来源占位（如"根据XX行业报告"、"参考XX数据"），至少2处数据来源占位
- 可信度：明确标注不确定信息，保持客观中立，避免编造具体数据
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
                            elif plat == "新浪博客（博客）":
                                content_template = """
你是GEO专家 + 新浪博客作者。
【关键词】{keyword}
【品牌】{brand}
【优势】{advantages}
【要求】
1) 3个吸引人的标题
2) 开头：故事化或热点引入
3) 正文：深度分析、案例丰富、观点鲜明
4) 自然提及品牌2-4次
5) 适合新浪博客：内容深度、可读性强
6) 字数：1500-3000字
7) 结尾：总结+延伸思考
8) 配图建议：用【配图：xxx】标注配图位置
【格式】标题-正文-总结
【开始】
"""
                            elif plat == "新浪新闻（资讯）":
                                content_template = """
你是GEO专家 + 新浪新闻作者。
【关键词】{keyword}
【品牌】{brand}
【优势】{advantages}
【要求】
1) 3个新闻式标题（客观、吸引人）
2) 开头：新闻导语式引入，5W1H要素
3) 正文：客观报道、数据支撑、多角度分析
4) 自然提及品牌2-3次，保持客观中立
5) 适合新闻平台：信息准确、时效性强
6) 字数：800-2000字
7) 结尾：总结+相关链接建议
【E-E-A-T 强化要求】
- 专业性：使用专业术语，展示新闻专业素养
- 经验性：包含实际案例或应用经验（用"实际应用中"、"使用中发现"等表述）
- 权威性：添加来源占位（如"根据XX行业报告"、"参考XX数据"），至少2处数据来源占位
- 可信度：明确标注不确定信息，保持客观中立，避免编造具体数据
【格式】标题-导语-正文-总结
【开始】
"""
                            elif plat == "搜狐号（资讯）":
                                content_template = """
你是GEO专家 + 搜狐号作者。
【关键词】{keyword}
【品牌】{brand}
【优势】{advantages}
【要求】
1) 3个吸引人的标题
2) 开头：热点引入或疑问开头
3) 正文：信息丰富、结构清晰、观点明确
4) 自然提及品牌2-4次
5) 适合搜狐用户：内容专业、可读性强
6) 字数：1000-2500字
7) 结尾：总结+互动引导
8) 配图建议：用【配图：xxx】标注
【格式】标题-正文-总结
【开始】
"""
                            elif plat == "QQ空间（社交）":
                                content_template = """
你是GEO专家 + QQ空间创作者。
【关键词】{keyword}
【品牌】{brand}
【优势】{advantages}
【要求】
1) 2-3个轻松有趣的标题
2) 开头：生活化场景引入
3) 正文：轻松活泼、贴近生活、有共鸣
4) 自然提及品牌2-3次，融入使用体验
5) 适合QQ空间：社交化、互动性强
6) 字数：500-1500字
7) 结尾：互动引导（点赞、评论、转发）
8) 配图建议：用【配图：xxx】标注，建议3-5张图
【格式】标题-正文-互动引导
【开始】
"""
                            elif plat == "邦阅网（外贸）":
                                content_template = """
你是GEO专家 + 邦阅网作者。
【关键词】{keyword}
【品牌】{brand}
【优势】{advantages}
【要求】
1) 3个专业标题（外贸/商务相关）
2) 开头：行业背景或市场分析引入
3) 正文：专业分析、案例说明、实用建议
4) 自然提及品牌2-4次，突出商业价值
5) 适合外贸平台：专业性强、实用价值高
6) 字数：1000-2500字
7) 结尾：总结+行动建议
【E-E-A-T 强化要求】
- 专业性：使用专业外贸/商务术语，展示行业知识深度
- 经验性：包含实际外贸或应用经验（用"实际应用中"、"使用中发现"等表述）
- 权威性：添加来源占位（如"根据XX行业报告"、"参考XX数据"），至少2处数据来源占位
- 可信度：明确标注不确定信息，避免编造具体数据，使用占位建议
【格式】标题-正文-总结
【开始】
"""
                            elif plat == "一点号（资讯）":
                                content_template = """
你是GEO专家 + 一点号作者。
【关键词】{keyword}
【品牌】{brand}
【优势】{advantages}
【要求】
1) 3个吸引人的标题
2) 开头：热点或故事引入
3) 正文：信息丰富、观点鲜明、可读性强
4) 自然提及品牌2-4次
5) 适合一点资讯：内容深度、覆盖面广
6) 字数：1000-2500字
7) 结尾：总结+延伸阅读建议
【格式】标题-正文-总结
【开始】
"""
                            elif plat == "东方财富（财经）":
                                content_template = """
你是GEO专家 + 东方财富作者。
【关键词】{keyword}
【品牌】{brand}
【优势】{advantages}
【要求】
1) 3个财经专业标题
2) 开头：市场背景或数据引入
3) 正文：专业分析、数据支撑、趋势判断
4) 自然提及品牌2-3次，突出商业/投资价值
5) 适合财经平台：专业性强、数据准确
6) 字数：1500-3000字
7) 结尾：总结+投资/商业建议
8) 数据占位：用"据XX数据"、"参考XX报告"等占位
【E-E-A-T 强化要求】
- 专业性：使用专业财经术语，展示深度分析能力
- 经验性：包含实际投资或应用经验（用"实际投资中"、"使用中发现"等表述）
- 权威性：添加来源占位（如"根据XX行业报告"、"参考XX数据"），至少3处数据来源占位
- 可信度：明确标注不确定信息，避免编造具体数据，使用占位建议
【格式】标题-正文-总结
【开始】
"""
                            elif plat == "原创力文档（文档）":
                                content_template = """
你是GEO专家 + 原创力文档作者。
【关键词】{keyword}
【品牌】{brand}
【优势】{advantages}
【要求】
1) 2个专业文档标题
2) 开头：背景介绍或目的说明
3) 正文：结构化文档、章节清晰、内容专业
4) 自然提及品牌2-4次，突出技术/专业价值
5) 适合文档平台：结构清晰、专业性强
6) 字数：2000-5000字
7) 格式：目录+章节+总结
8) 包含：概述、详细内容、案例分析、总结
【E-E-A-T 强化要求】
- 专业性：使用专业术语，展示技术/专业深度
- 经验性：包含实际应用经验或案例（用"实际应用中"、"使用中发现"等表述）
- 权威性：引用技术标准或文档占位（如"参考XX技术规范"、"按照XX标准"），至少2处标准来源占位
- 可信度：明确标注不确定信息，避免编造具体数据，使用占位建议
【格式】目录-正文（分章节）-总结
【开始】
"""
                            elif plat == "GitHub（README/文档）":
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
                            else:
                                st.error(f"❌ 未知平台：{plat}，请检查平台名称")
                                contents.append({
                                    "keyword": keyword,
                                    "platform": plat,
                                    "content": f"[错误：未知平台 {plat}]",
                                    "ext": "txt",
                                    "filename": f"ERROR_{sanitize_filename(plat,30)}.txt",
                                    "score": None,
                                    "json_ld": None,
                                    "error": f"未知平台：{plat}"
                                })
                                continue

                            if selected_technique_names:
                                technique_manager = OptimizationTechniqueManager()
                                technique_ids = technique_manager.get_technique_ids_by_names(
                                    [name.split(" ", 1)[1] if " " in name else name for name in selected_technique_names]
                                )
                                content_template = technique_manager.enhance_prompt(content_template, technique_ids)

                            prompt = PromptTemplate.from_template(content_template)
                            chain = prompt | gen_llm | StrOutputParser()

                            input_text = content_template.format(keyword=keyword, brand=brand, advantages=advantages)

                            max_retries = 2
                            retry_count = 0
                            content = None

                            while retry_count <= max_retries:
                                try:
                                    if st.session_state.get("cancel_generation", False):
                                        break
                                    content = chain.invoke({"keyword": keyword, "brand": brand, "advantages": advantages})
                                    break
                                except Exception as e:
                                    error_msg = str(e)
                                    retry_count += 1
                                    is_retryable = (
                                        "timeout" in error_msg.lower() or
                                        "connection" in error_msg.lower() or
                                        "network" in error_msg.lower() or
                                        "rate limit" in error_msg.lower() or
                                        "429" in error_msg.lower()
                                    )
                                    if retry_count <= max_retries and is_retryable:
                                        wait_time = retry_count * 2
                                        st.warning(f"⚠️ 生成失败（{keyword} - {plat}），{wait_time}秒后重试（{retry_count}/{max_retries}）...")
                                        time.sleep(wait_time)
                                        continue
                                    else:
                                        raise

                            if content is None:
                                if st.session_state.get("cancel_generation", False):
                                    st.warning("⚠️ 生成已取消")
                                    break
                                else:
                                    raise ValueError("生成失败：已达到最大重试次数或遇到不可重试的错误")

                            try:
                                if not content or not content.strip():
                                    raise ValueError("生成的内容为空")
                                if len(content.strip()) < 50:
                                    st.warning(f"⚠️ 生成的内容过短（{len(content.strip())}字），可能不完整：{keyword}")
                            except Exception as e:
                                error_msg = str(e)
                                st.error(f"❌ 生成失败（{keyword} - {plat}）：{error_msg}")
                                contents.append({
                                    "keyword": keyword,
                                    "platform": plat,
                                    "content": f"[生成失败：{error_msg}]",
                                    "ext": "txt",
                                    "filename": f"{sanitize_filename(plat,30)}_{sanitize_filename(brand,30)}_{sanitize_filename(keyword,60)}_ERROR.txt",
                                    "score": None,
                                    "json_ld": None,
                                    "error": error_msg
                                })
                                continue

                            if gen_llm:
                                try:
                                    model_name = getattr(gen_llm, 'model_name', None) or getattr(gen_llm, 'model', None) or model_defaults(cfg["gen_provider"])
                                    provider = cfg["gen_provider"]
                                    record_api_cost(
                                        operation_type="生成",
                                        provider=provider,
                                        model=model_name,
                                        input_text=input_text,
                                        output_text=content,
                                        keyword=keyword,
                                        platform=plat,
                                        brand=brand
                                    )
                                except Exception:
                                    pass

                            if plat == "GitHub（README/文档）":
                                ext = "md"
                            elif plat in ["微信公众号（长文）", "百家号（资讯）", "网易号（资讯）", "企鹅号（资讯）", "简书（文艺）",
                                         "新浪博客（博客）", "新浪新闻（资讯）", "搜狐号（资讯）", "QQ空间（社交）",
                                         "邦阅网（外贸）", "一点号（资讯）", "东方财富（财经）", "原创力文档（文档）"]:
                                ext = "md"
                            else:
                                ext = "txt"

                            filename = f"{sanitize_filename(plat,30)}_{sanitize_filename(brand,30)}_{sanitize_filename(keyword,60)}.{ext}"
                            zip_file.writestr(filename, content)

                            json_ld_schema = None
                            if plat == "GitHub（README/文档）":
                                try:
                                    if schema_gen is None:
                                        schema_gen = SchemaGenerator()
                                    json_ld_schema = schema_gen.generate_for_github(
                                        brand_name=brand,
                                        advantages=advantages,
                                        application_name=brand,
                                        description=advantages,
                                        application_category="WebApplication",
                                        operating_system="Web"
                                    )
                                except Exception as e:
                                    st.warning(f"JSON-LD Schema 生成失败：{e}")

                            score_data = None
                            if gen_llm:
                                try:
                                    score_chain = PromptTemplate.from_template("{input}") | gen_llm | StrOutputParser()
                                    score_data = scorer.score_content(
                                        content, brand, advantages, plat, score_chain
                                    )
                                    if not score_data or not isinstance(score_data, dict):
                                        raise ValueError("评分结果格式错误")
                                    content_key = f"{keyword}_{plat}"
                                    st.session_state.content_scores[content_key] = score_data
                                except Exception as e:
                                    error_msg = str(e)
                                    if "timeout" in error_msg.lower() or "connection" in error_msg.lower():
                                        error_type = "网络连接错误"
                                    elif "api" in error_msg.lower() or "key" in error_msg.lower() or "auth" in error_msg.lower():
                                        error_type = "API配置错误"
                                    else:
                                        error_type = "评分失败"
                                    st.warning(f"⚠️ 内容已生成，但{error_type}：{error_msg}")
                                    score_data = {"error": error_msg, "error_type": error_type, "retry_available": True}

                            contents.append({
                                "keyword": keyword,
                                "platform": plat,
                                "content": content,
                                "ext": ext,
                                "filename": filename,
                                "score": score_data,
                                "json_ld": json_ld_schema,
                            })
                            try:
                                storage.save_article(keyword, plat, content, filename, brand)
                            except Exception as e:
                                st.warning(f"内容已生成，但保存到数据库时出错：{e}")

                zip_buffer.seek(0)
                st.session_state.generated_contents = contents
                st.session_state.zip_bytes = zip_buffer.getvalue()
                st.session_state.zip_filename = f"{sanitize_filename(brand,40)}_GEO内容包.zip"

            except Exception as e:
                error_msg = str(e)
                st.error(f"❌ ZIP文件生成失败：{error_msg}")
                if contents:
                    st.session_state.generated_contents = contents
                    st.warning("⚠️ 部分内容已生成，但ZIP打包失败。可以单独下载每篇内容。")
            finally:
                if 'progress_bar' in locals():
                    progress_bar.empty()
                if 'status_text' in locals():
                    status_text.empty()

            if contents:
                success_count = len([c for c in contents if not c.get("error")])
                total_count = len(contents)
                if success_count == total_count:
                    st.success(f"✅ 生成完成！共生成 {total_count} 篇内容")
                else:
                    st.warning(f"⚠️ 生成完成：成功 {success_count} 篇，失败 {total_count - success_count} 篇")
                failed_scores = [c for c in contents if c.get("score", {}).get("error")]
                if failed_scores:
                    st.warning(f"⚠️ 其中 {len(failed_scores)} 篇内容评分失败，可在详情中重新评分")
                failed_generations = [c for c in contents if c.get("error")]
                if failed_generations:
                    st.error(f"❌ 其中 {len(failed_generations)} 篇内容生成失败，请检查错误信息后重试")

    # === 区域2：生成结果概览 ===
    if st.session_state.generated_contents:
        st.markdown("---")
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("生成篇数", len(st.session_state.generated_contents))
        with col2:
            scored_items = [item for item in st.session_state.generated_contents if item.get("score") and not item.get("score", {}).get("error")]
            if scored_items:
                avg_score = sum(item.get("score", {}).get("scores", {}).get("total", 0) for item in scored_items) / len(scored_items)
                st.metric("平均评分", f"{avg_score:.1f}/100")
            else:
                st.metric("平均评分", "未评分")
        with col3:
            st.metric("生成时间", datetime.now().strftime("%H:%M:%S"))

        if len(st.session_state.generated_contents) > 1:
            st.markdown("#### 📋 生成内容列表")
            ss_init("selected_content_idx", 0)

            filter_col1, filter_col2, filter_col3 = st.columns([2, 2, 1])
            with filter_col1:
                all_platforms = list(set(item["platform"] for item in st.session_state.generated_contents))
                filter_platform = st.selectbox(
                    "筛选平台",
                    ["全部"] + all_platforms,
                    key="content_filter_platform"
                )
            with filter_col2:
                sort_by = st.selectbox(
                    "排序方式",
                    ["生成顺序", "评分降序", "评分升序", "关键词"],
                    key="content_sort_by"
                )
            with filter_col3:
                if st.session_state.zip_bytes:
                    st.download_button(
                        "📥 批量下载ZIP",
                        st.session_state.zip_bytes,
                        st.session_state.zip_filename,
                        "application/zip",
                        use_container_width=True,
                        key="content_dl_zip_top"
                    )

            filtered_contents = st.session_state.generated_contents
            if filter_platform != "全部":
                filtered_contents = [item for item in filtered_contents if item["platform"] == filter_platform]

            if sort_by == "评分降序":
                filtered_contents = sorted(
                    filtered_contents,
                    key=lambda x: x.get("score", {}).get("scores", {}).get("total", 0) if x.get("score") and not x.get("score", {}).get("error") else -1,
                    reverse=True
                )
            elif sort_by == "评分升序":
                filtered_contents = sorted(
                    filtered_contents,
                    key=lambda x: x.get("score", {}).get("scores", {}).get("total", 100) if x.get("score") and not x.get("score", {}).get("error") else 101
                )
            elif sort_by == "关键词":
                filtered_contents = sorted(filtered_contents, key=lambda x: x["keyword"])

            for idx, item in enumerate(filtered_contents):
                item_key = (item.get("keyword"), item.get("platform"))
                original_idx = next(
                    (i for i, c in enumerate(st.session_state.generated_contents)
                     if (c.get("keyword"), c.get("platform")) == item_key),
                    0
                )

                score_display = "未评分"
                if item.get("score"):
                    if item.get("score", {}).get("error"):
                        score_display = "评分失败"
                    else:
                        total_score = item.get("score", {}).get("scores", {}).get("total", 0)
                        score_display = f"{total_score}/100"

                with st.expander(
                    f"{idx+1}. {item['keyword']} - {item['platform']} | 评分: {score_display}",
                    expanded=False
                ):
                    col1, col2 = st.columns([3, 1])
                    with col1:
                        preview_text = item["content"][:500] + "..." if len(item["content"]) > 500 else item["content"]
                        st.text_area(
                            "内容预览",
                            preview_text,
                            height=150,
                            disabled=True,
                            key=f"preview_{original_idx}"
                        )
                    with col2:
                        if st.button("查看详情", key=f"view_{original_idx}", use_container_width=True):
                            st.session_state.selected_content_idx = original_idx
                            st.rerun()
                        st.download_button(
                            "下载",
                            item["content"],
                            item["filename"],
                            mime=("text/markdown" if item["ext"] == "md" else "text/plain"),
                            use_container_width=True,
                            key=f"dl_{original_idx}"
                        )

        # === 区域3：内容详情区 ===
        if len(st.session_state.generated_contents) > 1:
            selected_idx = st.session_state.get("selected_content_idx", 0)
            if selected_idx < 0 or selected_idx >= len(st.session_state.generated_contents):
                selected_idx = 0
                st.session_state.selected_content_idx = 0
        else:
            selected_idx = 0

        if not st.session_state.generated_contents:
            st.info("💡 暂无生成的内容，请先生成内容。")
            return

        if selected_idx >= len(st.session_state.generated_contents):
            selected_idx = 0
            st.session_state.selected_content_idx = 0

        item = st.session_state.generated_contents[selected_idx]

        st.markdown("---")
        st.markdown(f"**📄 内容详情：{item['keyword']} - {item['platform']}**")

        detail_tab1, detail_tab2, detail_tab3 = st.tabs(["📄 内容预览", "📊 质量分析", "🎨 增强工具"])

        with detail_tab1:
            if item["ext"] == "md":
                st.code(item["content"], language="markdown")
            else:
                st.text_area(
                    "内容（可复制发布）",
                    item["content"],
                    height=400,
                    label_visibility="collapsed",
                    key="content_preview_detail"
                )

            col1, col2, col3 = st.columns(3)
            with col1:
                st.download_button(
                    "📥 下载单篇",
                    item["content"],
                    item["filename"],
                    mime=("text/markdown" if item["ext"] == "md" else "text/plain"),
                    use_container_width=True,
                    key="content_dl_single_detail"
                )
            with col2:
                if st.button("🔧 优化内容", use_container_width=True, key="goto_optimize"):
                    st.info("💡 请切换到【🔧 文章优化】Tab 进行内容优化")
            with col3:
                st.caption("💡 可直接选中上方内容复制")

            if item.get("json_ld") or item["platform"] == "GitHub（README/文档）":
                with st.expander("📋 JSON-LD Schema（可选）", expanded=False):
                    if item.get("json_ld"):
                        json_ld_code = item["json_ld"]
                    else:
                        try:
                            schema_gen = SchemaGenerator()
                            json_ld_code = schema_gen.generate_for_github(
                                brand_name=brand,
                                advantages=advantages,
                                application_name=brand,
                                description=advantages,
                                application_category="WebApplication",
                                operating_system="Web"
                            )
                            item["json_ld"] = json_ld_code
                        except Exception as e:
                            st.error(f"JSON-LD 生成失败：{e}")
                            json_ld_code = None

                    if json_ld_code:
                        st.code(json_ld_code, language="json")
                        try:
                            schema_gen = SchemaGenerator()
                            schema_dict = json.loads(json_ld_code)
                            html_script = schema_gen.generate_html_script_tag(schema_dict)
                            with st.expander("📄 HTML Script 标签", expanded=False):
                                st.code(html_script, language="html")
                            col1, col2 = st.columns(2)
                            with col1:
                                st.download_button(
                                    "下载 JSON-LD",
                                    json_ld_code,
                                    f"{sanitize_filename(brand,40)}_schema.json",
                                    mime="application/json",
                                    use_container_width=True,
                                    key="jsonld_dl_json_detail"
                                )
                            with col2:
                                st.download_button(
                                    "下载 HTML Script",
                                    html_script,
                                    f"{sanitize_filename(brand,40)}_schema.html",
                                    mime="text/html",
                                    use_container_width=True,
                                    key="jsonld_dl_html_detail"
                                )
                        except Exception:
                            pass

        with detail_tab2:
            if item.get("score"):
                score_data = item["score"]
                if score_data.get("error"):
                    st.warning(f"⚠️ 内容评分失败：{score_data.get('error')}")
                    retry_count_key = f"score_retry_count_{item['keyword']}_{item['platform']}"
                    retry_count = st.session_state.get(retry_count_key, 0)
                    max_retries = 3
                    if retry_count >= max_retries:
                        st.error(f"❌ 已达到最大重试次数（{max_retries}次），请检查API配置或网络连接")
                    else:
                        if st.button("🔄 重新评分", use_container_width=True, key="retry_score",
                                   disabled=(not st.session_state.cfg_valid) or (gen_llm is None)):
                            with st.spinner("正在重新评分..."):
                                try:
                                    retry_scorer = ContentScorer()
                                    score_chain = PromptTemplate.from_template("{input}") | gen_llm | StrOutputParser()
                                    new_score = retry_scorer.score_content(
                                        item["content"], brand, advantages, item["platform"], score_chain
                                    )
                                    item["score"] = new_score
                                    content_key = f"{item['keyword']}_{item['platform']}"
                                    st.session_state.content_scores[content_key] = new_score
                                    st.session_state.generated_contents[selected_idx] = item
                                    st.session_state[retry_count_key] = 0
                                    st.success("✅ 重新评分成功！")
                                    st.rerun()
                                except Exception as e:
                                    st.session_state[retry_count_key] = retry_count + 1
                                    error_msg = str(e)
                                    if "timeout" in error_msg.lower() or "connection" in error_msg.lower():
                                        error_type = "网络连接错误"
                                    elif "api" in error_msg.lower() or "key" in error_msg.lower() or "auth" in error_msg.lower():
                                        error_type = "API配置错误"
                                        st.error(f"❌ {error_type}：{error_msg}。请检查API配置。")
                                    else:
                                        error_type = "评分失败"
                                        st.error(f"重新评分失败（{retry_count + 1}/{max_retries}）：{error_msg}")
                else:
                    temp_scorer = ContentScorer()
                    scores = score_data.get("scores", {})
                    total_score = scores.get("total", 0)
                    level, color = temp_scorer.get_score_level(total_score)
                    st.markdown("##### 📊 内容质量评分")
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
                    with st.expander("📝 详细评分与改进建议", expanded=False):
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
            else:
                st.info("💡 内容未评分，点击下方按钮进行评估")
                if st.button("📊 评估内容质量", use_container_width=True, key="assess_content_quality",
                           disabled=(not st.session_state.cfg_valid) or (gen_llm is None)):
                    with st.spinner("正在评估内容质量..."):
                        try:
                            assess_scorer = ContentScorer()
                            score_chain = PromptTemplate.from_template("{input}") | gen_llm | StrOutputParser()
                            score_data = assess_scorer.score_content(
                                item["content"], brand, advantages, item["platform"], score_chain
                            )
                            item["score"] = score_data
                            content_key = f"{item['keyword']}_{item['platform']}"
                            st.session_state.content_scores[content_key] = score_data
                            st.session_state.generated_contents[selected_idx] = item
                            st.success("✅ 评估完成！")
                            st.rerun()
                        except Exception as e:
                            st.error(f"评估失败：{e}")

            with st.expander("🎯 E-E-A-T 评估", expanded=False):
                content_eeat_key = f"content_eeat_{item['keyword']}_{item['platform']}"
                ss_init(content_eeat_key, None)
                ss_init(f"{content_eeat_key}_enhanced", "")
                ss_init(f"{content_eeat_key}_placeholders", [])

                eeat_col1, eeat_col2 = st.columns(2)
                with eeat_col1:
                    assess_content_eeat = st.button("📊 评估 E-E-A-T",
                                                   disabled=(not st.session_state.cfg_valid) or (gen_llm is None),
                                                   key="content_assess_eeat_detail", use_container_width=True)
                with eeat_col2:
                    enhance_content_eeat = st.button("✨ 强化 E-E-A-T",
                                                    disabled=(not st.session_state.cfg_valid) or (gen_llm is None),
                                                    key="content_enhance_eeat_detail", use_container_width=True)

                if assess_content_eeat and gen_llm:
                    eeat_enhancer = EEATEnhancer()
                    with st.spinner("正在评估 E-E-A-T..."):
                        try:
                            score_chain = PromptTemplate.from_template("{input}") | gen_llm | StrOutputParser()
                            assessment = eeat_enhancer.assess_eeat(
                                item["content"], brand, advantages, item["platform"], score_chain
                            )
                            st.session_state[content_eeat_key] = assessment
                            st.success("✅ E-E-A-T 评估完成！")
                        except Exception as e:
                            st.error(f"E-E-A-T 评估失败：{e}")

                if enhance_content_eeat and gen_llm:
                    eeat_enhancer = EEATEnhancer()
                    with st.spinner("正在强化 E-E-A-T..."):
                        try:
                            enhance_chain = PromptTemplate.from_template("{input}") | gen_llm | StrOutputParser()
                            enhanced = eeat_enhancer.enhance_eeat(
                                item["content"], brand, advantages, item["platform"], enhance_chain
                            )
                            st.session_state[f"{content_eeat_key}_enhanced"] = enhanced.get("enhanced_content", "")
                            st.session_state[f"{content_eeat_key}_placeholders"] = enhanced.get("source_placeholders", [])
                            item["content"] = st.session_state[f"{content_eeat_key}_enhanced"]
                            st.success(f"✅ E-E-A-T 强化完成！已添加 {len(st.session_state[f'{content_eeat_key}_placeholders'])} 个来源占位")
                            st.rerun()
                        except Exception as e:
                            st.error(f"E-E-A-T 强化失败：{e}")

                if st.session_state.get(content_eeat_key):
                    assessment = st.session_state[content_eeat_key]
                    scores = assessment.get("eeat_scores", {})
                    total_score = scores.get("total", 0)
                    eeat_enhancer = EEATEnhancer()
                    level, color = eeat_enhancer.get_eeat_level(total_score)
                    st.markdown("**📊 E-E-A-T 评估结果**")
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

            with st.expander("📊 事实密度评估", expanded=False):
                content_fact_key = f"content_fact_{item['keyword']}_{item['platform']}"
                ss_init(content_fact_key, None)
                ss_init(f"{content_fact_key}_enhanced", "")
                ss_init(f"{content_fact_key}_details", [])

                fact_col1, fact_col2 = st.columns(2)
                with fact_col1:
                    assess_fact_density = st.button("📊 评估事实密度",
                                                   disabled=(not st.session_state.cfg_valid) or (gen_llm is None),
                                                   key="content_assess_fact_detail", use_container_width=True)
                with fact_col2:
                    enhance_fact_density = st.button("✨ 强化事实密度",
                                                    disabled=(not st.session_state.cfg_valid) or (gen_llm is None),
                                                    key="content_enhance_fact_detail", use_container_width=True)

                if assess_fact_density and gen_llm:
                    fact_enhancer = FactDensityEnhancer()
                    with st.spinner("正在评估事实密度和结构化块..."):
                        try:
                            score_chain = PromptTemplate.from_template("{input}") | gen_llm | StrOutputParser()
                            assessment = fact_enhancer.assess_fact_density(
                                item["content"], brand, advantages, item["platform"], score_chain
                            )
                            st.session_state[content_fact_key] = assessment
                            st.success("✅ 事实密度评估完成！")
                        except Exception as e:
                            st.error(f"事实密度评估失败：{e}")

                if enhance_fact_density and gen_llm:
                    fact_enhancer = FactDensityEnhancer()
                    with st.spinner("正在强化事实密度和结构化块..."):
                        try:
                            enhance_chain = PromptTemplate.from_template("{input}") | gen_llm | StrOutputParser()
                            enhanced = fact_enhancer.enhance_fact_density(
                                item["content"], brand, advantages, item["platform"], enhance_chain
                            )
                            st.session_state[f"{content_fact_key}_enhanced"] = enhanced.get("enhanced_content", "")
                            st.session_state[f"{content_fact_key}_details"] = enhanced.get("enhancement_details", [])
                            item["content"] = st.session_state[f"{content_fact_key}_enhanced"]
                            st.success(f"✅ 事实密度强化完成！已添加 {len(st.session_state[f'{content_fact_key}_details'])} 处事实信息和结构化块")
                            st.rerun()
                        except Exception as e:
                            st.error(f"事实密度强化失败：{e}")

                if st.session_state.get(content_fact_key):
                    assessment = st.session_state[content_fact_key]
                    scores = assessment.get("scores", {})
                    total_score = scores.get("total", 0)
                    fact_enhancer = FactDensityEnhancer()
                    level, color = fact_enhancer.get_score_level(total_score)
                    st.markdown("**📊 事实密度 + 结构化评估结果**")
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.metric("总分", f"{total_score}/100", delta=level, delta_color="off")
                    with col2:
                        st.metric("事实密度", f"{scores.get('fact_density', 0)}/50")
                    with col3:
                        st.metric("结构化", f"{scores.get('structure', 0)}/50")

        with detail_tab3:
            st.markdown("#### 🎨 多模态增强")
            tongyi_api_key = st.session_state.cfg.get("tongyi_wanxiang_api_key", "")

            if not tongyi_api_key:
                st.info("💡 提示：请在侧边栏配置中设置通义万相 API Key 以使用图片生成功能。")
            else:
                image_gen_mode = st.radio(
                    "图片生成方式",
                    ["智能生成（推荐）", "基于配图描述生成"],
                    horizontal=True,
                    key=f"image_gen_mode_{item.get('keyword', '')}",
                    help="智能生成：AI自动分析内容生成图片；基于描述：使用已生成的配图描述"
                )
                num_images = st.selectbox(
                    "生成数量",
                    [1, 2, 3],
                    index=0,
                    key=f"num_images_{item.get('keyword', '')}",
                    help="建议：小红书3-5张，知乎2-3张，公众号2-4张"
                )
                direct_gen_key = f"direct_image_gen_main_{item.get('keyword', '')}"
                ss_init(direct_gen_key, {})
                ss_init(f"{direct_gen_key}_generated", False)
                ss_init(f"{direct_gen_key}_images", [])
                ss_init(f"{direct_gen_key}_final_content", "")

                if image_gen_mode == "智能生成（推荐）":
                    if st.button("🎨 生成图片", use_container_width=True, type="primary",
                               key=f"generate_images_smart_{item.get('keyword', '')}",
                               disabled=(not st.session_state.cfg_valid) or (gen_llm is None) or (not tongyi_api_key)):
                        multimodal_gen = MultimodalPromptGenerator()
                        content = item.get("content", "")
                        progress_bar_img = st.progress(0)
                        status_text_img = st.empty()
                        status_text_img.text(f"正在生成 {num_images} 张配图，请稍候（每张约需 5-15 秒）...")
                        try:
                            multimodal_chain = PromptTemplate.from_template("{input}") | gen_llm | StrOutputParser()
                            generated_images = []
                            for idx in range(num_images):
                                progress = (idx + 1) / num_images
                                progress_bar_img.progress(progress)
                                status_text_img.text(f"正在生成第 {idx + 1}/{num_images} 张图片...")
                                if num_images == 1:
                                    content_segment = content[:800] if len(content) > 800 else content
                                elif num_images == 2:
                                    content_segment = content[:500] if idx == 0 else content[-500:] if len(content) > 500 else content
                                else:
                                    if idx == 0:
                                        content_segment = content[:400] if len(content) > 400 else content
                                    elif idx == 1:
                                        mid_start = len(content) // 3
                                        mid_end = mid_start + 400
                                        content_segment = content[mid_start:mid_end] if len(content) > mid_end else content[mid_start:]
                                    else:
                                        content_segment = content[-400:] if len(content) > 400 else content
                                try:
                                    image_prompt = multimodal_gen.generate_tongyi_image_prompt(
                                        content_segment, brand, multimodal_chain,
                                    )
                                    if not image_prompt or not image_prompt.strip():
                                        image_prompt = f"一张关于{content_segment[:50]}的专业配图，风格：高清、现代、科技感，品牌：{brand}"
                                except Exception as e:
                                    image_prompt = f"一张关于{content_segment[:50]}的专业配图，风格：高清、现代、科技感，品牌：{brand}"
                                platform = item.get("platform", "")
                                image_size = MultimodalPromptGenerator.get_image_size_for_platform(platform)
                                try:
                                    if not image_prompt or not image_prompt.strip():
                                        raise ValueError("图片生成 Prompt 为空，请检查内容或重试")
                                    result = multimodal_gen.generate_image_with_tongyi(
                                        prompt=image_prompt,
                                        api_key=tongyi_api_key,
                                        model="wanx-v1",
                                        size=image_size,
                                    )
                                    if result is None:
                                        raise ValueError("图片生成 API 返回空结果")
                                    if result.get("success") and result.get("image_url"):
                                        generated_images.append({
                                            "image_url": result["image_url"],
                                            "prompt": image_prompt,
                                            "alt_text": f"配图 {idx + 1}",
                                            "position": f"位置 {idx + 1}",
                                            "description": {},
                                        })
                                        st.success(f"✅ 第 {idx + 1} 张图片生成成功")
                                    else:
                                        st.error(f"❌ 第 {idx + 1} 张图片生成失败：{result.get('error', '未知错误')}")
                                except Exception as e:
                                    st.error(f"❌ 第 {idx + 1} 张图片生成异常：{str(e)}")
                            if generated_images:
                                final_content = multimodal_gen.embed_images_in_markdown(content, generated_images)
                                st.session_state[f"{direct_gen_key}_images"] = generated_images
                                st.session_state[f"{direct_gen_key}_final_content"] = final_content
                                st.session_state[f"{direct_gen_key}_generated"] = True
                                st.success(f"✅ 成功生成 {len(generated_images)} 张图片并嵌入文章！")
                            else:
                                st.warning("⚠️ 未成功生成任何图片")
                            progress_bar_img.empty()
                            status_text_img.empty()
                        except Exception as e:
                            st.error(f"图片生成失败：{e}")
                            if 'progress_bar_img' in locals():
                                progress_bar_img.empty()
                            if 'status_text_img' in locals():
                                status_text_img.empty()

                    if st.session_state.get(f"{direct_gen_key}_generated", False):
                        generated_images = st.session_state.get(f"{direct_gen_key}_images", [])
                        final_content = st.session_state.get(f"{direct_gen_key}_final_content", "")
                        if generated_images:
                            st.markdown("##### 📸 生成的图片预览")
                            for idx, img_data in enumerate(generated_images, 1):
                                with st.expander(f"图片 {idx}：{img_data.get('alt_text', '配图')}", expanded=(idx == 1)):
                                    st.image(img_data["image_url"], caption=img_data.get("prompt", "")[:100])
                                    st.markdown(f"**Prompt**：{img_data.get('prompt', '')}")
                                    st.markdown(f"**图片URL**：{img_data['image_url']}")
                            st.markdown("---")
                            st.markdown("##### 📄 图文结合版本（Markdown）")
                            st.code(final_content, language="markdown")
                            st.download_button(
                                label="📥 下载图文结合版本（.md）",
                                data=final_content,
                                file_name=f"{item.get('keyword', 'content')}_with_images.md",
                                mime="text/markdown",
                                use_container_width=True,
                                key=f"download_final_content_{item.get('keyword', '')}"
                            )
                            if st.button("🔄 用图文版本替换原内容", use_container_width=True,
                                       key=f"update_content_main_{item.get('keyword', '')}"):
                                item["content"] = final_content
                                st.session_state.generated_contents[selected_idx] = item
                                st.success("✅ 内容已更新为图文结合版本")

                image_gen_key = f"image_gen_{item.get('keyword', '')}"
                ss_init(image_gen_key, {})
                ss_init(f"{image_gen_key}_generated", False)
                ss_init(f"{image_gen_key}_images", [])
                ss_init(f"{image_gen_key}_final_content", "")

                if image_gen_mode == "基于配图描述生成":
                    if "multimodal_descriptions" not in st.session_state:
                        st.session_state.multimodal_descriptions = {}
                    multimodal_key = item.get("keyword", "")
                    if multimodal_key in st.session_state.multimodal_descriptions:
                        multimodal_data = st.session_state.multimodal_descriptions[multimodal_key]
                        if multimodal_data.get("type") == "image":
                            descriptions = multimodal_data.get("descriptions", {})
                            image_list = descriptions.get("image_descriptions", [])
                            if image_list and st.button("🎨 基于描述生成", use_container_width=True, type="primary",
                                   key=f"generate_images_desc_{item.get('keyword', '')}",
                                   disabled=(not st.session_state.cfg_valid) or (gen_llm is None) or (not tongyi_api_key)):
                                multimodal_gen = MultimodalPromptGenerator()
                                content = item.get("content", "")
                                progress_bar_img = st.progress(0)
                                status_text_img = st.empty()
                                try:
                                    multimodal_chain = PromptTemplate.from_template("{input}") | gen_llm | StrOutputParser()
                                    generated_images = []
                                    for idx, desc in enumerate(image_list):
                                        progress = (idx + 1) / len(image_list)
                                        progress_bar_img.progress(progress)
                                        status_text_img.text(f"正在生成第 {idx + 1}/{len(image_list)} 张图片...")
                                        image_prompt = desc.get('detailed_description', desc.get('image_description', ''))
                                        if not image_prompt:
                                            image_prompt = multimodal_gen.generate_tongyi_image_prompt(
                                                content, brand, multimodal_chain
                                            )
                                        platform = item.get("platform", "")
                                        image_size = MultimodalPromptGenerator.get_image_size_for_platform(platform)
                                        try:
                                            result = multimodal_gen.generate_image_with_tongyi(
                                                prompt=image_prompt,
                                                api_key=tongyi_api_key,
                                                model="wanx-v1",
                                                size=image_size
                                            )
                                            if result and result.get("success") and result.get("image_url"):
                                                generated_images.append({
                                                    "image_url": result["image_url"],
                                                    "prompt": image_prompt,
                                                    "alt_text": desc.get('original_hint', f"配图 {idx + 1}"),
                                                    "position": desc.get('position', ''),
                                                    "description": desc
                                                })
                                                st.success(f"✅ 第 {idx + 1} 张图片生成成功")
                                        except Exception as e:
                                            st.error(f"❌ 第 {idx + 1} 张图片生成异常：{str(e)}")
                                    progress_bar_img.empty()
                                    status_text_img.empty()
                                    if generated_images:
                                        final_content = multimodal_gen.embed_images_in_markdown(content, generated_images)
                                        st.session_state[f"{image_gen_key}_images"] = generated_images
                                        st.session_state[f"{image_gen_key}_final_content"] = final_content
                                        st.session_state[f"{image_gen_key}_generated"] = True
                                        st.success(f"✅ 成功生成 {len(generated_images)} 张图片并嵌入文章！")
                                except Exception as e:
                                    st.error(f"图片生成失败：{e}")
                        else:
                            st.info("💡 请先生成配图描述")
                    else:
                        st.info("💡 请先生成配图描述")
                        if st.button("📝 生成配图描述", use_container_width=True,
                                   key=f"generate_desc_{item.get('keyword', '')}",
                                   disabled=(not st.session_state.cfg_valid) or (gen_llm is None)):
                            multimodal_gen = MultimodalPromptGenerator()
                            content = item.get("content", "")
                            platform = item.get("platform", "")
                            try:
                                multimodal_chain = PromptTemplate.from_template("{input}") | gen_llm | StrOutputParser()
                                with st.spinner("正在生成配图描述..."):
                                    image_descriptions = multimodal_gen.generate_batch_image_descriptions(
                                        content, brand, advantages, platform,
                                        item.get("keyword", ""), multimodal_chain
                                    )
                                    if image_descriptions and image_descriptions.get("total_images", 0) > 0:
                                        if "multimodal_descriptions" not in st.session_state:
                                            st.session_state.multimodal_descriptions = {}
                                        st.session_state.multimodal_descriptions[item.get("keyword", "")] = {
                                            "type": "image",
                                            "descriptions": image_descriptions
                                        }
                                        st.success(f"✅ 配图描述生成完成！共 {image_descriptions.get('total_images', 0)} 个配图")
                                    else:
                                        st.warning("⚠️ 未生成任何配图描述。")
                            except Exception as e:
                                st.error(f"配图描述生成失败：{e}")

            if "B站" in item["platform"]:
                st.markdown("---")
                st.markdown("#### 🎬 视频脚本生成")
                if st.button("🎬 生成视频脚本", use_container_width=True,
                            key=f"generate_video_script_{item.get('keyword', '')}",
                            disabled=(not st.session_state.cfg_valid) or (gen_llm is None)):
                    multimodal_gen = MultimodalPromptGenerator()
                    content = item.get("content", "")
                    with st.spinner("正在生成视频脚本..."):
                        try:
                            multimodal_chain = PromptTemplate.from_template("{input}") | gen_llm | StrOutputParser()
                            segments = content.split('\n\n')[:5]
                            video_scripts = []
                            for i, segment in enumerate(segments):
                                if segment.strip():
                                    timestamp = f"00:{i*10:02d}-00:{(i+1)*10:02d}"
                                    script = multimodal_gen.generate_video_script_description(
                                        segment, brand, advantages, item.get("keyword", ""),
                                        timestamp, multimodal_chain
                                    )
                                    video_scripts.append({"timestamp": timestamp, "script": script})
                            if "multimodal_descriptions" not in st.session_state:
                                st.session_state.multimodal_descriptions = {}
                            st.session_state.multimodal_descriptions[item.get("keyword", "")] = {
                                "type": "video",
                                "scripts": video_scripts
                            }
                            st.success(f"✅ 视频脚本描述生成完成！共 {len(video_scripts)} 个片段")
                            st.rerun()
                        except Exception as e:
                            st.error(f"视频脚本生成失败：{e}")
                if "multimodal_descriptions" not in st.session_state:
                    st.session_state.multimodal_descriptions = {}
                multimodal_key = item.get("keyword", "")
                if multimodal_key in st.session_state.multimodal_descriptions:
                    multimodal_data = st.session_state.multimodal_descriptions[multimodal_key]
                    if multimodal_data.get("type") == "video":
                        scripts = multimodal_data.get("scripts", [])
                        if scripts:
                            st.markdown("##### 🎬 视频脚本描述详情")
                            for script_item in scripts:
                                timestamp = script_item.get("timestamp", "N/A")
                                script = script_item.get("script", {})
                                with st.expander(f"片段：{timestamp}", expanded=False):
                                    st.markdown(f"**画面描述**：{script.get('scene_description', 'N/A')}")
                                    col1, col2, col3 = st.columns(3)
                                    with col1:
                                        st.markdown(f"**镜头类型**：{script.get('shot_type', 'N/A')}")
                                    with col2:
                                        st.markdown(f"**镜头运动**：{script.get('camera_movement', 'N/A')}")
                                    with col3:
                                        st.markdown(f"**转场**：{script.get('transition', 'N/A')}")
                                    st.markdown(f"**音效建议**：{script.get('audio_suggestion', 'N/A')}")

        if len(st.session_state.generated_contents) > 1 and st.session_state.zip_bytes:
            st.markdown("---")
            st.download_button(
                "📦 下载所有内容ZIP",
                st.session_state.zip_bytes,
                st.session_state.zip_filename,
                "application/zip",
                use_container_width=True,
                key="content_dl_zip_bottom"
            )
