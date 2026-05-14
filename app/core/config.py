from dataclasses import dataclass
import os

from dotenv import load_dotenv


load_dotenv()


@dataclass(frozen=True)
class Settings:
    app_name: str = os.getenv("APP_NAME", "Smart CV Reviewer")
    groq_api_key: str | None = os.getenv("GROQ_API_KEY")
    groq_model: str = os.getenv("GROQ_MODEL", "qwen/qwen3-32b")
    max_upload_mb: int = int(os.getenv("MAX_UPLOAD_MB", "6"))
    chunk_size: int = int(os.getenv("RAG_CHUNK_SIZE", "1200"))
    chunk_overlap: int = int(os.getenv("RAG_CHUNK_OVERLAP", "160"))
    top_k_chunks: int = int(os.getenv("RAG_TOP_K", "7"))
    llm_temperature: float = float(os.getenv("GROQ_TEMPERATURE", "0.15"))

    @property
    def max_upload_bytes(self) -> int:
        return self.max_upload_mb * 1024 * 1024


settings = Settings()
