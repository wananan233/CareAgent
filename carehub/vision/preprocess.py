"""V0 OpenCV 内存帧预处理；不读取路径、不持久化原始媒体。"""
from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class FrameMetadata:
    camera_simulator_id: str
    frame_timestamp: str
    width: int
    height: int
    frame_sha256: str
    quality: str


def preprocess_bgr(frame: object, *, camera_simulator_id: str, frame_timestamp: str, target_size: int = 640) -> tuple[object, FrameMetadata]:
    """确定性缩放和质量检查；返回内存帧，不写文件。"""
    import cv2
    import numpy as np

    if not camera_simulator_id or target_size < 32:
        raise ValueError("invalid media contract")
    try:
        datetime.fromisoformat(frame_timestamp.replace("Z", "+00:00"))
    except ValueError as error:
        raise ValueError("frame_timestamp must be ISO-8601") from error
    if not isinstance(frame, np.ndarray) or frame.ndim != 3 or frame.shape[2] != 3 or frame.dtype != np.uint8:
        raise ValueError("frame must be uint8 BGR ndarray")
    height, width = frame.shape[:2]
    if height == 0 or width == 0:
        raise ValueError("frame must not be empty")
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    quality = "LOW" if float(gray.std()) < 3.0 else "HIGH"
    scale = min(target_size / width, target_size / height)
    resized = cv2.resize(frame, (max(1, round(width * scale)), max(1, round(height * scale))), interpolation=cv2.INTER_AREA)
    digest = hashlib.sha256(frame.tobytes()).hexdigest()
    return resized, FrameMetadata(camera_simulator_id, frame_timestamp, width, height, digest, quality)
