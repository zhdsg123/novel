"""
AI Agent 全自动小说创作系统
启动: streamlit run app.py
"""

import streamlit as st
from src.workflow.graph import NovelCreationWorkflow, NovelState
from src.memory.vector_store import NovelMemoryStore
from src.config import STYLE_TEMPLATES, DEFAULT_WORD_COUNT
from src.utils.text_utils import export_txt

# ─── 页面配置 ──────────────────────────────────────────

st.set_page_config(
    page_title="AI Agent 全自动小说创作系统",
    page_icon="📖",
    layout="wide",
)

# ─── CSS 样式系统 ──────────────────────────────────────

st.markdown("""
<style>
    /* ── 全局 ── */
    #MainMenu, footer, header { visibility: hidden; }
    * { scrollbar-width: thin; scrollbar-color: #444 #1a1a1a; }

    /* ── 顶部横幅 ── */
    .main-header {
        background: linear-gradient(135deg, #1a1a2e 0%, #16213e 50%, #0f3460 100%);
        border: 1px solid #2a2a4a;
        border-radius: 12px;
        padding: 1.6rem 2rem;
        margin-bottom: 1.2rem;
        text-align: center;
    }
    .main-header h1 {
        font-size: 1.8rem; font-weight: 700;
        background: linear-gradient(90deg, #a78bfa, #60a5fa);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
        margin-bottom: 0.3rem;
    }
    .main-header .subtitle { color: #8899aa; font-size: 0.88rem; letter-spacing: 0.05em; }

    /* ── 左侧面板 ── */
    .left-panel {
        background: #1a1a24;
        border: 1px solid #2a2a3a;
        border-radius: 12px;
        padding: 1.3rem;
    }
    .left-panel .section-title {
        color: #a78bfa;
        font-size: 0.8rem;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.08em;
        margin-bottom: 0.6rem;
    }
    .left-panel .divider {
        border: none; border-top: 1px solid #2a2a3a;
        margin: 1rem 0;
    }

    /* ── 统计卡片 ── */
    .stat-row {
        display: flex; gap: 0.5rem; margin-top: 0.5rem;
    }
    .stat-item {
        flex: 1; text-align: center;
        background: #222233; border-radius: 8px; padding: 0.5rem 0.3rem;
        border: 1px solid #2a2a3a;
    }
    .stat-item .stat-num { font-size: 1.2rem; font-weight: 700; color: #e0e0e0; }
    .stat-item .stat-label { font-size: 0.7rem; color: #777; margin-top: 0.1rem; }

    /* ── 内容卡片 ── */
    .chapter-card {
        background: #1a1a24;
        border: 1px solid #2a2a3a;
        border-radius: 12px;
        padding: 2rem 2.2rem;
        line-height: 2;
        font-size: 1.02rem;
        color: #d0d0d0;
        max-height: 62vh;
        overflow-y: auto;
        white-space: pre-wrap;
        font-family: 'Georgia', 'Noto Serif SC', 'SimSun', serif;
    }
    .report-card {
        background: #1a1a24;
        border: 1px solid #2a2a3a;
        border-left: 3px solid #f0a030;
        border-radius: 0 12px 12px 0;
        padding: 1.5rem 1.8rem;
        font-size: 0.92rem;
        color: #c0c0c0;
        white-space: pre-wrap;
    }

    /* ── 欢迎卡片 ── */
    .welcome-card {
        text-align: center; padding: 3rem 2rem;
        background: #1a1a24; border: 1px solid #2a2a3a;
        border-radius: 12px;
    }
    .welcome-card h3 { color: #aaa; font-weight: 500; margin-bottom: 0.8rem; }
    .welcome-card .flow-steps {
        display: flex; justify-content: center; gap: 0.6rem;
        flex-wrap: wrap; margin-top: 1rem;
    }
    .flow-steps span {
        background: #222233; color: #999; padding: 0.3rem 0.8rem;
        border-radius: 20px; font-size: 0.82rem; border: 1px solid #333;
    }
    .flow-steps span.active { background: #2d2d4a; color: #a78bfa; border-color: #4a4a6a; }

    /* ── 按钮微调 ── */
    .stButton > button {
        border-radius: 8px; font-weight: 600;
        transition: all 0.15s;
    }
    .stButton > button:hover {
        filter: brightness(1.1); transform: translateY(-1px);
    }

    /* ── 信息提示 ── */
    .stAlert { border-radius: 8px !important; }
</style>
""", unsafe_allow_html=True)

# ─── 顶部横幅 ──────────────────────────────────────────

