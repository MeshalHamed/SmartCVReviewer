import pytest
from fastapi import HTTPException

from app.services.extractor import detect_language, extract_from_text
from app.services.rag import build_rag_bundle
from app.services.reviewer import _contains_third_language_script, _extract_json_object


def test_detects_arabic_text():
    text = "مهندس برمجيات بخبرة في بايثون وتطوير تطبيقات الويب وتحليل البيانات."
    assert detect_language(text) == "Arabic"


def test_text_extraction_requires_meaningful_content():
    with pytest.raises(HTTPException):
        extract_from_text("short")


def test_rag_selects_chunks_without_stuffing():
    text = "\n\n".join(
        [
            "Python developer with FastAPI and PostgreSQL experience. Built APIs and dashboards.",
            "Education: Computer Science. Certifications: AWS Cloud Practitioner.",
            "Projects include Arabic NLP, RAG search, and automated resume screening.",
        ]
        * 18
    )
    bundle = build_rag_bundle(text)
    assert bundle.stats["total_chunks"] >= bundle.stats["selected_chunks"]
    assert bundle.stats["selected_chunks"] <= 7
    assert "Chunk" in bundle.context


def test_extract_json_object_strips_reasoning_tags():
    parsed = _extract_json_object('<think>private reasoning</think>\n{"language":"English","ats_score":80}')
    assert parsed["language"] == "English"
    assert parsed["ats_score"] == 80


def test_detects_third_language_script_in_payload():
    assert _contains_third_language_script({"weaknesses": ["짧ة جدًا"]})
    assert not _contains_third_language_script({"weaknesses": ["مختصرة جدًا مع Python"]})
