"""
LangGraph 多智能体工作流
编排 4 个 Agent 的流水线执行：世界观 → 人物 → 章节 → 校验润色
支持新创作模式和续写模式的自动切换。
"""

from typing import TypedDict, Optional
from langgraph.graph import StateGraph, END

from src.llm.client import LLMClient
from src.memory.vector_store import NovelMemoryStore
from src.agents.world_builder import WORLD_BUILDER_PROMPT, build_world_prompt
from src.agents.character_designer import CHARACTER_DESIGNER_PROMPT, build_character_prompt
from src.agents.chapter_writer import (
    build_chapter_system_prompt,
    build_chapter_user_prompt,
)
from src.agents.proofreader import (
    build_proofreader_system,
    build_proofreader_user,
    build_plotline_extraction_prompt,
)
from src.config import AGENT_SYSTEM_PREFIX


# ─── State 定义 ────────────────────────────────────────

class NovelState(TypedDict):
    """小说创作流水线的全局状态。"""
    # ── 用户输入 ──
    genre: str
    plot_requirements: str
    target_word_count: int
    existing_text: str
    style: str
    is_continuation: bool

    # ── Agent 产出 ──
    world_setting: str
    characters: str
    chapter_content: str
    polished_chapter: str
    verification_report: str

    # ── 流程控制 ──
    current_step: str
    progress_log: list[str]
    error: str


# ─── 工作流构建 ────────────────────────────────────────

