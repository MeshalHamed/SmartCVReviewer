from __future__ import annotations

import json
import re
from typing import Any

from fastapi import HTTPException
from langchain_core.prompts import ChatPromptTemplate
from langchain_groq import ChatGroq

from app.core.config import settings
from app.schemas import ReviewResponse
from app.services.extractor import detect_language
from app.services.rag import RagBundle


REVIEW_SCHEMA = {
    "language": "Arabic or English",
    "executive_summary": "Concise 3-5 sentence review in the CV language.",
    "ats_score": "Integer from 0 to 100.",
    "strengths": ["Specific strengths grounded in evidence."],
    "weaknesses": ["Specific weaknesses or risks."],
    "improvements": ["Actionable CV edits with examples when helpful."],
    "recommended_roles": [
        {
            "title": "Suitable job role title",
            "why": "Why this role fits the evidence",
            "fit_score": "Integer from 0 to 100",
            "keywords": ["ATS/job-search keywords"],
        }
    ],
    "missing_keywords": ["Important missing or weak keywords"],
    "evidence_notes": ["Brief notes showing which evidence drove the review"],
    "next_steps": ["Prioritized next actions"],
}


SYSTEM_PROMPT = """
You are a senior bilingual CV/resume reviewer and hiring-market analyst.
Your job is to review Arabic and English CVs precisely, fairly, and practically.

Rules:
- Reply in the same dominant language as the CV: {language}. If the CV is Arabic, all user-facing values must be Arabic.
- For Arabic CVs, translate all explanations, category phrases, and advice into Arabic. Keep only technology/product names such as Python, FastAPI, AWS, Docker, or PostgreSQL in Latin characters when appropriate.
- Never use a third language that is not Arabic or English.
- Use only the retrieved CV evidence and the document statistics. Do not invent employers, dates, degrees, tools, or achievements.
- Think carefully internally, but do not reveal chain-of-thought. Return concise professional conclusions only.
- Be direct but constructive. Mention uncertainty when evidence is missing.
- Prefer measurable, ATS-friendly improvement advice.
- Recommend realistic job roles based on evidence, not ambition alone.
- Return valid JSON only. No Markdown fences, no commentary outside JSON.

JSON shape:
{schema}
"""


USER_PROMPT = """
Document statistics:
{stats}

Retrieved CV evidence:
{context}

Additional correction instruction:
{repair_instruction}

Review the CV and produce the JSON response now.
"""


def _build_llm() -> ChatGroq:
    if not settings.groq_api_key:
        raise HTTPException(
            status_code=500,
            detail="GROQ_API_KEY is not configured. Add it to .env before using AI review.",
        )
    return ChatGroq(
        model=settings.groq_model,
        groq_api_key=settings.groq_api_key,
        temperature=settings.llm_temperature,
        max_tokens=2500,
    )


def review_cv(text: str, rag: RagBundle, source_type: str) -> ReviewResponse:
    language = detect_language(text)
    prompt = ChatPromptTemplate.from_messages(
        [
            ("system", SYSTEM_PROMPT),
            ("user", USER_PROMPT),
        ]
    )
    chain = prompt | _build_llm()

    payload: dict[str, Any] | None = None
    repair_instruction = "None."
    for _ in range(2):
        try:
            raw_response = chain.invoke(
                {
                    "language": language,
                    "schema": json.dumps(REVIEW_SCHEMA, ensure_ascii=False, indent=2),
                    "stats": json.dumps(rag.stats, ensure_ascii=False, indent=2),
                    "context": rag.context,
                    "repair_instruction": repair_instruction,
                }
            )
            content = raw_response.content if hasattr(raw_response, "content") else str(raw_response)
            payload = _extract_json_object(content)
            if not _contains_third_language_script(payload):
                break
            repair_instruction = (
                "The previous answer used a third-language script. Rewrite the complete JSON in the requested CV language only. "
                "For Arabic, keep only technology and product names in Latin characters."
            )
        except HTTPException:
            raise
        except Exception as exc:
            raise HTTPException(status_code=502, detail=f"AI review failed: {exc}") from exc

    if payload is None:
        raise HTTPException(status_code=502, detail="AI review failed: empty model response.")

    payload["source_type"] = source_type
    payload["rag"] = rag.stats
    return ReviewResponse.model_validate(payload)


def _extract_json_object(content: Any) -> dict[str, Any]:
    if isinstance(content, list):
        content = "\n".join(str(part) for part in content)
    text = str(content).strip()
    text = re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL | re.IGNORECASE).strip()
    text = text.removeprefix("```json").removeprefix("```").removesuffix("```").strip()

    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1 or end <= start:
        raise ValueError(f"No JSON object found in model response: {text[:300]}")

    return json.loads(text[start : end + 1])


def _contains_third_language_script(value: Any) -> bool:
    text = json.dumps(value, ensure_ascii=False) if not isinstance(value, str) else value
    return bool(re.search(r"[\u3040-\u30ff\u3400-\u4dbf\u4e00-\u9fff\uac00-\ud7af]", text))
