from __future__ import annotations

import os
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Optional

import joblib
import numpy as np
from langchain_community.vectorstores import FAISS
from langchain_core.documents import Document
from langchain_core.embeddings import Embeddings
from langchain_core.messages import HumanMessage, SystemMessage

from model_behavior import segment_hint


class LocalTfidfEmbeddings(Embeddings):
    """A local embedding backend that keeps the RAG stack fully offline."""

    def __init__(self) -> None:
        from sklearn.feature_extraction.text import TfidfVectorizer

        self.vectorizer = TfidfVectorizer(
            lowercase=True,
            ngram_range=(1, 2),
            max_features=5000,
        )
        self._is_fitted = False

    def fit(self, texts: list[str]) -> None:
        corpus = texts if texts else ["placeholder"]
        self.vectorizer.fit(corpus)
        self._is_fitted = True

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        if not self._is_fitted:
            self.fit(texts)
        matrix = self.vectorizer.transform(texts)
        return matrix.astype(np.float32).toarray().tolist()

    def embed_query(self, text: str) -> list[float]:
        if not self._is_fitted:
            self.fit([text])
        vector = self.vectorizer.transform([text])
        return vector.astype(np.float32).toarray()[0].tolist()

    def save(self, path: Path) -> None:
        joblib.dump(self.vectorizer, path)

    @classmethod
    def load(cls, path: Path) -> "LocalTfidfEmbeddings":
        instance = cls.__new__(cls)
        instance.vectorizer = joblib.load(path)
        instance._is_fitted = True
        return instance


def _chunk_text(text: str, chunk_size: int = 1000, overlap: int = 150) -> list[str]:
    cleaned = text.strip()
    if not cleaned:
        return []

    if len(cleaned) <= chunk_size:
        return [cleaned]

    chunks: list[str] = []
    start = 0
    while start < len(cleaned):
        end = min(len(cleaned), start + chunk_size)
        chunk = cleaned[start:end].strip()
        if chunk:
            chunks.append(chunk)
        if end >= len(cleaned):
            break
        start = max(end - overlap, start + 1)
    return chunks


@dataclass
class RetrievedSource:
    source: str
    chunk_index: int
    snippet: str
    score: float


