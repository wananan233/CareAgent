"""跌倒候选到 CareEventV1 的安全适配入口。"""
from __future__ import annotations
from .fall import FallCandidate
from .pipeline import ingest_detections

def ingest_fall_candidate(store: object, candidate: FallCandidate, *, observation_id: str, tenant_id: str, household_id: str, subject_id: str, device_id: str, sequence: int, occurred_at: str) -> tuple[str, ...]:
    """委托统一视觉管线；不会跳过时序确认或人工复核。"""
    return ingest_detections(store, ({"observation_id": observation_id, "label": candidate.label, "confidence": candidate.confidence},), tenant_id=tenant_id, household_id=household_id, subject_id=subject_id, device_id=device_id, sequence=sequence, occurred_at=occurred_at)
