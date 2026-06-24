"""
全局配置模块 —— 管理 API 密钥、模型参数、默认值。
密钥由 .env 文件加载，开发者预填，用户无需感知。
"""

import os
from dotenv import load_dotenv

load_dotenv()

# ─── LLM 配置 ───────────────────────────────────────────
LLM_API_KEY = os.getenv("LLM_API_KEY", "your-deepseek-api-key-here")
LLM_BASE_URL = os.getenv("LLM_BASE_URL", "https://api.deepseek.com/v1")
LLM_MODEL = os.getenv("LLM_MODEL", "deepseek-chat")
LLM_TEMPERATURE = 0.7
LLM_MAX_TOKENS = 4096

# ─── 嵌入模型配置 ───────────────────────────────────────
# 使用 sklearn HashingVectorizer，完全本地运行，无需下载任何模型
EMBEDDING_DIM = int(os.getenv("EMBEDDING_DIM", "384"))

# ─── Chroma 配置 ────────────────────────────────────────
CHROMA_PERSIST_DIR = os.getenv("CHROMA_PERSIST_DIR", "./chroma_db")

# ─── 章节默认值 ─────────────────────────────────────────
DEFAULT_WORD_COUNT = 3000
MIN_WORD_COUNT = 500
MAX_WORD_COUNT = 10000
WORD_COUNT_STEP = 500

# ─── 文风模板 ──────────────────────────────────────────
STYLE_TEMPLATES = {
    "爽文": "节奏明快、爽点密集、主角强势、打脸反转频繁，语言通俗直白，情绪张力强",
    "古风": "文辞典雅、意境深远、对白半文半白，注重氛围渲染和意蕴表达",
    "都市": "语言生活化、贴近现实、对话自然流畅，注重细节描写和人物心理刻画",
    "悬疑": "叙事紧凑、悬念迭起、细节伏笔丰富，氛围压抑神秘，逻辑推理严谨",
}

# ─── Agent 提示词前缀 ───────────────────────────────────
AGENT_SYSTEM_PREFIX = "你是一个专业的网络小说创作AI智能体，隶属于「AI Agent全自动小说创作系统」。"
