from __future__ import annotations

import json
from typing import Any

from fastapi import HTTPException
from langchain_core.prompts import ChatPromptTemplate

from app.schemas import OptimizedCV, ReviewResponse
from app.services.extractor import detect_language
from app.services.rag import build_rag_bundle
from app.services.reviewer import _build_llm, _contains_third_language_script, _extract_json_object


OPTIMIZED_CV_SCHEMA = {
    "language": "Arabic or English",
    "full_name": "Candidate name if explicitly present, otherwise empty string",
    "target_title": "Focused role title aligned with the evidence",
    "contact_line": "Email | phone | LinkedIn/GitHub if explicitly present, otherwise empty string",
    "location": "Location if explicitly present, otherwise empty string",
    "links": ["Portfolio, GitHub, LinkedIn links if present"],
    "summary": "2-4 line ATS-friendly professional summary grounded only in evidence",
    "core_skills": ["Recruiter-readable strengths and domain skills"],
    "technical_skills": ["Tools, languages, platforms, frameworks from evidence only"],
    "experience": [
        {
            "title": "Role title if present",
            "company": "Company if present",
            "location": "Location if present",
            "dates": "Dates if present",
            "bullets": ["Impact-oriented bullet using action verb and evidence only"],
        }
    ],
    "projects": [
        {
            "name": "Project name or descriptive project title",
            "technologies": ["Technologies from evidence"],
            "bullets": ["What was built, how, and why it matters without invented metrics"],
        }
    ],
    "education": [
        {
            "degree": "Degree if present",
            "institution": "Institution if present",
            "location": "Location if present",
            "dates": "Dates if present",
            "notes": ["Relevant notes from evidence"],
        }
    ],
    "certifications": ["Certifications from evidence only"],
    "additional_sections": [
        {
            "title": "Section title",
            "company": "",
            "location": "",
            "dates": "",
            "bullets": ["Relevant facts that do not fit above"],
        }
    ],
}


SYSTEM_PROMPT = """
You are an expert resume writer for competitive global technology companies such as Google, Microsoft, Meta, Amazon, and Apple.
Create a polished, ATS-friendly CV rewrite in the same language as the original CV: {language}.

Quality bar:
- Use a clean global tech resume style: concise summary, keywords, action verbs, evidence-based bullets, no decorative language.
- Do not invent names, companies, dates, degrees, metrics, locations, certifications, links, or employers.
- If metrics are missing, write strong outcome-oriented bullets without fake numbers.
- Preserve important technology names exactly, especially Python, FastAPI, PostgreSQL, Docker, AWS, RAG, NLP, REST.
- For Arabic CVs, write Arabic user-facing text and keep technology names in Latin characters where standard.
- Never use a third language. Return valid JSON only.

JSON shape:
{schema}
"""


USER_PROMPT = """
Existing review:
{review}

Retrieved CV evidence:
{context}

Additional correction instruction:
{repair_instruction}

Generate the optimized CV JSON now.
"""


def optimize_cv(text: str, review: ReviewResponse) -> OptimizedCV:
    language = detect_language(text)
    rag = build_rag_bundle(text)
    prompt = ChatPromptTemplate.from_messages([("system", SYSTEM_PROMPT), ("user", USER_PROMPT)])
    chain = prompt | _build_llm()

    payload: dict[str, Any] | None = None
    repair_instruction = "None."
    for _ in range(2):
        try:
            raw_response = chain.invoke(
                {
                    "language": language,
                    "schema": json.dumps(OPTIMIZED_CV_SCHEMA, ensure_ascii=False, indent=2),
                    "review": review.model_dump_json(indent=2),
                    "context": rag.context,
                    "repair_instruction": repair_instruction,
                }
            )
            content = raw_response.content if hasattr(raw_response, "content") else str(raw_response)
            payload = _extract_json_object(content)
            if not _contains_third_language_script(payload):
                break
            repair_instruction = "Rewrite the complete JSON using only the requested CV language and standard Latin technology names."
        except HTTPException:
            raise
        except Exception as exc:
            raise HTTPException(status_code=502, detail=f"Optimized CV generation failed: {exc}") from exc

    if payload is None:
        raise HTTPException(status_code=502, detail="Optimized CV generation failed: empty model response.")

    return OptimizedCV.model_validate(payload)
