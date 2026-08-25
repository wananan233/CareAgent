"""视觉批次资源上限适配器。"""
from collections.abc import Iterable, Mapping
from .events import VisionObservation
from .inference import observations_from_detections

def bounded_observations(detections: Iterable[Mapping[str, object]], *, max_detections: int = 256) -> tuple[VisionObservation, ...]:
    """限制单批次检测数量，防止异常输入耗尽内存或 CPU。"""
    if max_detections < 1:
        raise ValueError("max_detections must be positive")
    materialized = []
    for index, detection in enumerate(detections):
        if index >= max_detections:
            raise ValueError("vision detection batch exceeds resource limit")
        materialized.append(detection)
    return observations_from_detections(materialized)
