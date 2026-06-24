"""
Agent 3: 章节创作智能体（核心模块）
联动 RAG 记忆库，结合用户需求，自主撰写高质量网文章节。
支持文风锁定、字数控制、剧情伏笔回收。
"""

from src.config import AGENT_SYSTEM_PREFIX, STYLE_TEMPLATES

CHAPTER_WRITER_SYSTEM = """{prefix}你是一位资深网络小说作家，文笔流畅，擅长各类题材创作。

## 你的写作信条
1. **节奏为王**：每章必须有爽点/冲突/转折，拒绝平淡流水账
2. **人物立体**：角色的言行必须符合其性格设定，杜绝OOC
3. **伏笔意识**：有意埋下可回收的伏笔，也要回收已有伏笔
4. **沉浸感强**：通过细节描写、心理刻画让读者身临其境
5. **衔接自然**：与前后章节保持逻辑连贯、设定一致

## 当前写作风格要求
{style_requirement}

## 写作规范
- 适当使用对话推进剧情
- 每500-800字应有节奏变化（紧张→舒缓→紧张）
- 章节结尾留有悬念或期待感
- 保持与已有设定的严格一致性

## 字数要求
目标字数：{target_words} 字（请尽量接近，允许 ±10% 浮动）"""

CHAPTER_WRITER_USER = """请根据以下信息撰写本章内容：

【小说题材】
{genre}

【本章剧情需求】
{plot_requirements}

【当前世界观设定】
{world_setting}

【人物角色档案】
{characters}

【已有剧情上下文（RAG记忆检索）】
{context}

## 请开始撰写本章正文
直接输出章节正文内容（无需"以下是章节内容"等引导词），使用自然段落，适当分段。"""


def build_chapter_system_prompt(style: str, target_words: int) -> str:
    """构建章节创作的系统提示词。"""
    style_desc = STYLE_TEMPLATES.get(style, STYLE_TEMPLATES["爽文"])
    return CHAPTER_WRITER_SYSTEM.format(
        prefix=AGENT_SYSTEM_PREFIX,
        style_requirement=f"【{style}】风格要求：{style_desc}",
        target_words=target_words,
    )


def build_chapter_user_prompt(
    genre: str,
    plot_requirements: str,
    world_setting: str,
    characters: str,
    context: str,
) -> str:
    """构建章节创作的用户提示词。"""
    context_display = context if context else "（全新小说，暂无上下文）"
    return CHAPTER_WRITER_USER.format(
        genre=genre,
        plot_requirements=plot_requirements,
        world_setting=world_setting if world_setting else "（根据题材自由发挥）",
        characters=characters if characters else "（根据题材塑造）",
        context=context_display,
    )
