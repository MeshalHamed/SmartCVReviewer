from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
from uuid import uuid4

from app.schemas import ReviewResponse


@dataclass
class ReviewRecord:
    review_id: str
    text: str
    source_type: str
    review: ReviewResponse
    created_at: datetime


_records: dict[str, ReviewRecord] = {}
_ttl = timedelta(hours=2)
_data_dir = Path(".data/reviews")


def save_review(text: str, source_type: str, review: ReviewResponse) -> ReviewResponse:
    cleanup_expired_reviews()
    review_id = str(uuid4())
    review.review_id = review_id
    _records[review_id] = ReviewRecord(
        review_id=review_id,
        text=text,
        source_type=source_type,
        review=review,
        created_at=datetime.now(timezone.utc),
    )
    _write_record(_records[review_id])
    return review


def get_review(review_id: str) -> ReviewRecord | None:
    cleanup_expired_reviews()
    if review_id in _records:
        return _records[review_id]
    record = _read_record(review_id)
    if record is not None:
        _records[review_id] = record
    return record


def cleanup_expired_reviews() -> None:
    now = datetime.now(timezone.utc)
    expired = [review_id for review_id, record in _records.items() if now - record.created_at > _ttl]
    for review_id in expired:
        _records.pop(review_id, None)
        _record_path(review_id).unlink(missing_ok=True)

    if not _data_dir.exists():
        return
    for path in _data_dir.glob("*.json"):
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
            created_at = datetime.fromisoformat(payload["created_at"])
        except (OSError, KeyError, ValueError, json.JSONDecodeError):
            path.unlink(missing_ok=True)
            continue
        if now - created_at > _ttl:
            path.unlink(missing_ok=True)


def _write_record(record: ReviewRecord) -> None:
    _data_dir.mkdir(parents=True, exist_ok=True)
    payload = {
        "review_id": record.review_id,
        "text": record.text,
        "source_type": record.source_type,
        "review": record.review.model_dump(mode="json"),
        "created_at": record.created_at.isoformat(),
    }
    _record_path(record.review_id).write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")


def _read_record(review_id: str) -> ReviewRecord | None:
    path = _record_path(review_id)
    if not path.exists():
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
        return ReviewRecord(
            review_id=payload["review_id"],
            text=payload["text"],
            source_type=payload["source_type"],
            review=ReviewResponse.model_validate(payload["review"]),
            created_at=datetime.fromisoformat(payload["created_at"]),
        )
    except (OSError, KeyError, ValueError, json.JSONDecodeError):
        path.unlink(missing_ok=True)
        return None


def _record_path(review_id: str) -> Path:
    safe_id = "".join(char for char in review_id if char.isalnum() or char in "-_")
    return _data_dir / f"{safe_id}.json"
