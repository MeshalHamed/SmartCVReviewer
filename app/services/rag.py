from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
import math
import re

from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter

from app.core.config import settings


REVIEW_QUERY = """
CV resume profile summary contact skills technical skills soft skills work experience projects education
certifications achievements measurable impact leadership responsibilities tools programming languages
ATS keywords job titles strengths weaknesses improvements gaps career fit
السيرة الذاتية المهارات الخبرة التعليم المشاريع الشهادات الإنجازات الكلمات المفتاحية الوظائف المناسبة نقاط القوة نقاط الضعف التحسينات
"""


@dataclass(frozen=True)
class RagBundle:
    context: str
    chunks: list[Document]
    selected_chunks: list[Document]
    stats: dict


def _count_words(text: str) -> int:
    return len(re.findall(r"[\w\u0600-\u06ff]+", text, flags=re.UNICODE))


def _tokens(text: str) -> list[str]:
    return re.findall(r"[\w\u0600-\u06ff]{2,}", text.lower(), flags=re.UNICODE)


def build_rag_bundle(text: str) -> RagBundle:
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=settings.chunk_size,
        chunk_overlap=settings.chunk_overlap,
        separators=["\n\n", "\n", ". ", "، ", " ", ""],
    )
    chunks = splitter.create_documents([text])
    for index, chunk in enumerate(chunks, start=1):
        chunk.metadata["chunk_id"] = index

    selected = _retrieve(chunks, REVIEW_QUERY, settings.top_k_chunks)
    context = _format_context(selected)

    stats = {
        "total_characters": len(text),
        "estimated_words": _count_words(text),
        "total_chunks": len(chunks),
        "selected_chunks": len(selected),
        "chunk_size": settings.chunk_size,
        "chunk_overlap": settings.chunk_overlap,
        "retrieval": "TF-IDF cosine similarity over LangChain text chunks",
    }
    return RagBundle(context=context, chunks=chunks, selected_chunks=selected, stats=stats)


def _retrieve(chunks: list[Document], query: str, top_k: int) -> list[Document]:
    if not chunks:
        return []
    if len(chunks) <= top_k:
        return chunks

    tokenized_docs = [_tokens(chunk.page_content) for chunk in chunks]
    query_tokens = _tokens(query)
    document_count = len(tokenized_docs)
    document_frequency: Counter[str] = Counter()
    for doc_tokens in tokenized_docs:
        document_frequency.update(set(doc_tokens))

    idf = {
        token: math.log((1 + document_count) / (1 + frequency)) + 1
        for token, frequency in document_frequency.items()
    }

    query_vector = _tfidf_vector(query_tokens, idf)
    scores = [
        _cosine_similarity(query_vector, _tfidf_vector(doc_tokens, idf))
        for doc_tokens in tokenized_docs
    ]

    ranked_indexes = sorted(range(len(scores)), key=lambda index: scores[index], reverse=True)[:top_k]
    selected: list[Document] = []
    for index in sorted(ranked_indexes):
        chunk = chunks[index]
        chunk.metadata["score"] = round(float(scores[index]), 4)
        selected.append(chunk)
    return selected


def _tfidf_vector(tokens: list[str], idf: dict[str, float]) -> dict[str, float]:
    counts = Counter(token for token in tokens if token in idf)
    total = sum(counts.values()) or 1
    return {token: (count / total) * idf[token] for token, count in counts.items()}


def _cosine_similarity(left: dict[str, float], right: dict[str, float]) -> float:
    if not left or not right:
        return 0.0
    dot = sum(weight * right.get(token, 0.0) for token, weight in left.items())
    left_norm = math.sqrt(sum(weight * weight for weight in left.values()))
    right_norm = math.sqrt(sum(weight * weight for weight in right.values()))
    if not left_norm or not right_norm:
        return 0.0
    return dot / (left_norm * right_norm)


def _format_context(chunks: list[Document]) -> str:
    sections = []
    for chunk in chunks:
        chunk_id = chunk.metadata.get("chunk_id", "?")
        score = chunk.metadata.get("score", "full")
        sections.append(f"[Chunk {chunk_id} | relevance {score}]\n{chunk.page_content.strip()}")
    return "\n\n---\n\n".join(sections)