class RAGEngine:
    def __init__(self, knowledge_base_dir: str | Path | None = None, artifacts_dir: str | Path | None = None) -> None:
        self.base_dir = Path(__file__).resolve().parent
        self.knowledge_base_dir = Path(knowledge_base_dir or self.base_dir / "knowledge_base")
        self.artifacts_dir = Path(artifacts_dir or self.base_dir / "artifacts")
        self.index_dir = self.artifacts_dir / "faiss_index"
        self.vectorizer_path = self.artifacts_dir / "tfidf_vectorizer.joblib"
        self.embeddings = self._load_embeddings()
        self.vector_store = self._load_or_build_store()

    def _load_embeddings(self) -> LocalTfidfEmbeddings:
        if self.vectorizer_path.exists():
            return LocalTfidfEmbeddings.load(self.vectorizer_path)
        return LocalTfidfEmbeddings()

    def _load_or_build_store(self) -> FAISS | None:
        if self.index_dir.exists() and self.vectorizer_path.exists():
            try:
                return FAISS.load_local(
                    str(self.index_dir),
                    self.embeddings,
                    allow_dangerous_deserialization=True,
                )
            except TypeError:
                return FAISS.load_local(str(self.index_dir), self.embeddings)
            except Exception:
                pass

        return self.build_index()

    def load_documents(self) -> list[Document]:
        documents: list[Document] = []
        if not self.knowledge_base_dir.exists():
            return documents

        for markdown_file in sorted(self.knowledge_base_dir.rglob("*.md")):
            content = markdown_file.read_text(encoding="utf-8")
            for chunk_index, chunk in enumerate(_chunk_text(content), start=1):
                documents.append(
                    Document(
                        page_content=chunk,
                        metadata={
                            "source": markdown_file.name,
                            "path": str(markdown_file),
                            "chunk_index": chunk_index,
                        },
                    )
                )
        return documents

    def build_index(self) -> FAISS | None:
        documents = self.load_documents()
        if not documents:
            return None

        texts = [document.page_content for document in documents]
        self.embeddings.fit(texts)
        vector_store = FAISS.from_documents(documents, self.embeddings)

        self.artifacts_dir.mkdir(parents=True, exist_ok=True)
        self.index_dir.mkdir(parents=True, exist_ok=True)
        vector_store.save_local(str(self.index_dir))
        self.embeddings.save(self.vectorizer_path)

        self.vector_store = vector_store
        return vector_store

    def refresh(self) -> FAISS | None:
        if self.index_dir.exists():
            shutil.rmtree(self.index_dir)
        if self.vectorizer_path.exists():
            self.vectorizer_path.unlink()
        return self.build_index()

    def retrieve(self, question: str, top_k: int = 4) -> list[RetrievedSource]:
        if self.vector_store is None:
            self.vector_store = self.build_index()

        if self.vector_store is None:
            return []

        docs_and_scores = self.vector_store.similarity_search_with_score(question, k=top_k)
        results: list[RetrievedSource] = []
        for rank, (document, score) in enumerate(docs_and_scores, start=1):
            results.append(
                RetrievedSource(
                    source=str(document.metadata.get("source", "unknown")),
                    chunk_index=int(document.metadata.get("chunk_index", rank)),
                    snippet=document.page_content[:350].replace("\n", " ").strip(),
                    score=round(float(score), 4),
                )
            )
        return results

    def answer_question(
        self,
        question: str,
        behavior_context: Optional[Dict[str, Any]] = None,
        top_k: int = 4,
    ) -> Dict[str, Any]:
        retrieved_sources = self.retrieve(question, top_k=top_k)
        behavior_segment = behavior_context.get("segment") if behavior_context else None
        persona_hint = segment_hint(behavior_segment)

        context_blocks = []
        for index, source in enumerate(retrieved_sources, start=1):
            context_blocks.append(
                f"[{index}] Nguồn: {source.source} | chunk {source.chunk_index} | điểm phù hợp {source.score}\n"
                f"{source.snippet}"
            )

        if not context_blocks:
            context_blocks.append("Không tìm thấy tài liệu phù hợp trong knowledge_base.")

        prompt = f"""
Bạn là trợ lý tư vấn mua sắm cho một hệ thống e-commerce.
Hãy trả lời bằng tiếng Việt, ngắn gọn nhưng đủ ý, dựa trên tài liệu nội bộ.
Nếu thông tin không có trong tài liệu, hãy nói rõ là chưa tìm thấy dữ liệu hỗ trợ.
Luôn trích dẫn nguồn theo số thứ tự trong ngoặc vuông, ví dụ [1], [2].

Hồ sơ khách hàng:
{persona_hint}

Phân khúc dự đoán:
{behavior_segment or "Chưa xác định"}

Ngữ cảnh truy xuất:
{chr(10).join(context_blocks)}

Câu hỏi người dùng:
{question}
""".strip()

        answer = self._generate_answer(prompt, question=question, retrieved_sources=retrieved_sources, persona_hint=persona_hint)

        return {
            "answer": answer,
            "sources": [
                {
                    "source": source.source,
                    "chunk_index": source.chunk_index,
                    "score": source.score,
                    "snippet": source.snippet,
                }
                for source in retrieved_sources
            ],
            "prompt_preview": prompt,
        }

    def _generate_answer(
        self,
        prompt: str,
        question: str,
        retrieved_sources: list[RetrievedSource],
        persona_hint: str,
    ) -> str:
        llm = self._build_llm()
        if llm is not None:
            try:
                messages = [
                    SystemMessage(content="Bạn là trợ lý thương mại điện tử chuyên tư vấn theo ngữ cảnh và nguồn nội bộ."),
                    HumanMessage(content=prompt),
                ]
                response = llm.invoke(messages)
                content = getattr(response, "content", None)
                if content:
                    return str(content).strip()
            except Exception:
                pass

        cited_sources = " ".join(
            f"[{index + 1}] {source.source}" for index, source in enumerate(retrieved_sources)
        )
        summary_points = []
        for source in retrieved_sources[:3]:
            summary_points.append(f"- {source.snippet[:180]}...")

        if not summary_points:
            summary_points.append("- Chưa có nguồn tài liệu phù hợp để tổng hợp.")

        return (
            f"{persona_hint} Dựa trên tài liệu đã truy xuất, câu hỏi '{question}' có thể được trả lời theo hướng: "
            f"{'; '.join(summary_points)}. Nguồn tham chiếu: {cited_sources or 'chưa có nguồn'}."
        )

    def _build_llm(self):
        if not os.getenv("OPENAI_API_KEY"):
            return None

        try:
            from langchain_openai import ChatOpenAI

            return ChatOpenAI(
                model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
                temperature=0.2,
            )
        except Exception:
            return None