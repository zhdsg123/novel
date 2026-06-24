"""
向量知识库 — RAG 长效记忆系统
自动选择：chromadb（优先）→ 纯 sklearn（回退）
"""

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from src.utils.text_utils import split_text
from src.config import CHROMA_PERSIST_DIR

# chromadb 安全导入
try:
    import chromadb
    from chromadb.config import Settings as ChromaSettings
    from sklearn.feature_extraction.text import HashingVectorizer
    _HAS_CHROMADB = True
except Exception:
    _HAS_CHROMADB = False


# ═══════════════════════════════════════════════════════
# ChromaDB 版本（优先使用）
# ═══════════════════════════════════════════════════════

if _HAS_CHROMADB:

    class _EmbeddingFn:
        def __init__(self, n_features=384):
            self._name = f"sklearn-hash-{n_features}"
            self._vec = HashingVectorizer(
                n_features=n_features, analyzer='char_wb',
                ngram_range=(2, 4), norm='l2', alternate_sign=False,
            )
        def name(self): return self._name
        def __call__(self, input):
            if isinstance(input, str): input = [input]
            return self._vec.transform(input).toarray().tolist()
        def embed_query(self, input): return self.__call__(input)

    class ChromaMemoryStore:
        COLLECTIONS = ["world_settings", "characters", "chapters", "plot_lines"]

        def __init__(self, persist_dir=CHROMA_PERSIST_DIR):
            self._ef = _EmbeddingFn()
            self._client = chromadb.PersistentClient(
                path=persist_dir,
                settings=ChromaSettings(anonymized_telemetry=False),
            )
            self._ensure_collections()

        def _ensure_collections(self):
            existing = {c.name for c in self._client.list_collections()}
            for name in self.COLLECTIONS:
                if name not in existing:
                    self._client.create_collection(name=name, embedding_function=self._ef)

        def _col(self, name):
            return self._client.get_collection(name=name, embedding_function=self._ef)

        def _next_id(self, col):
            return col.count() + 1

        def _meta(self, m=None):
            m = m or {}
            if not m: m = {"source": "system"}
            return m

        def add_world_setting(self, text, metadata=None):
            if not text: return
            c = self._col("world_settings")
            c.add(documents=[text], metadatas=[self._meta(metadata)], ids=[f"w_{self._next_id(c)}"])

        def add_characters(self, text, metadata=None):
            if not text: return
            c = self._col("characters")
            c.add(documents=[text], metadatas=[self._meta(metadata)], ids=[f"c_{self._next_id(c)}"])

        def add_chapter(self, text, metadata=None):
            if not text: return
            col = self._col("chapters")
            chunks = split_text(text, 500)
            bid = self._next_id(col)
            for i, chunk in enumerate(chunks):
                col.add(documents=[chunk], metadatas=[self._meta(metadata)], ids=[f"ch_{bid}_{i}"])

        def add_plot_line(self, text, metadata=None):
            if not text: return
            c = self._col("plot_lines")
            c.add(documents=[text], metadatas=[self._meta(metadata)], ids=[f"p_{self._next_id(c)}"])

        def _query_col(self, name, q, n):
            col = self._col(name)
            if col.count() == 0: return ""
            r = col.query(query_texts=[q], n_results=min(n, col.count()))
            docs = r.get("documents", [[]])[0]
            return "\n---\n".join(docs) if docs else ""

        def query_world_settings(self, q, n=3): return self._query_col("world_settings", q, n)
        def query_characters(self, q, n=5): return self._query_col("characters", q, n)
        def query_chapters(self, q, n=5): return self._query_col("chapters", q, n)
        def query_plot_lines(self, q, n=3): return self._query_col("plot_lines", q, n)

        def query_all(self, q, n=3):
            return {
                "world": self.query_world_settings(q, n),
                "characters": self.query_characters(q, n),
                "chapters": self.query_chapters(q, n),
                "plots": self.query_plot_lines(q, n),
            }

        def build_context_prompt(self, q):
            ctx = self.query_all(q, 3)
            parts = []
            if ctx["world"]: parts.append(f"【已有世界观设定】\n{ctx['world']}")
            if ctx["characters"]: parts.append(f"【已有角色档案】\n{ctx['characters']}")
            if ctx["chapters"]: parts.append(f"【相关历史章节片段】\n{ctx['chapters']}")
            if ctx["plots"]: parts.append(f"【未回收的剧情伏笔】\n{ctx['plots']}")
            return "\n\n".join(parts) if parts else ""

        def import_existing_novel(self, text, metadata=None):
            self.add_chapter(text, metadata or {"source": "imported"})

        def clear_all(self):
            for name in self.COLLECTIONS:
                try: self._client.delete_collection(name)
                except Exception: pass
            self._ensure_collections()

        def get_stats(self):
            s = {}
            for name in self.COLLECTIONS:
                try: s[name] = self._col(name).count()
                except Exception: s[name] = 0
            return s


