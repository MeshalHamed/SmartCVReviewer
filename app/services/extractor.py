from __future__ import annotations

from io import BytesIO
import re

from fastapi import HTTPException, UploadFile
from pypdf import PdfReader

from app.core.config import settings


SUPPORTED_EXTENSIONS = {".pdf", ".txt"}


def normalize_text(text: str) -> str:
    text = text.replace("\x00", " ")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def detect_language(text: str) -> str:
    arabic_chars = sum(1 for char in text if "\u0600" <= char <= "\u06ff")
    latin_chars = sum(1 for char in text if ("a" <= char.lower() <= "z"))
    if arabic_chars > latin_chars * 0.35 and arabic_chars > 25:
        return "Arabic"
    return "English"


def _decode_text_file(data: bytes) -> str:
    for encoding in ("utf-8-sig", "utf-8", "cp1256"):
        try:
            return data.decode(encoding)
        except UnicodeDecodeError:
            continue
    raise HTTPException(status_code=400, detail="Could not decode text file as UTF-8 or Arabic Windows-1256.")


def _extract_pdf(data: bytes) -> str:
    try:
        reader = PdfReader(BytesIO(data))
    except Exception as exc:
        raise HTTPException(status_code=400, detail="Invalid or unreadable PDF file.") from exc

    pages: list[str] = []
    for index, page in enumerate(reader.pages, start=1):
        page_text = page.extract_text() or ""
        if page_text.strip():
            pages.append(f"[Page {index}]\n{page_text}")

    if not pages:
        raise HTTPException(status_code=400, detail="No selectable text was found in the PDF.")
    return "\n\n".join(pages)


async def extract_from_upload(file: UploadFile) -> str:
    filename = file.filename or ""
    suffix = "." + filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    if suffix not in SUPPORTED_EXTENSIONS:
        raise HTTPException(status_code=400, detail="Only PDF and TXT files are supported.")

    data = await file.read()
    if not data:
        raise HTTPException(status_code=400, detail="Uploaded file is empty.")
    if len(data) > settings.max_upload_bytes:
        raise HTTPException(status_code=413, detail=f"File is larger than {settings.max_upload_mb} MB.")

    if suffix == ".pdf":
        return normalize_text(_extract_pdf(data))
    return normalize_text(_decode_text_file(data))


def extract_from_text(text: str) -> str:
    cleaned = normalize_text(text)
    if len(cleaned) < 80:
        raise HTTPException(status_code=400, detail="Please provide more CV text for a meaningful review.")
    return cleaned
