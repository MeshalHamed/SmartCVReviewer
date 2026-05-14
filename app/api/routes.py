from __future__ import annotations

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from fastapi.responses import StreamingResponse
from io import BytesIO

from app.schemas import ReviewResponse
from app.services.extractor import extract_from_text, extract_from_upload
from app.services.optimizer import optimize_cv
from app.services.pdf_renderer import render_cv_pdf
from app.services.rag import build_rag_bundle
from app.services.reviewer import review_cv
from app.services.store import get_review, save_review


router = APIRouter()


@router.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@router.post("/review", response_model=ReviewResponse)
async def review(
    file: UploadFile | None = File(default=None),
    cv_text: str | None = Form(default=None),
) -> ReviewResponse:
    has_file = file is not None and bool(file.filename)
    has_text = cv_text is not None and bool(cv_text.strip())

    if has_file and has_text:
        raise HTTPException(status_code=400, detail="Choose either file upload or pasted text, not both.")
    if not has_file and not has_text:
        raise HTTPException(status_code=400, detail="Upload a CV file or paste CV text.")

    if has_file and file is not None:
        text = await extract_from_upload(file)
        source_type = "file"
    else:
        text = extract_from_text(cv_text or "")
        source_type = "text"

    rag = build_rag_bundle(text)
    review_result = review_cv(text=text, rag=rag, source_type=source_type)
    return save_review(text=text, source_type=source_type, review=review_result)


@router.get("/reviews/{review_id}/modified-cv.pdf")
def download_modified_cv(review_id: str) -> StreamingResponse:
    record = get_review(review_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Review not found or expired. Please review the CV again.")

    optimized_cv = optimize_cv(record.text, record.review)
    pdf_bytes = render_cv_pdf(optimized_cv)
    filename = "optimized-cv.pdf"
    return StreamingResponse(
        BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