# ═══════════════════════════════════════════════════════
# 纯 sklearn 回退版本
# ═══════════════════════════════════════════════════════

class SimpleMemoryStore:
    COLLECTIONS = ["world_settings", "characters", "chapters", "plot_lines"]

    def __init__(self, persist_dir=None):
        self._store = {k: [] for k in self.COLLECTIONS}
        self._vec = TfidfVectorizer(analyzer='char_wb', ngram_range=(2, 4), max_features=512)

    def _add(self, col, text):
        if text: self._store[col].append(text)

    def _query(self, col, q, n):
        docs = self._store[col]
        if not docs: return ""
        try:
            all_texts = docs + [q]
            vecs = self._vec.fit_transform(all_texts)
            scores = cosine_similarity(vecs[-1:], vecs[:-1])[0]
            top = scores.argsort()[-min(n, len(docs)):][::-1]
            return "\n---\n".join(docs[i] for i in top if scores[i] > 0.01)
        except Exception:
            return "\n---\n".join(docs[-n:])

    def add_world_setting(self, text, metadata=None): self._add("world_settings", text)
    def add_characters(self, text, metadata=None): self._add("characters", text)
    def add_plot_line(self, text, metadata=None): self._add("plot_lines", text)

    def add_chapter(self, text, metadata=None):
        for chunk in split_text(text): self._add("chapters", chunk)

    def query_world_settings(self, q, n=3): return self._query("world_settings", q, n)
    def query_characters(self, q, n=5): return self._query("characters", q, n)
    def query_chapters(self, q, n=5): return self._query("chapters", q, n)
    def query_plot_lines(self, q, n=3): return self._query("plot_lines", q, n)

    def query_all(self, q, n=3):
        return {k: self._query(k, q, n) for k in self.COLLECTIONS}

    def build_context_prompt(self, q):
        ctx = self.query_all(q, 3)
        parts = []
        if ctx["world_settings"]: parts.append(f"【已有世界观设定】\n{ctx['world_settings']}")
        if ctx["characters"]: parts.append(f"【已有角色档案】\n{ctx['characters']}")
        if ctx["chapters"]: parts.append(f"【相关历史章节片段】\n{ctx['chapters']}")
        if ctx["plot_lines"]: parts.append(f"【未回收的剧情伏笔】\n{ctx['plot_lines']}")
        return "\n\n".join(parts) if parts else ""

    def import_existing_novel(self, text, metadata=None): self.add_chapter(text)
    def clear_all(self):
        for k in self.COLLECTIONS: self._store[k] = []

    def get_stats(self):
        return {k: len(v) for k, v in self._store.items()}


# ═══════════════════════════════════════════════════════
# 对外统一导出
# ═══════════════════════════════════════════════════════

if _HAS_CHROMADB:
    NovelMemoryStore = ChromaMemoryStore
else:
    NovelMemoryStore = SimpleMemoryStore
