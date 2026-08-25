"""视觉推理结果的隐私边界适配器；不执行模型、不接触原始媒体。"""
from __future__ import annotations

from collections.abc import Iterable, Mapping

from .events import VisionObservation

_FORBIDDEN_KEYS = frozenset({"frame", "frame_path", "video", "video_path", "face", "face_id", "name", "person_id", "bbox", "xyxy"})


def observations_from_detections(detections: Iterable[Mapping[str, object]]) -> tuple[VisionObservation, ...]:
    """将模型输出裁剪成无媒体、无身份的观察对象。"""
    result: list[VisionObservation] = []
    for detection in detections:
        keys = set(detection)
        if keys & _FORBIDDEN_KEYS or not keys <= {"observation_id", "label", "confidence"}:
            raise ValueError("vision detection contains forbidden or unknown fields")
        observation_id, label, confidence = detection.get("observation_id"), detection.get("label"), detection.get("confidence")
        if not isinstance(observation_id, str) or not observation_id or not isinstance(label, str) or not label:
            raise ValueError("observation_id and label must be non-empty strings")
        if not isinstance(confidence, (int, float)) or isinstance(confidence, bool) or not 0 <= confidence <= 1:
            raise ValueError("confidence must be within [0, 1]")
        bucket = "HIGH" if confidence >= 0.8 else "MEDIUM" if confidence >= 0.5 else "LOW"
        result.append(VisionObservation(observation_id, label[:80], bucket, "CANDIDATE"))
    return tuple(result)
