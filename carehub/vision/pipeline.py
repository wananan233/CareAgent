"""V0 视觉观察到 EventStore 的确定性、最小化管线。"""
from __future__ import annotations

from collections.abc import Iterable, Mapping

from .events import append_vision_observation, build_vision_event
from .inference import observations_from_detections


def ingest_detections(
    store: object,
    detections: Iterable[Mapping[str, object]],
    *,
    tenant_id: str,
    household_id: str,
    subject_id: str,
    device_id: str,
    sequence: int,
    occurred_at: str,
) -> tuple[str, ...]:
    """写入最小视觉事件，返回实际插入的 event_id。"""
    observations = observations_from_detections(detections)
    inserted: list[str] = []
    for offset, observation in enumerate(observations):
        event = build_vision_event(
            observation,
            tenant_id=tenant_id,
            household_id=household_id,
            subject_id=subject_id,
            aggregate_id=device_id,
            sequence=sequence + offset,
            occurred_at=occurred_at,
        )
        if append_vision_observation(store, event):
            inserted.append(str(event["event_id"]))
    return tuple(inserted)
