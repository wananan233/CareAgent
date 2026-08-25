"""把视觉模型的最小输出转换为 CareEventV1。

本模块不读取视频、不保存帧或人脸信息，也不作安全等级裁决；视觉模型只能
提供辅助观察，最终业务状态仍由 Core 规则和人工复核决定。
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Mapping

from carehub.core.events import new_event


CONFIDENCE_BUCKETS = frozenset({"LOW", "MEDIUM", "HIGH"})
TEMPORAL_STATES = frozenset({"CANDIDATE", "CONFIRMED", "REJECTED"})


@dataclass(frozen=True)
class VisionObservation:
    """不含身份和媒体引用的最小观察结果。"""

    observation_id: str
    label: str
    confidence_bucket: str
    temporal_state: str
    source: str = "SIMULATOR"


def confirm_observation(labels: Iterable[str], *, required_consecutive: int = 3) -> str:
    """仅依据相邻标签做时间确认；不把确认结果升级为告警或动作。"""
    if required_consecutive < 1:
        raise ValueError("required_consecutive must be positive")
    sequence = list(labels)
    if not sequence:
        return "REJECTED"
    tail = sequence[-1]
    if not isinstance(tail, str) or not tail:
        return "REJECTED"
    return "CONFIRMED" if len(sequence) >= required_consecutive and all(item == tail for item in sequence[-required_consecutive:]) else "CANDIDATE"


def build_vision_event(
    observation: VisionObservation,
    *,
    tenant_id: str,
    household_id: str,
    subject_id: str,
    aggregate_id: str,
    sequence: int,
    occurred_at: str,
) -> dict[str, object]:
    """构造可写入 EventStore 的最小视觉事件。"""
    if observation.confidence_bucket not in CONFIDENCE_BUCKETS:
        raise ValueError("invalid confidence bucket")
    if observation.temporal_state not in TEMPORAL_STATES:
        raise ValueError("invalid temporal state")
    if not observation.observation_id or not observation.label:
        raise ValueError("observation_id and label are required")
    payload = {
        "observation_id": observation.observation_id,
        "label": observation.label[:80],
        "confidence_bucket": observation.confidence_bucket,
        "temporal_state": observation.temporal_state,
    }
    return new_event(
        tenant_id=tenant_id,
        household_id=household_id,
        subject_id=subject_id,
        aggregate=f"device:{aggregate_id}",
        sequence=sequence,
        event_type="VISION_OBSERVATION",
        payload=payload,
        source=observation.source,
        quality=observation.confidence_bucket,
        privacy="INTERNAL",
        occurred_at=occurred_at,
        event_id=f"vision-{aggregate_id}-{sequence}-{observation.observation_id}"[:180],
        received_at=occurred_at,
        correlation_id=f"corr-vision-{aggregate_id}-{sequence}",
        trace_id=f"trace-vision-{aggregate_id}-{sequence}",
    )


def append_vision_observation(store: object, event: Mapping[str, object]) -> bool:
    """通过 EventStore 的最小 append 接口写入事件，不暴露媒体内容。"""
    append = getattr(store, "append", None)
    if not callable(append):
        raise TypeError("store must provide append(event)")
    return bool(append(dict(event)))
