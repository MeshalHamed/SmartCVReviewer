# Smart CV Reviewer

Arabic/English AI CV reviewer built with FastAPI, LangChain Groq, Kimi/Groq models, and a lightweight RAG pipeline. Users can upload a PDF/TXT CV or paste CV text. The app detects the dominant language and returns feedback in the same language.

## Project Plan

1. Input UX
   - Accept one source at a time: PDF/TXT upload or pasted text.
   - Disable pasted text when a file is selected.
   - Disable upload when text is present.

2. Extraction
   - Extract selectable PDF text with `pypdf`.
   - Decode text files with UTF-8 first and Arabic Windows-1256 fallback.
   - Normalize whitespace while preserving Arabic text.

3. RAG Review Flow
   - Split the CV into LangChain text chunks.
   - Retrieve the most relevant chunks with pure-Python TF-IDF cosine similarity.
   - Send only retrieved evidence and document stats to the LLM.
   - Avoid stuffing the full CV into the prompt.

4. AI Review
   - Use `langchain_groq.ChatGroq`.
   - Default model: `qwen/qwen3-32b`, an available Groq reasoning model.
   - Optional Kimi model: set `GROQ_MODEL=moonshotai/kimi-k2-instruct` if your Groq account has access.
   - Prompt forces same-language output, grounded feedback, no invented facts, and valid JSON.

5. Optimized CV PDF
   - Generate a rewritten CV in a global tech company style.
   - Keep it ATS-friendly with clear headings, skills, projects, education, and action bullets.
   - Avoid invented employers, dates, metrics, degrees, or certifications.
   - Export the optimized CV as a downloadable PDF.

6. API and Frontend
   - FastAPI endpoints for health and review.
   - Minimal animated HTML/CSS/JS UI.
   - Render strengths, weaknesses, improvements, ATS score, missing keywords, suitable roles, and PDF download.

## Features

- Arabic and English CV support.
- PDF and TXT extraction.
- Pasted text review.
- RAG-based chunk retrieval before LLM review.
- Same-language feedback.
- Job role recommendations with fit scores and keywords.
- Downloadable optimized CV PDF with a clean ATS-friendly layout.
- Clean FastAPI backend and modular services.
- Charming responsive frontend with small animations.

## Folder Structure

```text
SmartCVReviewer/
  app/
    api/
      __init__.py
      routes.py
    core/
      config.py
    services/
      extractor.py
      optimizer.py
      pdf_renderer.py
      rag.py
      reviewer.py
      store.py
    static/
      app.js
      styles.css
    templates/
      index.html
    __init__.py
    main.py
    schemas.py
  tests/
    test_api.py
    test_services.py
  .env.example
  .gitignore
  README.md
  requirements.txt
```

## Setup

```bash
cd SmartCVReviewer
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
```

Edit `.env`:

```env
GROQ_API_KEY=your_groq_api_key_here
GROQ_MODEL=qwen/qwen3-32b
```

Run:

```bash
uvicorn app.main:app --reload --port 8000
```

Open:

```text
http://127.0.0.1:8000
```

If Windows shows `WinError 10013`, port `8000` is blocked or already reserved. Run with another port:

```bash
uvicorn app.main:app --reload --port 8001
```

## API

Health:

```bash
curl http://127.0.0.1:8000/api/health
```

Review pasted text:

```bash
curl -X POST http://127.0.0.1:8000/api/review ^
  -F "cv_text=Python developer with FastAPI, PostgreSQL, Docker, and data analysis experience. Built dashboards, REST APIs, and RAG search tools. Education: Computer Science. Certifications: AWS Cloud Practitioner."
```

Review file:

```bash
curl -X POST http://127.0.0.1:8000/api/review ^
  -F "file=@cv.pdf"
```

Download optimized CV PDF after review:

```bash
curl -L -o optimized-cv.pdf http://127.0.0.1:8000/api/reviews/{review_id}/modified-cv.pdf
```

Example response:

```json
{
  "review_id": "1f1b5f48-1a7b-4b66-a95e-6c4626e35bb4",
  "language": "English",
  "executive_summary": "The CV shows a strong backend Python profile with practical API and data experience...",
  "ats_score": 78,
  "strengths": ["Clear Python/FastAPI positioning", "Relevant project evidence"],
  "weaknesses": ["Limited measurable achievements", "Missing deployment details"],
  "improvements": ["Add metrics for API performance or user impact"],
  "recommended_roles": [
    {
      "title": "Junior Backend Python Developer",
      "why": "The evidence includes FastAPI, PostgreSQL, and API project work.",
      "fit_score": 84,
      "keywords": ["FastAPI", "PostgreSQL", "REST APIs"]
    }
  ],
  "missing_keywords": ["CI/CD", "Testing", "Cloud deployment"],
  "evidence_notes": ["Retrieved chunks mention FastAPI, PostgreSQL, dashboards, and RAG tools."],
  "next_steps": ["Add 3 measurable bullets under each project."],
  "source_type": "text",
  "rag": {
    "total_characters": 184,
    "estimated_words": 24,
    "total_chunks": 1,
    "selected_chunks": 1,
    "chunk_size": 1200,
    "chunk_overlap": 160,
    "retrieval": "TF-IDF cosine similarity over LangChain text chunks"
  }
}
```

## Tests

```bash
pytest
```

The tests cover language detection, minimum text validation, RAG chunk retrieval, API validation, root page rendering, and PDF generation.

## Render Deployment

This repo includes `render.yaml`, `Procfile`, and `runtime.txt`.

On Render:

1. Create a new Web Service from the GitHub repo.
2. Use the start command:

```bash
uvicorn app.main:app --host 0.0.0.0 --port $PORT
```

3. Add environment variables:

```env
GROQ_API_KEY=your_groq_api_key_here
GROQ_MODEL=qwen/qwen3-32b
```
