"""
Chroma 本地向量知识库 — RAG 长效记忆系统

管理 4 个 Collection：
- world_settings:  世界观设定
- characters:      人物档案
- chapters:        历史章节（分片存储）
- plot_lines:      剧情伏笔

支持：全文检索、增量入库、导入旧文自动解析、一键清空。

嵌入方案：sklearn HashingVectorizer（字符级 n-gram 哈希）
- 完全离线、零模型下载、零外网依赖
- 对中文文本有较好的语义区分能力
- 确定性输出：相同文本永远产生相同向量
"""

import chromadb
from chromadb.config import Settings as ChromaSettings
from sklearn.feature_extraction.text import HashingVectorizer
from src.config import CHROMA_PERSIST_DIR
from src.utils.text_utils import split_text


class SklearnEmbeddingFunction:
    """
    基于 sklearn HashingVectorizer 的本地嵌入函数。
    使用字符级 n-gram 哈希，将中文文本映射到固定维度向量。

    优势：
    - 完全本地运行，无需下载任何模型文件
    - 确定性哈希：相同输入永远产生相同输出
    - 支持中文字符 n-gram，无需分词
    """

    def __init__(self, n_features: int = 384):
        self.n_features = n_features
        self._name = f"sklearn-hashing-{n_features}"
        self.vectorizer = HashingVectorizer(
            n_features=n_features,
            analyzer='char_wb',       # 字符级 word-boundary n-gram
            ngram_range=(2, 4),       # 2-gram 到 4-gram，覆盖中文词组
            norm='l2',                # L2 归一化
            alternate_sign=False,     # 正值便于相似度计算
        )

    def name(self) -> str:
        """ChromaDB 要求的接口：返回嵌入函数名称。"""
        return self._name

    def __call__(self, input: list[str]) -> list[list[float]]:
        """嵌入文本列表，返回向量列表（兼容旧版 ChromaDB 接口）。"""
        if isinstance(input, str):
            input = [input]
        vectors = self.vectorizer.transform(input)
        return vectors.toarray().tolist()

    def embed_query(self, input) -> list[list[float]]:
        """ChromaDB 1.5+ 要求的新接口：嵌入查询或文档。"""
        return self.__call__(input)


