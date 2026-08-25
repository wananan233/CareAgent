"""隔离 YOLO 推理边界；输出仅为内存中的候选检测。"""
from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class InferenceDetection:
    label: str
    confidence: float
    bbox_xyxy: tuple[float, float, float, float]
    frame_timestamp: str
    model_version: str


class YOLOInferenceService:
    def __init__(self, predictor: Any, *, model_version: str) -> None:
        self._predictor = predictor
        self.model_version = model_version

    @classmethod
    def from_weights(cls, weights_path: str | Path) -> "YOLOInferenceService":
        path = Path(weights_path)
        if not path.is_file() or path.is_relative_to(Path.cwd()):
            raise ValueError("weights must be an existing external file")
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        from ultralytics import YOLO
        return cls(YOLO(str(path)), model_version=f"sha256:{digest}")

    def infer(self, frame: object, *, frame_timestamp: str, confidence_threshold: float = 0.25) -> tuple[InferenceDetection, ...]:
        if not 0 <= confidence_threshold <= 1:
            raise ValueError("confidence_threshold must be within [0, 1]")
        result = self._predictor.predict(source=frame, conf=confidence_threshold, save=False, verbose=False)[0]
        detections: list[InferenceDetection] = []
        for index, confidence in enumerate(result.boxes.conf.tolist()):
            coords = tuple(float(x) for x in result.boxes.xyxy.tolist()[index])
            label = str(result.names[int(result.boxes.cls.tolist()[index])])
            detections.append(InferenceDetection(label, float(confidence), coords, frame_timestamp, self.model_version))
        return tuple(detections)
