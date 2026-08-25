"""V0 视觉候选的时序确认与人工复核内存队列。"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone

from .events import VisionObservation, confirm_observation


@dataclass(frozen=True)
class ReviewItem:
    review_id: str
    observation: VisionObservation
    status: str
    reason: str
    created_at: str


class ReviewQueue:
    def __init__(self) -> None:
        self._items: dict[str, ReviewItem] = {}

    def submit(self, review_id: str, observation: VisionObservation, history: list[str]) -> ReviewItem:
        state = confirm_observation(history)
        status = "PENDING" if observation.confidence_bucket != "HIGH" or state != "CONFIRMED" else "READY"
        item = ReviewItem(review_id, observation, status, "LOW_CONFIDENCE_OR_UNCONFIRMED" if status == "PENDING" else "TEMPORALLY_CONFIRMED", datetime.now(timezone.utc).isoformat(timespec="seconds"))
        self._items[review_id] = item
        return item

    def decide(self, review_id: str, *, approved: bool) -> ReviewItem:
        current = self._items[review_id]
        status = "CONFIRMED" if approved else "REJECTED"
        item = ReviewItem(current.review_id, current.observation, status, "HUMAN_APPROVED" if approved else "HUMAN_REJECTED", current.created_at)
        self._items[review_id] = item
        return item

    def get(self, review_id: str) -> ReviewItem:
        return self._items[review_id]
