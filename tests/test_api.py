from fastapi.testclient import TestClient

from app.api import routes
from app.main import app
from app.schemas import OptimizedCV, ReviewResponse


client = TestClient(app)


def _fake_review(text, rag, source_type):
    return ReviewResponse(
        language="English",
        executive_summary="A focused backend CV with clear Python experience.",
        ats_score=82,
        strengths=["Python and API experience"],
        weaknesses=["Needs more metrics"],
        improvements=["Add quantified project outcomes"],
        recommended_roles=[
            {
                "title": "Backend Python Developer",
                "why": "The CV mentions Python, APIs, and databases.",
                "fit_score": 86,
                "keywords": ["Python", "FastAPI", "REST"],
            }
        ],
        missing_keywords=["Testing", "CI/CD"],
        evidence_notes=["Retrieved evidence included Python and API work."],
        next_steps=["Rewrite project bullets with impact metrics."],
        source_type=source_type,
        rag=rag.stats,
    )


def test_review_text_flow(monkeypatch):
    monkeypatch.setattr(routes, "review_cv", _fake_review)
    cv_text = (
        "Python backend developer with FastAPI, PostgreSQL, Docker, REST APIs, dashboards, "
        "and Arabic NLP projects. Built RAG search tools and automated reporting workflows."
    )

    response = client.post("/api/review", data={"cv_text": cv_text})

    assert response.status_code == 200
    data = response.json()
    assert data["source_type"] == "text"
    assert data["ats_score"] == 82
    assert data["rag"]["selected_chunks"] >= 1
    assert data["review_id"]


def test_root_page_loads():
    response = client.get("/")

    assert response.status_code == 200
    assert "Smart CV Reviewer" in response.text


def test_review_rejects_file_and_text_together():
    response = client.post(
        "/api/review",
        data={"cv_text": "This text is intentionally present with a file."},
        files={"file": ("cv.txt", b"Python developer with APIs and databases.", "text/plain")},
    )

    assert response.status_code == 400
    assert "either file upload or pasted text" in response.json()["detail"]


def test_download_modified_cv_pdf(monkeypatch):
    monkeypatch.setattr(routes, "review_cv", _fake_review)
    monkeypatch.setattr(
        routes,
        "optimize_cv",
        lambda text, review: OptimizedCV(
            language="English",
            full_name="Candidate",
            target_title="Backend Python Developer",
            summary="Backend developer with Python API experience.",
            core_skills=["Backend Engineering", "API Design"],
            technical_skills=["Python", "FastAPI", "PostgreSQL"],
            projects=[
                {
                    "name": "RAG Search Tool",
                    "technologies": ["Python", "RAG"],
                    "bullets": ["Built a retrieval workflow for document search."],
                }
            ],
        ),
    )
    review_response = client.post(
        "/api/review",
        data={
            "cv_text": (
                "Python backend developer with FastAPI, PostgreSQL, Docker, REST APIs, dashboards, "
                "Arabic NLP projects, RAG search tools, and reporting workflows."
            )
        },
    )
    review_id = review_response.json()["review_id"]

    pdf_response = client.get(f"/api/reviews/{review_id}/modified-cv.pdf")

    assert pdf_response.status_code == 200
    assert pdf_response.headers["content-type"] == "application/pdf"
    assert pdf_response.content.startswith(b"%PDF")