class NovelCreationWorkflow:
    """小说创作工作流，封装 LangGraph 流水线的构建与执行。"""

    def __init__(self):
        self.llm = LLMClient()
        self.memory = NovelMemoryStore()
        self.graph = self._build_graph()

    def _build_graph(self) -> StateGraph:
        """构建 LangGraph StateGraph。"""
        workflow = StateGraph(NovelState)

        # 注册节点
        workflow.add_node("build_world", self._node_build_world)
        workflow.add_node("design_characters", self._node_design_characters)
        workflow.add_node("write_chapter", self._node_write_chapter)
        workflow.add_node("proofread", self._node_proofread)

        # 设置入口：根据是否续写选择不同路径
        workflow.set_conditional_entry_point(
            self._route_entry,
            {
                "build_world": "build_world",
                "write_chapter": "write_chapter",
            },
        )

        # 设置边
        workflow.add_edge("build_world", "design_characters")
        workflow.add_edge("design_characters", "write_chapter")
        workflow.add_edge("write_chapter", "proofread")
        workflow.add_edge("proofread", END)

        return workflow.compile()

    def _route_entry(self, state: NovelState) -> str:
        """根据是否续写选择入口节点。"""
        if state.get("is_continuation") and state.get("existing_text"):
            state["current_step"] = "续写模式：从RAG记忆检索已有设定，直接进入章节创作"
            state["progress_log"] = [state["current_step"]]
            # 导入旧文到记忆库
            self.memory.import_existing_novel(
                state["existing_text"],
                metadata={"source": "user_import"},
            )
            # 检索已有设定填充 state
            context = self.memory.build_context_prompt(state["plot_requirements"])
            state["world_setting"] = self.memory.query_world_settings(
                state["plot_requirements"], n_results=3
            )
            state["characters"] = self.memory.query_characters(
                state["plot_requirements"], n_results=5
            )
            return "write_chapter"
        else:
            state["current_step"] = "新书模式：从世界观设定开始完整创作流程"
            state["progress_log"] = [state["current_step"]]
            return "build_world"

    # ─── Node 1: 世界观设定 ─────────────────────────

    def _node_build_world(self, state: NovelState) -> NovelState:
        """Agent 1: 生成世界观设定。"""
        self._log(state, "🌍 Agent 1/4: 正在构建世界观设定...")

        world = self.llm.chat(
            system_prompt=WORLD_BUILDER_PROMPT.format(prefix=AGENT_SYSTEM_PREFIX),
            user_prompt=build_world_prompt(
                state["genre"], state["plot_requirements"]
            ),
        )

        state["world_setting"] = world
        self.memory.add_world_setting(world, metadata={"genre": state["genre"]})
        self._log(state, "✅ 世界观设定完成，已存入记忆库")
        return state

    # ─── Node 2: 人物塑造 ───────────────────────────

    def _node_design_characters(self, state: NovelState) -> NovelState:
        """Agent 2: 生成人物角色档案。"""
        self._log(state, "👤 Agent 2/4: 正在塑造人物角色...")

        characters = self.llm.chat(
            system_prompt=CHARACTER_DESIGNER_PROMPT.format(prefix=AGENT_SYSTEM_PREFIX),
            user_prompt=build_character_prompt(
                state["genre"],
                state["plot_requirements"],
                state.get("world_setting", ""),
            ),
        )

        state["characters"] = characters
        self.memory.add_characters(characters, metadata={"genre": state["genre"]})
        self._log(state, "✅ 人物角色塑造完成，已存入记忆库")
        return state

    # ─── Node 3: 章节创作（核心）────────────────────

    def _node_write_chapter(self, state: NovelState) -> NovelState:
        """Agent 3: 撰写章节正文。"""
        self._log(
            state,
            f"✍️ Agent 3/4: 正在撰写章节正文（目标 {state['target_word_count']} 字，{state['style']} 风格）...",
        )

        # 从 RAG 检索上下文
        context = self.memory.build_context_prompt(state["plot_requirements"])

        chapter = self.llm.chat(
            system_prompt=build_chapter_system_prompt(
                state["style"], state["target_word_count"]
            ),
            user_prompt=build_chapter_user_prompt(
                state["genre"],
                state["plot_requirements"],
                state.get("world_setting", ""),
                state.get("characters", ""),
                context,
            ),
            max_tokens=8192,
        )

        state["chapter_content"] = chapter
        self.memory.add_chapter(chapter, metadata={
            "genre": state["genre"],
            "style": state["style"],
        })
        self._log(state, "✅ 章节初稿完成，进入校验润色...")
        return state

    # ─── Node 4: 校验与润色 ─────────────────────────

    def _node_proofread(self, state: NovelState) -> NovelState:
        """Agent 4: 剧情校验 + 文笔润色。"""
        self._log(state, "🔍 Agent 4/4: 正在进行剧情校验与文笔润色...")

        # 检索上下文用于校验
        context = self.memory.build_context_prompt(
            f"{state['genre']} {state['plot_requirements']}"
        )

        result = self.llm.chat(
            system_prompt=build_proofreader_system(),
            user_prompt=build_proofreader_user(
                state["genre"],
                state.get("world_setting", ""),
                state.get("characters", ""),
                context,
                state.get("chapter_content", ""),
            ),
            max_tokens=8192,
        )

        # 解析输出：分离润色后章节和校验报告
        polished, report = self._parse_proofread_result(result)
        state["polished_chapter"] = polished
        state["verification_report"] = report

        # 提取新伏笔存入记忆库
        self._extract_and_store_plotlines(state.get("chapter_content", ""))

        self._log(state, "✅ 全流程完成！成品章节已就绪。")
        return state

    # ─── 辅助方法 ────────────────────────────────────

    def _log(self, state: NovelState, message: str):
        """记录进度日志。"""
        state["current_step"] = message
        if "progress_log" not in state:
            state["progress_log"] = []
        state["progress_log"].append(message)

    def _parse_proofread_result(self, raw: str) -> tuple[str, str]:
        """
        解析 Agent 4 的输出，分离润色后章节和校验报告。
        支持多种标题格式（### / ## / 无#号）。
        """
        polished = raw
        report = ""

        # 章节标记（按优先级匹配）
        chapter_markers = [
            "### 【文笔润色后的成品章节】",
            "### 文笔润色后的成品章节",
            "【文笔润色后的成品章节】",
            "文笔润色后的成品章节",
            "## 【文笔润色后的成品章节】",
            "## 文笔润色后的成品章节",
            "### 润色后的成品章节",
            "润色后的成品章节",
        ]

        report_markers = [
            "### 【剧情校验报告】",
            "### 剧情校验报告",
            "【剧情校验报告】",
            "剧情校验报告",
            "## 【剧情校验报告】",
            "## 剧情校验报告",
        ]

        # 1. 先定位章节标记，提取章节内容
        for cm in chapter_markers:
            if cm in raw:
                parts = raw.split(cm, 1)
                if len(parts) == 2:
                    polished = parts[1]
                    break

        # 2. 在 polished 中寻找报告标记，切分报告
        for rm in report_markers:
            if rm in polished:
                chapter_parts = polished.split(rm, 1)
                polished = chapter_parts[0].strip()
                report = chapter_parts[1].strip() if len(chapter_parts) > 1 else ""
                break

        return polished.strip(), report.strip()

    def _extract_and_store_plotlines(self, chapter_content: str):
        """从章节中提取伏笔并存入记忆库。"""
        if not chapter_content:
            return
        system, user = build_plotline_extraction_prompt(chapter_content)
        try:
            plotlines = self.llm.chat(system_prompt=system, user_prompt=user)
            if plotlines and "无明显伏笔" not in plotlines:
                self.memory.add_plot_line(plotlines)
        except Exception:
            pass  # 伏笔提取非关键路径，静默失败

    # ─── 对外接口 ────────────────────────────────────

    def run(self, state: NovelState) -> NovelState:
        """
        执行完整的创作流水线。
        返回更新后的 NovelState。
        """
        try:
            result = self.graph.invoke(state)
            return result
        except Exception as e:
            state["error"] = str(e)
            state["current_step"] = f"❌ 创作流程出错: {e}"
            state["progress_log"].append(state["current_step"])
            return state

    def run_stream(self, state: NovelState):
        """
        流式执行创作流水线，每步 yield state 快照。
        用于 Streamlit 实时进度展示。
        """
        try:
            for step_output in self.graph.stream(state):
                yield step_output
        except Exception as e:
            state["error"] = str(e)
            state["current_step"] = f"❌ 创作流程出错: {e}"
            state["progress_log"].append(state["current_step"])
            yield {state["current_step"]: state}