st.markdown("""
<div class="main-header">
    <h1>AI Agent 全自动小说创作系统</h1>
    <div class="subtitle">一键生成完整小说 &nbsp;·&nbsp; AI 智能连载 &nbsp;·&nbsp; 剧情永不崩坏</div>
</div>
""", unsafe_allow_html=True)


# ─── 初始化 ────────────────────────────────────────────

@st.cache_resource
def get_store():
    return NovelMemoryStore()

@st.cache_resource
def get_wf():
    return NovelCreationWorkflow()

memory = get_store()

defaults = {
    "input_genre": "", "input_plot_req": "",
    "input_target_words": DEFAULT_WORD_COUNT,
    "input_style": "爽文", "input_existing_text": "",
    "chapter_content": "", "polished_chapter": "",
    "verification_report": "", "world_setting": "", "characters": "",
    "progress_log": [], "error": "",
    "trigger_generate": False,
}
for k, v in defaults.items():
    if k not in st.session_state:
        st.session_state[k] = v


# ─── 创作触发（在布局之前执行，避免 rerun 干扰） ──────

if st.session_state.trigger_generate:
    st.session_state.trigger_generate = False

    if not st.session_state.input_genre.strip():
        st.error("请先输入小说题材")
    elif not st.session_state.input_plot_req.strip():
        st.error("请先输入本章剧情需求")
    else:
        cont = bool(st.session_state.input_existing_text.strip())
        initial_state: NovelState = {
            "genre": st.session_state.input_genre.strip(),
            "plot_requirements": st.session_state.input_plot_req.strip(),
            "target_word_count": st.session_state.input_target_words,
            "existing_text": st.session_state.input_existing_text.strip() if cont else "",
            "style": st.session_state.input_style,
            "is_continuation": cont,
            "world_setting": st.session_state.world_setting,
            "characters": st.session_state.characters,
            "chapter_content": "", "polished_chapter": "",
            "verification_report": "", "current_step": "",
            "progress_log": [], "error": "",
        }

        try:
            wf = get_wf()
            steps = ["章节创作", "校验润色"] if cont else ["世界观设定", "人物塑造", "章节创作", "校验润色"]

            with st.status("🎬 AI 创作流水线启动中...", expanded=True) as status:
                idx = 0
                for output in wf.graph.stream(initial_state):
                    idx += 1
                    for _node, ns in output.items():
                        label = steps[min(idx - 1, len(steps) - 1)]
                        status.update(label=f"⚙️ 步骤 {idx}/{len(steps)}：{label}")
                        for f in ["world_setting", "characters", "chapter_content",
                                   "polished_chapter", "verification_report"]:
                            if ns.get(f):
                                st.session_state[f] = ns[f]
                        if ns.get("progress_log"):
                            st.session_state.progress_log = ns["progress_log"]
                            st.write("▸ " + ns["progress_log"][-1])
                status.update(label="✅ 全流程完成！", state="complete")
        except Exception as e:
            st.error(f"创作流程异常: {e}")

    st.rerun()


# ─── 双栏布局 ──────────────────────────────────────────

left, right = st.columns([1, 2.2], gap="medium")


# ═══════════════════════════════════════════════════════
# 左侧面板
# ═══════════════════════════════════════════════════════

