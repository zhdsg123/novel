# AI Agent 全自动小说创作系统

> 一键生成完整小说 · AI 智能连载 · 剧情永不崩坏

面向小说创作者的全自动 AI 多智能体写作工具。内置 4 个专业 AI Agent 流水线协作，搭载 RAG 长效记忆，支持百万字长篇稳定续写。

---

## 快速开始

### 1. 环境要求
- Python 3.10+
- DeepSeek API Key（[免费注册获取](https://platform.deepseek.com/api_keys)）

### 2. 安装

```bash
# 克隆项目
git clone <repo-url>
cd 小说ai

# 安装依赖
pip install -r requirements.txt

# 配置密钥
cp .env.example .env
# 编辑 .env 文件，填入你的 DeepSeek API Key
```

### 3. 启动

```bash
streamlit run app.py
```

浏览器打开 `http://localhost:8501`，输入小说题材和剧情需求，点击「一键全自动写作」。

---

## 功能

| 功能 | 说明 |
|------|------|
| 🚀 一键生成 | 输入题材+剧情+字数，AI 全自动完成世界观→人物→章节→校验→润色 |
| 🧠 长效记忆 | Chroma 本地向量库，百万字连载人设/战力/剧情不崩坏 |
| 🔄 智能续写 | 导入旧文，AI 永久记忆设定，续写无缝衔接 |
| 🎨 文风锁定 | 内置爽文/古风/都市/悬疑模板，全程统一风格 |
| 🔍 剧情自检 | 每章自动检测战力崩坏/人设矛盾/剧情冲突/时间线错误 |
| 📥 成品导出 | 一键导出 TXT，一键复制全文 |

## 架构

```
用户输入 → 世界观设定Agent → 人物塑造Agent → 章节创作Agent → 校验润色Agent → 成品输出
                              ↕
                        Chroma 向量知识库 (RAG)
```

- **UI**: Streamlit
- **Agent 编排**: LangGraph
- **向量记忆**: ChromaDB + sklearn HashingVectorizer（完全离线）
- **LLM**: DeepSeek API（兼容 OpenAI 接口，可替换）

## 项目结构

```
├── app.py                  # Streamlit 主界面
├── src/
│   ├── agents/             # 4 个 AI Agent
│   │   ├── world_builder.py
│   │   ├── character_designer.py
│   │   ├── chapter_writer.py
│   │   └── proofreader.py
│   ├── workflow/graph.py   # LangGraph 流水线
│   ├── memory/vector_store.py  # Chroma RAG 记忆
│   ├── llm/client.py       # LLM API 客户端
│   └── config.py           # 全局配置
├── requirements.txt
├── .env.example            # 密钥配置模板
└── .streamlit/config.toml  # 主题配置
```

## 许可

MIT License
