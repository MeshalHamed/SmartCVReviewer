from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
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
    return review


def get_review(review_id: str) -> ReviewRecord | None:
    cleanup_expired_reviews()
    return _records.get(review_id)


def cleanup_expired_reviews() -> None:
    now = datetime.now(timezone.utc)
    expired = [review_id for review_id, record in _records.items() if now - record.created_at > _ttl]
    for review_id in expired:
        _records.pop(review_id, None)