with left:
    st.markdown('<div class="left-panel">', unsafe_allow_html=True)

    st.markdown('<div class="section-title">📝 创作设置</div>', unsafe_allow_html=True)

    st.text_input("小说题材", key="input_genre",
                  placeholder="玄幻修仙 / 都市异能 / 悬疑推理 ...")

    st.text_area("本章剧情需求", key="input_plot_req",
                 placeholder="描述本章核心情节，例如：主角在宗门大比中意外展露真实实力，震惊全场，获得进入秘境资格...",
                 height=85)

    st.slider("目标字数（字）", 500, 10000, key="input_target_words", step=500)

    st.selectbox("文风锁定", list(STYLE_TEMPLATES.keys()), key="input_style")

    st.text_area("导入旧文（续写专用）", key="input_existing_text",
                 placeholder="粘贴已有小说内容，留空则开启全新创作...", height=75,
                 help="AI 将自动解析并记忆旧文中的世界观、人物和伏笔")

    st.markdown('<div class="divider"></div>', unsafe_allow_html=True)

    c1, c2 = st.columns([1.2, 1])
    with c1:
        if st.button("🚀 一键全自动写作", type="primary", use_container_width=True, key="btn_start"):
            st.session_state.trigger_generate = True
    with c2:
        if st.button("↻ 重置显示", use_container_width=True, key="btn_reset"):
            for k in ["chapter_content", "polished_chapter", "verification_report",
                       "world_setting", "characters", "progress_log", "error"]:
                st.session_state[k] = "" if k != "progress_log" else []
            st.rerun()

    if st.button("🗑 清空记忆库 — 开始全新小说", use_container_width=True, key="btn_clear"):
        memory.clear_all()
        for k in ["chapter_content", "polished_chapter", "verification_report",
                   "world_setting", "characters", "progress_log", "error",
                   "input_genre", "input_plot_req", "input_existing_text"]:
            st.session_state[k] = "" if k != "progress_log" else []
        st.session_state.input_target_words = DEFAULT_WORD_COUNT
        st.session_state.input_style = "爽文"
        st.rerun()

    st.markdown('<div class="divider"></div>', unsafe_allow_html=True)
    st.markdown('<div class="section-title">💾 记忆库状态</div>', unsafe_allow_html=True)

    stats = memory.get_stats()
    st.markdown(f"""
    <div class="stat-row">
        <div class="stat-item"><div class="stat-num">{stats.get('world_settings',0)}</div><div class="stat-label">世界观</div></div>
        <div class="stat-item"><div class="stat-num">{stats.get('characters',0)}</div><div class="stat-label">人物</div></div>
        <div class="stat-item"><div class="stat-num">{stats.get('chapters',0)}</div><div class="stat-label">章节</div></div>
        <div class="stat-item"><div class="stat-num">{stats.get('plot_lines',0)}</div><div class="stat-label">伏笔</div></div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown('</div>', unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════
# 右侧面板
# ═══════════════════════════════════════════════════════

with right:

    # ── 结果展示 ──
    has_content = any([
        st.session_state.polished_chapter,
        st.session_state.chapter_content,
        st.session_state.verification_report,
        st.session_state.world_setting,
        st.session_state.characters,
    ])

    if has_content:
        t1, t2, t3 = st.tabs(["📖 成品章节", "🔍 校验报告", "🌍 设定档案"])

        with t1:
            display = st.session_state.polished_chapter or st.session_state.chapter_content
            if display:
                st.markdown(f'<div class="chapter-card">{display}</div>', unsafe_allow_html=True)
                st.markdown("")
                cc1, cc2 = st.columns(2)
                with cc1:
                    data, fname = export_txt(display)
                    st.download_button("📥 导出 TXT 文件", data=data, file_name=fname,
                                       mime="text/plain; charset=utf-8", use_container_width=True)
                with cc2:
                    if st.button("✏️ 继续写下一章", use_container_width=True, key="btn_continue",
                                 help="保留当前设定，在左侧输入新剧情后再次生成"):
                        st.session_state.input_plot_req = ""
                        st.info("请在左侧输入新章节的剧情需求，然后点击「一键全自动写作」")
            else:
                st.info("暂无章节内容，请点击左侧「一键全自动写作」开始创作")

        with t2:
            rpt = st.session_state.verification_report
            if rpt:
                st.markdown(f'<div class="report-card">{rpt}</div>', unsafe_allow_html=True)
            else:
                st.info("暂无校验报告")

        with t3:
            st.caption("💡 可直接编辑世界观和人物设定，内容自动存入记忆库，下次创作生效")

            w = st.text_area("🌍 世界观设定", value=st.session_state.world_setting,
                             height=220, key="edit_world",
                             placeholder="生成后此处显示世界观设定，可直接编辑...")
            if w != st.session_state.world_setting:
                st.session_state.world_setting = w
                memory.add_world_setting(w, {"source": "user_edit"})

            c = st.text_area("👤 人物角色档案", value=st.session_state.characters,
                             height=220, key="edit_chars",
                             placeholder="生成后此处显示人物档案，可直接编辑...")
            if c != st.session_state.characters:
                st.session_state.characters = c
                memory.add_characters(c, {"source": "user_edit"})

    else:
        st.markdown("""
        <div class="welcome-card">
            <h3>👈 在左侧面板输入创作需求，点击「一键全自动写作」</h3>
            <div class="flow-steps">
                <span>1. 世界观搭建</span>
                <span>→</span>
                <span>2. 人物塑造</span>
                <span>→</span>
                <span>3. 章节撰写</span>
                <span>→</span>
                <span>4. 校验润色</span>
                <span>→</span>
                <span class="active">✨ 成品输出</span>
            </div>
            <p style="color:#666; margin-top:1rem; font-size:0.85rem;">
                四大 AI 智能体流水线协作 · RAG 长效记忆百万字不崩坏 · 零配置开箱即用
            </p>
        </div>
        """, unsafe_allow_html=True)


# ─── 底部 ──────────────────────────────────────────────

st.markdown("---")
st.caption("AI Agent 全自动小说创作系统 v1.0  |  多智能体协同创作  |  本地记忆安全存储  |  用户零配置开箱即用")