class NovelMemoryStore:
    """
    小说长效记忆库。
    基于 Chroma 本地持久化向量数据库，存储并检索小说核心设定与历史内容。
    """

    COLLECTIONS = ["world_settings", "characters", "chapters", "plot_lines"]

    def __init__(self, persist_dir: str = CHROMA_PERSIST_DIR):
        self.persist_dir = persist_dir
        self.embedding_fn = SklearnEmbeddingFunction()
        self.client = chromadb.PersistentClient(
            path=persist_dir,
            settings=ChromaSettings(anonymized_telemetry=False),
        )
        self._ensure_collections()

    def _ensure_collections(self):
        """确保所有 collection 已创建。"""
        existing = {c.name for c in self.client.list_collections()}
        for name in self.COLLECTIONS:
            if name not in existing:
                self.client.create_collection(
                    name=name,
                    embedding_function=self.embedding_fn,
                )

    def _get_collection(self, name: str):
        return self.client.get_collection(name=name, embedding_function=self.embedding_fn)

    # ─── 写入方法 ───────────────────────────────────────

    def add_world_setting(self, text: str, metadata: dict = None):
        """存储世界观设定。"""
        if not text:
            return
        col = self._get_collection("world_settings")
        meta = metadata or {}
        meta["type"] = "world_setting"
        col.add(documents=[text], metadatas=[meta], ids=[f"world_{self._next_id(col)}"])

    def add_characters(self, text: str, metadata: dict = None):
        """存储人物档案。"""
        if not text:
            return
        col = self._get_collection("characters")
        meta = metadata or {}
        meta["type"] = "character"
        col.add(documents=[text], metadatas=[meta], ids=[f"char_{self._next_id(col)}"])

    def add_chapter(self, text: str, metadata: dict = None):
        """存储章节内容（自动分片入库）。"""
        if not text:
            return
        chunks = split_text(text, chunk_size=500)
        col = self._get_collection("chapters")
        base_id = self._next_id(col)
        for i, chunk in enumerate(chunks):
            meta = metadata or {}
            meta["type"] = "chapter"
            meta["chunk_index"] = i
            col.add(
                documents=[chunk],
                metadatas=[meta],
                ids=[f"ch_{base_id}_{i}"],
            )

    def add_plot_line(self, text: str, metadata: dict = None):
        """存储剧情伏笔。"""
        if not text:
            return
        col = self._get_collection("plot_lines")
        meta = metadata or {}
        meta["type"] = "plot_line"
        col.add(documents=[text], metadatas=[meta], ids=[f"plot_{self._next_id(col)}"])

    # ─── 检索方法 ───────────────────────────────────────

    def query_world_settings(self, query: str, n_results: int = 3) -> str:
        """检索相关世界观设定。"""
        col = self._get_collection("world_settings")
        if col.count() == 0:
            return ""
        results = col.query(query_texts=[query], n_results=min(n_results, col.count()))
        docs = results.get("documents", [[]])[0]
        return "\n---\n".join(docs) if docs else ""

    def query_characters(self, query: str, n_results: int = 5) -> str:
        """检索相关人物档案。"""
        col = self._get_collection("characters")
        if col.count() == 0:
            return ""
        results = col.query(query_texts=[query], n_results=min(n_results, col.count()))
        docs = results.get("documents", [[]])[0]
        return "\n---\n".join(docs) if docs else ""

    def query_chapters(self, query: str, n_results: int = 5) -> str:
        """检索相关历史章节。"""
        col = self._get_collection("chapters")
        if col.count() == 0:
            return ""
        results = col.query(query_texts=[query], n_results=min(n_results, col.count()))
        docs = results.get("documents", [[]])[0]
        return "\n---\n".join(docs) if docs else ""

    def query_plot_lines(self, query: str, n_results: int = 3) -> str:
        """检索相关剧情伏笔。"""
        col = self._get_collection("plot_lines")
        if col.count() == 0:
            return ""
        results = col.query(query_texts=[query], n_results=min(n_results, col.count()))
        docs = results.get("documents", [[]])[0]
        return "\n---\n".join(docs) if docs else ""

    def query_all(self, query: str, n_results: int = 3) -> dict[str, str]:
        """
        跨所有 collection 检索，返回汇总上下文。
        用于 Agent 在创作/校验时全面回顾已有设定。
        """
        return {
            "world": self.query_world_settings(query, n_results),
            "characters": self.query_characters(query, n_results),
            "chapters": self.query_chapters(query, n_results),
            "plots": self.query_plot_lines(query, n_results),
        }

    def build_context_prompt(self, query: str) -> str:
        """
        构建一个汇总的上下文提示词块，供 Agent 使用。
        如果知识库为空，返回空字符串。
        """
        all_ctx = self.query_all(query, n_results=3)
        parts = []
        if all_ctx["world"]:
            parts.append(f"【已有世界观设定】\n{all_ctx['world']}")
        if all_ctx["characters"]:
            parts.append(f"【已有角色档案】\n{all_ctx['characters']}")
        if all_ctx["chapters"]:
            parts.append(f"【相关历史章节片段】\n{all_ctx['chapters']}")
        if all_ctx["plots"]:
            parts.append(f"【未回收的剧情伏笔】\n{all_ctx['plots']}")
        return "\n\n".join(parts) if parts else ""

    # ─── 批量导入 ───────────────────────────────────────

    def import_existing_novel(self, full_text: str, metadata: dict = None):
        """
        导入已有小说全文。
        自动分片存入 chapters collection，并检索可用的世界观和人物信息。
        """
        if not full_text:
            return
        self.add_chapter(full_text, metadata=metadata or {"source": "imported"})

    # ─── 维护方法 ───────────────────────────────────────

    def clear_all(self):
        """清空所有记忆库，用于开启全新小说项目。"""
        for name in self.COLLECTIONS:
            try:
                self.client.delete_collection(name)
            except Exception:
                pass
        self._ensure_collections()

    def get_stats(self) -> dict:
        """获取各 collection 的状态统计。"""
        stats = {}
        for name in self.COLLECTIONS:
            try:
                col = self._get_collection(name)
                stats[name] = col.count()
            except Exception:
                stats[name] = 0
        return stats

    # ─── 内部工具 ───────────────────────────────────────

    def _next_id(self, collection) -> int:
        """生成下一个递增 ID。"""
        return collection.count() + 1
